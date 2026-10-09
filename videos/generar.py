"""Crea el vídeo de cada publicación que aún no lo tiene y lo sube a Airtable (campo «Vídeo»).

- Lee en Publicaciones las que no están «Publicado» y no tienen vídeo (las más antiguas primero).
- Busca su cita en la tabla Citas para sacar la Fuente (gancho) y la foto (Foto manual o Wikipedia).
- El crédito de la foto sale del campo «Crédito foto» de la publicación (el que reviso yo).
- Si el crédito tiene «[...]» (pendiente de revisar), se salta esa publicación y se reintenta otro día.

Variables: AIRTABLE_TOKEN (secret de GitHub), LIMITE (máximo de vídeos por ejecución),
PRUEBA_LOCAL (opcional: JSON con publicaciones de prueba; no toca Airtable ni Wikipedia)."""
import base64, difflib, json, os, re, subprocess, sys, tempfile, time, unicodedata, urllib.parse
import requests
from comun import frases
from tts import sintetizar

BASE = "appeuC0uIAlqqp1h9"
T_PUB = "tbl7ynqI9bJrWtR0m"      # Publicaciones
T_CITAS = "tbluECdgOggDiZIFJ"    # Citas
CAMPO_VIDEO = "Vídeo"
CAMPO_TITULO = "Título vídeo"    # título para YouTube (lo puedo corregir en la revisión)
UA = "DichoYHechoBot/1.1 (https://www.instagram.com/dichoyhechoo_/; dichoyhecho66@gmail.com) GitHubActions"
AQUI = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("AIRTABLE_TOKEN", "")
LIMITE = int(os.environ.get("LIMITE") or 12)
PRUEBA = os.environ.get("PRUEBA_LOCAL")


# ---------- Airtable ----------
def pedir(method, url, **kw):
    for _ in range(4):
        r = requests.request(method, url, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=90, **kw)
        if r.status_code == 429:          # demasiadas peticiones: Airtable pide esperar 30 s
            time.sleep(31); continue
        if r.status_code >= 400:
            raise RuntimeError(f"Airtable {r.status_code}: {r.text[:300]}")
        return r.json()
    raise RuntimeError("Airtable sigue contestando 429")


def listar(tabla, campos, formula=None, orden=None):
    regs, params = [], [("pageSize", "100")] + [("fields[]", c) for c in campos]
    if formula: params.append(("filterByFormula", formula))
    if orden: params += [("sort[0][field]", orden), ("sort[0][direction]", "asc")]
    offset = None
    while True:
        p = params + ([("offset", offset)] if offset else [])
        d = pedir("GET", f"https://api.airtable.com/v0/{BASE}/{tabla}", params=p)
        regs += d["records"]
        offset = d.get("offset")
        if not offset: return regs


def actualizar(cambios):
    """cambios = [(rec_id, {campo: valor})]; de 10 en 10 (máximo de Airtable por petición)."""
    for i in range(0, len(cambios), 10):
        lote = [{"id": r, "fields": f} for r, f in cambios[i:i + 10]]
        pedir("PATCH", f"https://api.airtable.com/v0/{BASE}/{T_PUB}", json={"records": lote})


def titulo_video(frase, autor):
    """Título de YouTube (máx. 100): «cita» — Autor; si no cabe, Autor: «principio de la cita…»."""
    t = f"«{frase}» — {autor}"
    if len(t) <= 100:
        return t
    base = f"{autor}: «"
    corte = frase[:100 - len(base) - 2].rsplit(" ", 1)[0].rstrip(",;:.¿¡ ")
    return f"{base}{corte}…»"


def subir_video(rec_id, ruta, nombre):
    datos = open(ruta, "rb").read()
    if len(datos) > 5_000_000:
        raise RuntimeError(f"el vídeo pesa {len(datos) / 1e6:.1f} MB (máximo 5)")
    campo = urllib.parse.quote(CAMPO_VIDEO)
    pedir("POST", f"https://content.airtable.com/v0/{BASE}/{rec_id}/{campo}/uploadAttachment",
          json={"contentType": "video/mp4", "filename": nombre, "file": base64.b64encode(datos).decode()})


# ---------- Datos de la cita y foto ----------
def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[\W_]+", "", s)


def buscar_cita(pub, citas):
    f = norm(pub.get("Frase"))
    for c in citas:
        if norm(c["fields"].get("Cita")) == f:
            return c["fields"]
    # Si corregí una errata en la Frase: la más parecida del mismo autor
    mismos = [c["fields"] for c in citas if norm(c["fields"].get("Autor")) == norm(pub.get("Autor"))]
    mejor = max(mismos, key=lambda c: difflib.SequenceMatcher(None, norm(c.get("Cita")), f).ratio(), default=None)
    if mejor and difflib.SequenceMatcher(None, norm(mejor.get("Cita")), f).ratio() >= 0.85:
        return mejor
    return None


def descargar(url, ruta, ua=True):
    r = requests.get(url, headers={"User-Agent": UA} if ua else {}, timeout=60)
    r.raise_for_status()
    open(ruta, "wb").write(r.content)
    return ruta


def foto_wikipedia(titulo):
    """Foto principal del artículo, solo si tiene licencia libre (igual que el escenario 1)."""
    if not titulo: return None
    r = requests.get("https://en.wikipedia.org/w/api.php", headers={"User-Agent": UA}, timeout=30, params={
        "action": "query", "format": "json", "formatversion": "2", "prop": "pageimages",
        "piprop": "thumbnail|name", "pithumbsize": "1600", "pilicense": "free", "redirects": "1",
        "titles": titulo})
    r.raise_for_status()
    pags = r.json().get("query", {}).get("pages", [])
    return pags[0].get("thumbnail", {}).get("source") if pags else None


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "video"


