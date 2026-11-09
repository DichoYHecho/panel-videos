"""Prueba del aviso «Síguenos» (solo en la rama cta-sigenos).
Monta un vídeo de muestra con render.py: voz y música falsas (silencio y un tono suave, sin gastar Gemini),
una foto de Wikipedia y los tiempos de una cita corta. No toca Airtable ni ninguna red social.
Salida (carpeta prueba_cta/): muestra.mp4, hoja.png (todo el vídeo) y hoja_cta.png (zoom a la parte de arriba)."""
import json, os, subprocess, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from comun import frases

OUT = "prueba_cta"
os.makedirs(OUT, exist_ok=True)
cita = "No es que tengamos poco tiempo, sino que perdemos mucho."
autor = "Séneca"
UA = {"User-Agent": "DichoYHechoBot/1.1"}

foto = None
try:
    req = urllib.request.Request("https://es.wikipedia.org/api/rest_v1/page/summary/S%C3%A9neca", headers=UA)
    src = json.load(urllib.request.urlopen(req, timeout=30))["originalimage"]["source"]
    req = urllib.request.Request(src, headers=UA)
    open(f"{OUT}/foto.jpg", "wb").write(urllib.request.urlopen(req, timeout=60).read())
    foto = f"{OUT}/foto.jpg"
except Exception as e:
    print("sin foto (se usa el fondo neutro):", e)

# tiempos de voz inventados: gancho 2,4 s, unos 0,32 s por palabra en cada frase, autor 1 s
fr = frases(cita)
tv = [{"ini": 0.0, "fin": 2.4}]
t = 2.7
for f in fr:
    d = 0.32 * len(f.split()) + 0.4
    tv.append({"ini": round(t, 2), "fin": round(t + d, 2)})
    t += d + 0.25
tv.append({"ini": round(t, 2), "fin": round(t + 1.0, 2)})
json.dump(tv, open(f"{OUT}/voz.json", "w"))
total = t + 4

run = lambda *a: subprocess.run(list(a), check=True)
run("ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(total), f"{OUT}/voz.wav")
run("ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=196:duration={total}",
    "-ac", "2", "-ar", "44100", f"{OUT}/musica.wav")

cfg = {"cita": cita, "autor": autor, "fuente": "Cartas a Lucilio", "quien": "Filósofo estoico romano",
       "credito": "Foto: Wikipedia (prueba)", "voz_json": f"{OUT}/voz.json", "voz_wav": f"{OUT}/voz.wav",
       "musica": f"{OUT}/musica.wav", "salida": f"{OUT}/muestra.mp4"}
if foto:
    cfg["foto"] = foto
json.dump(cfg, open(f"{OUT}/config.json", "w"), ensure_ascii=False)
run(sys.executable, os.path.join(AQUI, "render.py"), f"{OUT}/config.json")

# hojas de fotogramas para verlo sin descargar el vídeo
run("ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/muestra.mp4", "-vf", "fps=2,scale=270:-1,tile=8x3",
    "-frames:v", "1", f"{OUT}/hoja.png")
run("ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/muestra.mp4", "-vf",
    "fps=5,crop=900:200:90:200,scale=450:-1,tile=4x10", "-frames:v", "1", f"{OUT}/hoja_cta.png")
os.remove(f"{OUT}/foto.jpg") if foto else None
print("listo", os.path.getsize(f"{OUT}/muestra.mp4") / 1e6, "MB")
