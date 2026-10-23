"""Paso previo rápido (sin instalar nada): ¿hay publicaciones que necesiten vídeo?
Escribe hay=true/false en GITHUB_OUTPUT para saltarse la instalación si no hay trabajo.
Cuenta las que no están «Publicado» y no tienen «Vídeo» (salvo crédito pendiente «[…]»),
las que tienen vídeo pero aún no tienen «Título vídeo» y, desde el 23 oct 2026 (fase V2),
las que tienen un vídeo con la voz de antes (sin «-v2» en el nombre del archivo), si REHACER=1."""
import json, os, urllib.parse, urllib.request

BASE, T_PUB = "appeuC0uIAlqqp1h9", "tbl7ynqI9bJrWtR0m"
REHACER = os.environ.get("REHACER", "1") == "1"
params = [("pageSize", "100"), ("filterByFormula", "{Estado}!='Publicado'"),
          ("fields[]", "Frase"), ("fields[]", "Crédito foto"), ("fields[]", "Vídeo"), ("fields[]", "Título vídeo")]
n, viejos, offset = 0, 0, None
while True:
    q = urllib.parse.urlencode(params + ([("offset", offset)] if offset else []))
    req = urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{T_PUB}?{q}",
                                 headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    for r in d["records"]:
        f = r["fields"]
        if not f.get("Frase"):
            continue
        if not f.get("Vídeo") and "[" not in (f.get("Crédito foto") or ""):
            n += 1
        elif f.get("Vídeo") and not f.get("Título vídeo"):
            n += 1  # vídeo hecho al que le falta el título de YouTube
        elif (REHACER and f.get("Vídeo") and "[" not in (f.get("Crédito foto") or "")
              and not any("-v2.mp4" in (a.get("filename") or "") for a in f["Vídeo"])):
            viejos += 1  # vídeo con la voz de antes: se rehace con la de Gemini
    offset = d.get("offset")
    if not offset: break
print(f"Publicaciones que necesitan vídeo: {n}; con la voz de antes: {viejos}")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as out:
    out.write(f"hay={'true' if n + viejos else 'false'}\n")
