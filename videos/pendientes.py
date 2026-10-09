"""Paso previo rápido (sin instalar nada): ¿hay publicaciones que necesiten vídeo?
Escribe hay=true/false en GITHUB_OUTPUT para saltarse la instalación si no hay trabajo.
Cuenta las que no están «Publicado», no tienen «Vídeo» y no tienen el crédito pendiente («[…]»)."""
import json, os, urllib.parse, urllib.request

BASE, T_PUB = "appeuC0uIAlqqp1h9", "tbl7ynqI9bJrWtR0m"
params = [("pageSize", "100"), ("filterByFormula", "{Estado}!='Publicado'"),
          ("fields[]", "Frase"), ("fields[]", "Crédito foto"), ("fields[]", "Vídeo")]
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
    offset = d.get("offset")
    if not offset: break
print(f"Publicaciones que necesitan vídeo: {n}")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as out:
    out.write(f"hay={'true' if n else 'false'}\n")
