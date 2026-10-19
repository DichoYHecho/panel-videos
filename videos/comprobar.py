"""Mejora M2: comprobar en Buffer que cada publicación «Publicado» salió de verdad.

Lee (no publica ni borra nada) las publicaciones de Buffer de los últimos días y,
para cada publicación de Airtable en «Publicado» sin comprobar (o pendiente «⏳»),
escribe una línea en el campo «Comprobación»:
  ✅ 19/10 17:01 · Foto, Reel, TikTok y YouTube publicados
  ⚠️ 19/10 17:01 · TikTok: <error de Buffer> · Bien: Foto, Reel y YouTube
  ⏳ 19/10 17:01 · Aún enviándose: YouTube        (se vuelve a mirar en la siguiente ejecución)
El campo «Avisos» enseña las «⚠️» en la tarjeta de la publicación. También deja un resumen en GitHub.
Sin avisos al móvil (decisión del 10 de octubre): la señal se queda en Airtable."""
import json, os, re, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BASE, T_PUB = "appeuC0uIAlqqp1h9", "tbl7ynqI9bJrWtR0m"
CAMPO = "Comprobación"
ORG = "6ac6ccc45fecc6a92564dae9"
CANAL = {"6ac6ce226a5c39ccb6482641": "instagram",
         "6ac91cf66a5c39ccb663ca38": "tiktok",
         "6ac91cd56a5c39ccb663c969": "youtube"}
ORDEN = ["Foto", "Reel", "TikTok", "YouTube"]
VIDEO_DESDE = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)  # desde aquí, todas llevan vídeo
MADRID = ZoneInfo("Europe/Madrid")
DIAS = int(os.environ.get("DIAS") or "4")


# ---------- Airtable ----------
def airtable(metodo, ruta, datos=None):
    req = urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{ruta}", method=metodo,
                                 data=json.dumps(datos).encode() if datos is not None else None,
                                 headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}",
                                          "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def por_comprobar():
    formula = f"AND({{Estado}}='Publicado', OR({{{CAMPO}}}='', FIND('⏳', {{{CAMPO}}})))"
    params = [("pageSize", "100"), ("filterByFormula", formula), ("fields[]", "Frase"), ("fields[]", "Autor"),
              ("fields[]", "Caption"), ("fields[]", "Vídeo"), ("fields[]", CAMPO)]
    out, offset = [], None
    while True:
        q = urllib.parse.urlencode(params + ([("offset", offset)] if offset else []))
        d = airtable("GET", f"{T_PUB}?{q}")
        out += d["records"]
        offset = d.get("offset")
        if not offset:
            return out


def guardar(cambios):
    for i in range(0, len(cambios), 10):
        airtable("PATCH", T_PUB, {"records": [{"id": rid, "fields": {CAMPO: txt}} for rid, txt in cambios[i:i + 10]]})


# ---------- Buffer (solo lectura) ----------
CAMPOS = "id status channelId text sentAt dueAt createdAt externalLink assets { type } error { message }"


def consulta(desde, after):
    # Los valores van escritos en la consulta (como en los ejemplos de la documentación de Buffer)
    pag = f"after: {json.dumps(after)}, " if after else ""
    return ("query Comprobar { posts(first: 100, " + pag +
            f"input: {{ organizationId: {json.dumps(ORG)}, filter: {{ startDate: {json.dumps(desde)} }} }}) "
            f"{{ edges {{ node {{ {CAMPOS} }} }} pageInfo {{ hasNextPage endCursor }} }} }}")


def posts_buffer(desde):
    out, after = [], None
    for _ in range(10):  # como mucho 1.000 publicaciones (10 peticiones)
        cuerpo = {"query": consulta(desde, after)}
        req = urllib.request.Request("https://api.buffer.com", data=json.dumps(cuerpo).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}",
                                              "Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        if d.get("errors"):
            raise SystemExit("Error de la API de Buffer: " + json.dumps(d["errors"], ensure_ascii=False)[:500])
        p = d["data"]["posts"]
        out += [e["node"] for e in p["edges"]]
        if not p["pageInfo"]["hasNextPage"]:
            break
        after = p["pageInfo"]["endCursor"]
    return out


