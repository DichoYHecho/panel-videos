"""Voces para prototipos de formatos nuevos (fase 2, 27 nov 2026). No toca Airtable ni publica nada.

Lee prototipos/voces.json: [{"nombre": ..., "voz": "Koda", "estilo": ..., "texto": ...}, ...] y guarda un WAV por
entrada en pruebas_voz/. Cada entrada gasta 1 audio de Gemini (límite gratis: 3 por minuto)."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts

os.makedirs("pruebas_voz", exist_ok=True)
for e in json.load(open("prototipos/voces.json", encoding="utf-8")):
    wav, modelo = tts.gemini(e["voz"], e["texto"], estilo=e.get("estilo") or tts.ESTILO, solo_principal=True)
    ruta = os.path.join("pruebas_voz", e["nombre"] + ".wav")
    with open(ruta, "wb") as f:
        f.write(wav)
    print(f"OK {e['nombre']} ({e['voz']}, {modelo}) -> {ruta}", flush=True)
