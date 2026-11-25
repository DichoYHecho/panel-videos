"""Sube a YouTube un vídeo largo del quiz (25 nov 2026), público y ya, con su título y descripción.

Lo lanza el workflow «Subir vídeo largo a YouTube», que antes descarga el vídeo del run que lo montó.
Uso: python3 subir_largo.py <video.mp4> <metadatos.json>
metadatos.json: {"titulo": "...", "descripcion": "..."}
Si el canal ya tiene un vídeo con ese título, no sube nada (no hay duplicados si se relanza)."""
import json, sys

import requests

from comprobar import norm
from subir_youtube import CATEGORIA, YT, subidos, token


def main():
    video, meta = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
    tok = token()
    hechos, _ = subidos(tok)
    if norm(meta["titulo"]) in hechos:
        print(f"Ya estaba en el canal: https://youtu.be/{hechos[norm(meta['titulo'])]}")
        return
    datos = open(video, "rb").read()
    cuerpo = {"snippet": {"title": meta["titulo"][:100],
                          "description": meta["descripcion"].replace("<", "‹").replace(">", "›")[:4900],
                          "categoryId": CATEGORIA, "defaultLanguage": "es", "defaultAudioLanguage": "es",
                          "tags": meta.get("etiquetas", [])},
              "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True,
                         "license": "youtube", "containsSyntheticMedia": True}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos", timeout=120,
                      params={"uploadType": "resumable", "part": "snippet,status", "notifySubscribers": "true"},
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(datos))},
                      data=json.dumps(cuerpo))
    if r.status_code >= 400:
        sys.exit(f"FALLO al empezar la subida: {r.status_code}: {r.text[:300]}")
    r = requests.put(r.headers["Location"], data=datos, timeout=1800, headers={"Authorization": f"Bearer {tok}"})
    if r.status_code >= 400:
        sys.exit(f"FALLO al subir: {r.status_code}: {r.text[:300]}")
    vid = r.json()["id"]
    st = requests.get(f"{YT}/videos", headers={"Authorization": f"Bearer {tok}"}, params={"part": "status", "id": vid},
                      timeout=60).json()["items"][0]["status"]
    if st.get("privacyStatus") != "public":
        sys.exit(f"FALLO: subido como https://youtu.be/{vid} pero su estado es {st}")
    print(f"Subido y público: https://youtu.be/{vid}")


if __name__ == "__main__":
    main()