# ---------- Comparar ----------
def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"\s+", " ", s).strip()


def clase(post):
    canal = CANAL.get(post.get("channelId"))
    if canal == "instagram":
        tipos = {a.get("type") for a in post.get("assets") or []}
        return "Reel" if "video" in tipos else "Foto"
    return {"tiktok": "TikTok", "youtube": "YouTube"}.get(canal)


def fecha(post):
    t = post.get("sentAt") or post.get("dueAt") or post.get("createdAt")
    return datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None


def lista(nombres):
    nombres = [n for n in ORDEN if n in nombres]
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def resultado(pub, posts):
    """Línea para el campo «Comprobación», o None si no se encuentra en Buffer."""
    f = pub["fields"]
    cap, frase = norm(f.get("Caption")), norm(f.get("Frase"))[:60]
    suyos = [p for p in posts if norm(p.get("text")) == cap] or \
            ([p for p in posts if frase and frase in norm(p.get("text"))] if frase else [])
    if not suyos:
        return None
    # Por cada red, el mejor estado (sent > sending/scheduled > error)
    rango = {"sent": 3, "sending": 2, "scheduled": 2, "needs_approval": 1, "draft": 1, "error": 0}
    mejor = {}
    for p in suyos:
        c = clase(p)
        if c and (c not in mejor or rango.get(p["status"], 0) > rango.get(mejor[c]["status"], 0)):
            mejor[c] = p
    foto = mejor.get("Foto")
    cuando = fecha(foto or suyos[0])
    hora = cuando.astimezone(MADRID).strftime("%d/%m %H:%M") if cuando else "?"
    esperadas = ["Foto"]
    hay_video = any(c in mejor for c in ("Reel", "TikTok", "YouTube"))
    if hay_video or (f.get("Vídeo") and cuando and cuando >= VIDEO_DESDE):
        esperadas += ["Reel", "TikTok", "YouTube"]
    bien = [c for c in esperadas if c in mejor and mejor[c]["status"] == "sent"]
    enviando = [c for c in esperadas if c in mejor and mejor[c]["status"] in ("sending", "scheduled")]
    fallos = []
    for c in esperadas:
        p = mejor.get(c)
        if p is None:
            fallos.append(f"{c}: no está en Buffer")
        elif p["status"] in ("error", "draft", "needs_approval"):
            msg = re.sub(r"\s+", " ", ((p.get("error") or {}).get("message") or p["status"])).strip()
            fallos.append(f"{c}: {msg[:120]}")
    if fallos:
        txt = f"⚠️ {hora} · " + " · ".join(fallos)
        if bien:
            txt += f" · Bien: {lista(bien)}"
        if enviando:
            txt += f" · Aún enviándose: {lista(enviando)}"
    elif enviando:
        txt = f"⏳ {hora} · Aún enviándose: {lista(enviando)}"
    else:
        txt = f"✅ {hora} · {lista(bien)} {'publicada' if bien == ['Foto'] else 'publicados'}"
    return txt[:250]


def main():
    pubs = por_comprobar()
    print(f"Publicaciones por comprobar: {len(pubs)}")
    if not pubs:
        return
    desde = (datetime.now(timezone.utc) - timedelta(days=DIAS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = posts_buffer(desde)
    print(f"Publicaciones en Buffer desde {desde}: {len(posts)}")
    cambios, filas = [], []
    for pub in pubs:
        txt = resultado(pub, posts)
        autor = pub["fields"].get("Autor", "?")
        if txt is None:
            filas.append((autor, f"No encontrada en Buffer en los últimos {DIAS} días (se deja sin comprobar)"))
            continue
        if txt != pub["fields"].get(CAMPO):
            cambios.append((pub["id"], txt))
        filas.append((autor, txt))
        print(f"- {autor}: {txt}")
    guardar(cambios)
    print(f"Actualizadas en Airtable: {len(cambios)}")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as out:
            out.write("## Comprobación de las publicaciones (M2)\n\n| Autor | Resultado |\n|---|---|\n")
            out.writelines(f"| {a} | {t.replace('|', '/')} |\n" for a, t in filas)


if __name__ == "__main__":
    main()
