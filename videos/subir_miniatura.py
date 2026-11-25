"""Pone una miniatura a un vídeo de YouTube (25 nov 2026).
Uso: python3 subir_miniatura.py <video_id> <imagen.jpg>
Necesita que el canal tenga activadas las funciones intermedias (verificación por teléfono)."""
import sys

import requests

from subir_youtube import YT, token


def main():
    vid, ruta = sys.argv[1], sys.argv[2]
    tok = token()
    datos = open(ruta, "rb").read()
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set", timeout=120,
                      params={"videoId": vid, "uploadType": "media"},
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"}, data=datos)
    if r.status_code >= 400:
        sys.exit(f"FALLO: {r.status_code}: {r.text[:500]}")
    print("Miniatura puesta:", r.json().get("items", [{}])[0].get("maxres", r.json()))
    print(f"https://youtu.be/{vid}")


if __name__ == "__main__":
    main()
