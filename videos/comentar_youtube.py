"""Tarea 6.16, fase C2 (26 oct 2026): publicar el «Comentario» debajo del Short de YouTube.

Se ejecuta en el trabajo «Comprobar publicaciones (M2)», justo después de comprobar.py:
- Busca en Airtable las publicaciones «Publicado» que tienen «Comentario» y aún no lo tienen publicado
  (campo «Comentario YouTube» vacío) o que fallaron («⚠»; se reintentan mientras estén en Buffer).
- En Buffer (solo lectura) busca su Short de YouTube ya enviado y saca el enlace del vídeo.
- Con la API de YouTube (gratis: 50 unidades por comentario, de 10.000 al día) publica el comentario
  en nombre del canal «Dicho y Hecho» y escribe en «Comentario YouTube»:
    ✅ 26/10 17:42 · https://www.youtube.com/watch?v=…&lc=<id del comentario>
    ⚠️ 26/10 17:42 · <error>      (se reintenta en la siguiente ejecución)
  Si el Short aún no está en YouTube (Buffer lo está enviando), se deja vacío y se mira la próxima vez.
- Cada resultado se guarda en Airtable nada más publicarlo, para no comentar nunca dos veces.
- La API no deja fijar el comentario: si lo quiero arriba, se fija a mano en YouTube Studio.

Secrets: AIRTABLE_TOKEN, BUFFER_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET y YT_REFRESH_TOKEN (autorización
del canal con el permiso youtube.force-ssl). Si faltan los de YouTube, no hace nada.
Variables: DIAS (cuántos días mirar en Buffer, 4 por defecto) y SOLO_MIRAR=1 (no publica ni guarda nada).
"""
import json, os, re, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from comprobar import CANAL, DIAS, MADRID, T_PUB, airtable, clase, letras, norm, posts_buffer

CAMPO = "Comentario YouTube"
SOLO_MIRAR = os.environ.get("SOLO_MIRAR") == "1"
CLAVES = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")


def por_comentar():
    formula = (f"AND({{Estado}}='Publicado', {{Comentario}}!='', "
               f"OR({{{CAMPO}}}='', FIND('⚠', {{{CAMPO}}})))")
    params = [("pageSize", "100"), ("filterByFormula", formula)] + \
             [("fields[]", c) for c in ("Frase", "Autor", "Caption", "Comentario", CAMPO)]
    out, offset = [], None
    while True:
        q = urllib.parse.urlencode(params + ([("offset", offset)] if offset else []))
        d = airtable("GET", f"{T_PUB}?{q}")
        out += d["records"]
        offset = d.get("offset")
        if not offset:
            return out


def guardar(rec_id, texto):
    airtable("PATCH", T_PUB, {"records": [{"id": rec_id, "fields": {CAMPO: texto[:250]}}]})


def short_de(pub, posts):
    """La publicación de Buffer del Short de YouTube de esta publicación (la mejor), o None."""
    f = pub["fields"]
    cap, frase = norm(f.get("Caption")), letras(f.get("Frase"))[:50]
    suyos = [p for p in posts if clase(p) == "YouTube"
             and (norm(p.get("text")) == cap or (frase and frase in letras(p.get("text"))))]
    enviados = [p for p in suyos if p.get("status") == "sent" and p.get("externalLink")]
    return (enviados or suyos or [None])[0]


def id_video(enlace):
    m = re.search(r"(?:shorts/|youtu\.be/|[?&]v=)([\w-]{11})", enlace or "")
    return m.group(1) if m else None


def pedir(url, datos=None, token=None, form=False):
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    if form:
        cuerpo = urllib.parse.urlencode(datos).encode()
        cabeceras["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        cuerpo = json.dumps(datos).encode() if datos is not None else None
        cabeceras["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method="POST" if cuerpo else "GET")
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")
        try:
            err = json.loads(txt).get("error")
            txt = err.get("message") if isinstance(err, dict) else (json.loads(txt).get("error_description") or err)
        except Exception:
            pass
        raise RuntimeError(f"{e.code}: {str(txt)[:200]}")


def acceso():
    d = pedir("https://oauth2.googleapis.com/token", {
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, form=True)
    return d["access_token"]


def comentar(token, video, texto):
    d = pedir("https://www.googleapis.com/youtube/v3/commentThreads?part=snippet",
              {"snippet": {"videoId": video, "topLevelComment": {"snippet": {"textOriginal": texto}}}}, token)
    return d["id"]


def main():
    falta = [c for c in CLAVES if not os.environ.get(c)]
    if falta:
        print(f"Faltan los secrets {', '.join(falta)}: no se publica ningún comentario en YouTube.")
        return
    pubs = por_comentar()
    print(f"Publicaciones con comentario por publicar en YouTube: {len(pubs)}")
    if SOLO_MIRAR:  # prueba de la autorización: solo lee el nombre del canal (1 unidad), no publica nada
        canal = pedir("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true", token=acceso())
        print("Autorización correcta. Canal:", ", ".join(c["snippet"]["title"] for c in canal.get("items", [])) or "(ninguno)")
    if not pubs:
        return
    desde = (datetime.now(timezone.utc) - timedelta(days=DIAS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = [p for p in posts_buffer(desde) if CANAL.get(p.get("channelId")) == "youtube"]
    token = None if SOLO_MIRAR else acceso()
    filas = []
    for pub in pubs:
        f, autor = pub["fields"], pub["fields"].get("Autor", "?")
        ahora = datetime.now(MADRID).strftime("%d/%m %H:%M")
        p = short_de(pub, posts)
        video = id_video(p.get("externalLink")) if p else None
        if not p:
            detalle = f"su Short no está en Buffer en los últimos {DIAS} días (se deja como está)"
        elif not video:
            detalle = f"el Short aún no está en YouTube (Buffer: {p.get('status')}); se mira en la siguiente ejecución"
        elif SOLO_MIRAR:
            detalle = f"(solo mirar) se publicaría en {video}: «{f['Comentario'][:80]}…»"
        else:
            try:
                cid = comentar(token, video, f["Comentario"].strip())
                txt = f"✅ {ahora} · https://www.youtube.com/watch?v={video}&lc={cid}"
            except Exception as e:
                txt = f"⚠️ {ahora} · {str(e)[:200]}"
            guardar(pub["id"], txt)   # en el momento, para no comentar nunca dos veces
            detalle = txt
        print(f"- {autor}: {detalle}", flush=True)
        filas.append(f"| {autor} | {detalle.replace('|', '/')} |")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as out:
            out.write("## Comentarios en YouTube (tarea 6.16)\n\n| Autor | Resultado |\n|---|---|\n" + "\n".join(filas) + "\n")


if __name__ == "__main__":
    main()
