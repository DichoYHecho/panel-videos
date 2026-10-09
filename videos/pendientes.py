"""Paso previo rápido (sin instalar nada): ¿hay publicaciones que necesiten vídeo?
Escribe hay=true/false en GITHUB_OUTPUT para saltarse la instalación si no hay trabajo.
Cuenta las que no están «Publicado» y no tienen «Vídeo» (salvo crédito pendiente «[…]»),
y las que tienen vídeo pero aún no tienen «Título vídeo»."""
import json, os, urllib.parse, urllib.request

BASE, T_PUB = "appeuC0uIAlqqp1h9", "tbl7ynqI9bJrWtR0m"
params = [("pageSize", "100"), ("filterByFormula", "{Estado}!='Publicado'"),
          ("fields[]", "Frase"), ("fields[]", "Crédito foto"), ("fields[]", "Vídeo"), ("fields[]", "Título vídeo")]
n, offset = 0, None
while True:
    q = urllib.parse.urlencode(params + ([("offset", offset)] if offset else []))
    req = urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{T_PUB}?{q}",
                                 headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    for r in d["records"]:
        f = r["fields"]
        if f.get("Frase") and not f.get("Vídeo") and "[" not in (f.get("Crédito foto") or ""):
            n += 1
        elif f.get("Frase") and f.get("Vídeo") and not f.get("Título vídeo"):
            n += 1  # vídeo hecho al que le falta el título de YouTube
    offset = d.get("offset")
    if not offset: break
print(f"Publicaciones que necesitan vídeo: {n}")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as out:
    out.write(f"hay={'true' if n else 'false'}\n")
