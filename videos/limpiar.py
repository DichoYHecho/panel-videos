"""Limpieza mensual automática: borra el adjunto «Vídeo» de las publicaciones ya «Publicado»
creadas hace más de 30 días (Buffer ya se llevó el vídeo al publicar). Libera espacio:
Airtable Free tiene 1 GB de adjuntos por base. La imagen y el resto de campos no se tocan."""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

BASE, T_PUB, DIAS = "appeuC0uIAlqqp1h9", "tbl7ynqI9bJrWtR0m", 30
CAB = {"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}", "Content-Type": "application/json"}


def api(metodo, url, cuerpo=None):
    req = urllib.request.Request(url, method=metodo, headers=CAB,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    return json.load(urllib.request.urlopen(req, timeout=60))


limite = datetime.now(timezone.utc) - timedelta(days=DIAS)
params = [("pageSize", "100"), ("filterByFormula", "{Estado}='Publicado'"),
          ("fields[]", "Vídeo"), ("fields[]", "Fecha de Creación"), ("fields[]", "Autor")]
borrar, offset = [], None
while True:
    q = urllib.parse.urlencode(params + ([("offset", offset)] if offset else []))
    d = api("GET", f"https://api.airtable.com/v0/{BASE}/{T_PUB}?{q}")
    for r in d["records"]:
        f = r["fields"]
        creada = f.get("Fecha de Creación") or r.get("createdTime")
        if f.get("Vídeo") and creada and datetime.fromisoformat(creada.replace("Z", "+00:00")) < limite:
            borrar.append((r["id"], f.get("Autor", "?")))
    offset = d.get("offset")
    if not offset: break

for i in range(0, len(borrar), 10):
    lote = [{"id": rid, "fields": {"Vídeo": []}} for rid, _ in borrar[i:i + 10]]
    api("PATCH", f"https://api.airtable.com/v0/{BASE}/{T_PUB}", {"records": lote})
print(f"Vídeos borrados (publicados hace más de {DIAS} días): {len(borrar)}")
for _, autor in borrar:
    print(" -", autor)
resumen = os.environ.get("GITHUB_STEP_SUMMARY")
if resumen:
    with open(resumen, "a") as f:
        f.write(f"### Limpieza mensual\n\nVídeos borrados de Airtable: {len(borrar)}\n")
