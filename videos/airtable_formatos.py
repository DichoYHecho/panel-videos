"""Fase 3.2 (27 nov 2026): crea la tabla «Vídeos» de la base «Formatos DyH» (espacio de trabajo aparte, con su propio
cupo de 1.000 registros y 1.000 llamadas al mes). Se puede lanzar las veces que haga falta: si la tabla ya existe,
solo añade los campos que falten. No borra nada.

Secret: AIRTABLE_TOKEN_FORMATOS (token personal con schema.bases:read/write y data.records:read/write, SOLO para
esta base). Las vistas (Kanban «Revisión») se crean a mano en la web: la API no deja crearlas."""
import os, sys
import requests

BASE = "appvmfWCVMC1oQyiI"
TABLA = "Vídeos"
TOKEN = os.environ.get("AIRTABLE_TOKEN_FORMATOS", "")
API = f"https://api.airtable.com/v0/meta/bases/{BASE}/tables"

FORMATOS = ["Frase célebre", "Quiz", "¿Lo dijo o no lo dijo?", "Autor contra autor", "El origen"]
ESTADOS = ["Por Revisar", "Aprobado", "Publicado", "Descartado"]
CAMPOS = [
    {"name": "Nombre", "type": "singleLineText", "description": "id de la ficha (p. ej. lodijo_einstein)"},
    {"name": "Formato", "type": "singleSelect", "options": {"choices": [{"name": f} for f in FORMATOS]}},
    {"name": "Estado", "type": "singleSelect", "options": {"choices": [{"name": e} for e in ESTADOS]}},
    {"name": "Vídeo", "type": "multipleAttachments"},
    {"name": "Título", "type": "singleLineText", "description": "título del Short (máx. 100 caracteres)"},
    {"name": "Descripción", "type": "multilineText", "description": "texto del post; las fuentes van aquí, nunca en el vídeo"},
    {"name": "Fuentes", "type": "multilineText"},
    {"name": "Comentario", "type": "multilineText", "description": "comentario propio para YouTube (máx. 500)"},
    {"name": "Publicar el", "type": "dateTime", "options": {"timeZone": "Europe/Madrid", "dateFormat": {"name": "european"}, "timeFormat": {"name": "24hour"}}},
    {"name": "Ficha", "type": "multilineText", "description": "ficha JSON del vídeo (guion con marcas y datos)"},
    {"name": "Avisos", "type": "multilineText", "description": "lo escribe GitHub: fallos de render, textos demasiado largos…"},
    {"name": "Comprobación", "type": "singleLineText", "description": "estado de la publicación en Buffer"},
    {"name": "ID Buffer", "type": "singleLineText"},
]


def main():
    if not TOKEN:
        sys.exit("Falta el secret AIRTABLE_TOKEN_FORMATOS: no se ha tocado nada.")
    h = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    tablas = requests.get(API, headers=h, timeout=30).json().get("tables", [])
    tabla = next((t for t in tablas if t["name"] == TABLA), None)
    if not tabla:
        r = requests.post(API, headers=h, timeout=30, json={"name": TABLA, "description": "Vídeos de los formatos nuevos: revisión y publicación", "fields": CAMPOS})
        r.raise_for_status()
        print(f"Tabla «{TABLA}» creada con {len(CAMPOS)} campos ({r.json()['id']}).")
        return
    tienen = {f["name"] for f in tabla["fields"]}
    for c in CAMPOS:
        if c["name"] not in tienen:
            r = requests.post(f"{API}/{tabla['id']}/fields", headers=h, timeout=30, json=c)
            r.raise_for_status()
            print(f"Campo añadido: {c['name']}")
    print(f"Tabla «{TABLA}» al día ({tabla['id']}).")


if __name__ == "__main__":
    main()