# ---------- Un vídeo ----------
def hacer_video(rec_id, pub, cita, tmp):
    frase, autor = pub["Frase"].strip(), pub["Autor"].strip()
    credito = (pub.get("Crédito foto") or "").strip()
    if "[" in credito:
        return "saltada", f"el crédito está pendiente de revisar: «{credito}»"

    # Foto: manual > Wikipedia > fondo neutro
    foto = None
    if cita.get("foto_local"):
        foto = cita["foto_local"]
    elif cita.get("Foto manual"):
        foto = descargar(cita["Foto manual"][0]["url"], os.path.join(tmp, "foto.jpg"), ua=False)
    else:
        url = foto_wikipedia(cita.get("Wikipedia"))
        if url:
            foto = descargar(url, os.path.join(tmp, "foto.jpg"))
    if not foto:
        credito = ""

    # Voz y música
    fr = frases(frase)
    tv = sintetizar(fr, autor, os.path.join(tmp, "voz.wav"), os.path.join(tmp, "voz.json"))
    dur_musica = max(14.0, 2.4 + tv[-1]["fin"] + 6)
    semilla = sum(rec_id.encode()) % 1000
    subprocess.run([sys.executable, os.path.join(AQUI, "musica.py"), os.path.join(tmp, "musica.wav"),
                    f"{dur_musica:.2f}", str(semilla)], check=True, stdout=subprocess.DEVNULL)

    salida = os.path.join(tmp, f"{slug(autor)}-{rec_id[-6:]}.mp4")
    cfg = {"cita": frase, "autor": autor, "fuente": cita.get("Fuente", ""),
           "credito": f"Foto: {credito}" if credito else "", "foto": foto,
           "voz_wav": os.path.join(tmp, "voz.wav"), "voz_json": os.path.join(tmp, "voz.json"),
           "musica": os.path.join(tmp, "musica.wav"), "salida": salida}
    json.dump(cfg, open(os.path.join(tmp, "cfg.json"), "w"), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(AQUI, "render.py"), os.path.join(tmp, "cfg.json")],
                       check=True, capture_output=True, text=True)
    info = json.loads(r.stdout.strip().splitlines()[-1])
    return "ok", info


def main():
    if PRUEBA:
        pubs = json.load(open(PRUEBA))
        pendientes = [(p["id"], p) for p in pubs]
        citas = None
    else:
        if not TOKEN:
            sys.exit("Falta el secret AIRTABLE_TOKEN")
        regs = listar(T_PUB, ["Frase", "Autor", "Crédito foto", "Estado", CAMPO_VIDEO, CAMPO_TITULO],
                      formula="{Estado}!='Publicado'", orden="Fecha de Creación")
        # Títulos que faltan en vídeos ya hechos
        sin_titulo = [(r["id"], {CAMPO_TITULO: titulo_video(r["fields"]["Frase"].strip(), r["fields"].get("Autor", "").strip())})
                      for r in regs if r["fields"].get(CAMPO_VIDEO) and not r["fields"].get(CAMPO_TITULO)
                      and r["fields"].get("Frase")]
        if sin_titulo:
            actualizar(sin_titulo)
            print(f"Títulos de YouTube añadidos a {len(sin_titulo)} vídeo(s) ya hechos.")
        pendientes = [(r["id"], r["fields"]) for r in regs if not r["fields"].get(CAMPO_VIDEO) and r["fields"].get("Frase")]
        print(f"Publicaciones sin vídeo: {len(pendientes)}. Se harán como mucho {LIMITE}.")
        citas = listar(T_CITAS, ["Cita", "Autor", "Wikipedia", "Fuente", "Foto manual"]) if pendientes else []

    filas, errores, hechos = [], 0, 0
    for rec_id, pub in pendientes:
        if hechos >= LIMITE: break
        autor = pub.get("Autor", "?")
        t0 = time.time()
        try:
            cita = pub if PRUEBA else buscar_cita(pub, citas)
            if cita is None:
                raise RuntimeError("no encuentro su cita en la tabla Citas")
            with tempfile.TemporaryDirectory() as tmp:
                estado, info = hacer_video(rec_id, pub, cita, tmp)
                if estado == "ok":
                    if PRUEBA:
                        os.makedirs("salida_prueba", exist_ok=True)
                        os.replace(info["salida"], os.path.join("salida_prueba", os.path.basename(info["salida"])))
                    else:
                        subir_video(rec_id, info["salida"], os.path.basename(info["salida"]))
                        actualizar([(rec_id, {CAMPO_TITULO: titulo_video(pub["Frase"].strip(), autor.strip())})])
                    hechos += 1
                    msg = f"{info['duracion']} s, {info['mb']} MB, {time.time() - t0:.0f} s de montaje · {info['gancho']}"
                else:
                    msg = info
        except Exception as e:  # una publicación con problemas no para las demás
            estado, msg, errores = "error", str(e)[:300], errores + 1
        print(f"[{estado}] {autor} ({rec_id}): {msg}", flush=True)
        filas.append(f"| {autor} | {estado} | {msg} |")

    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as f:
            f.write(f"### Vídeos creados: {hechos}\n\n| Autor | Estado | Detalle |\n|---|---|---|\n" + "\n".join(filas) + "\n")
    if errores:
        sys.exit(f"{errores} publicación(es) con error")


if __name__ == "__main__":
    main()
