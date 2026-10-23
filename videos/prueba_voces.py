"""Prueba de voces (fase V2, 23 oct 2026). No toca Airtable ni publica nada.

Lee el mismo texto (gancho + cita + autor) con varias voces de Gemini en estilo «narrador» y, para
comparar, con las voces de Piper que se usan ahora. Guarda un MP3 por voz en la carpeta pruebas_voz/.
Gasta como mucho 1 audio de Gemini por voz (límite gratis: 3 por minuto y 10 al día por modelo).

Variables: GEMINI_API_KEY (secret), VOCES_M y VOCES_F (opcional: nombres separados por comas),
ESTILO (opcional)."""
import base64, io, json, os, re, subprocess, sys, time, wave
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import gancho, frases, texto_voz

CLAVE = os.environ.get("GEMINI_API_KEY", "")
API = "https://generativelanguage.googleapis.com/v1beta"
MODELOS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]
ESTILO = os.environ.get("ESTILO") or (
    "Calm, warm documentary narrator. Native Castilian Spanish accent from Spain. "
    "Sincere and thoughtful, natural pauses between sentences, never sounds like an advert.")
VOCES_M = [v.strip() for v in (os.environ.get("VOCES_M") or "Koda,Ludo,Mako,Charon,Orus").split(",") if v.strip()]
VOCES_F = [v.strip() for v in (os.environ.get("VOCES_F") or "Kira,Kore,Sulafat,Aoede").split(",") if v.strip()]

# Dos citas del banco: un autor (Orden 27) y una autora (Orden 5)
EJEMPLOS = {
    "m": ("Viktor Frankl", "Cuando ya no podemos cambiar una situación, tenemos el desafío de cambiarnos a nosotros mismos.",
          "El hombre en busca de sentido (1946)"),
    "f": ("Marie Curie", "Uno nunca se fija en lo que ya ha hecho; solo puede ver lo que queda por hacer.",
          "Carta a su hermano Józef, 18 de marzo de 1894"),
}
SALIDA = "pruebas_voz"
_ultima = 0.0


def guion(autor, cita, fuente):
    g, _ = gancho(autor, fuente)
    return [g] + frases(cita) + [autor + "."]


def _post(url, cuerpo):
    r = requests.post(url, json=cuerpo, timeout=180,
                      headers={"x-goog-api-key": CLAVE, "Content-Type": "application/json"})
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


def _wav(pcm, sr=24000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)
    return buf.getvalue()


def _interactions(modelo, voz, texto):
    d = _post(f"{API}/interactions", {
        "model": modelo,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": texto,
            "annotations": [{"type": "speech_metadata", "style": ESTILO}]}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voz}]}})
    audios = [c for s in d.get("steps", []) if s.get("type") == "model_output"
              for c in s.get("content", []) if c.get("type") == "audio" and c.get("data")]
    if not audios:
        raise RuntimeError("sin audio: " + json.dumps(d)[:200])
    datos = base64.b64decode(audios[-1]["data"])
    return datos if datos[:4] == b"RIFF" else _wav(datos)


def _generate(modelo, voz, texto):
    d = _post(f"{API}/models/{modelo}:generateContent", {
        "contents": [{"role": "user", "parts": [{"text": f"## Style:\n{ESTILO}\n\n## Transcript:\n{texto}"}]}],
        "generationConfig": {"temperature": 1, "responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}})
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
    return _wav(base64.b64decode(part["data"]), int(m.group(1)) if m else 24000)


def gemini(voz, texto):
    global _ultima
    errores = []
    for modelo in MODELOS:
        for forma in (_interactions, _generate):
            falta = 21 - (time.time() - _ultima)
            if falta > 0:
                time.sleep(falta)
            _ultima = time.time()
            try:
                return forma(modelo, voz, texto), modelo
            except Exception as e:
                errores.append(f"{modelo}/{forma.__name__}: {str(e)[:200]}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    break
                if re.search(r"voice|voz", str(e), re.I) and "400" in str(e):
                    raise RuntimeError(f"la voz «{voz}» no existe: {str(e)[:200]}")
    raise RuntimeError(" | ".join(errores))


def a_mp3(wav_bytes, ruta):
    tmp = ruta + ".wav"
    open(tmp, "wb").write(wav_bytes)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-b:a", "128k", ruta], check=True)
    os.remove(tmp)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    filas = []
    # Las de ahora (Piper), para comparar
    try:
        from tts import sintetizar
        for g, (autor, cita, fuente) in EJEMPLOS.items():
            nombre = "davefx" if g == "m" else "sharvard"
            ruta_wav = os.path.join(SALIDA, "tmp.wav")
            sintetizar(guion(autor, cita, fuente), ruta_wav, os.path.join(SALIDA, "tmp.json"), voz=g, rapido=(0,))
            a_mp3(open(ruta_wav, "rb").read(), os.path.join(SALIDA, f"{g}-0-ahora-piper-{nombre}.mp3"))
            os.remove(ruta_wav); os.remove(os.path.join(SALIDA, "tmp.json"))
            filas.append(f"| {autor} | Piper {nombre} (la de ahora) | ok |")
    except Exception as e:
        filas.append(f"| — | Piper | error: {str(e)[:150]} |")

    if not CLAVE:
        sys.exit("Falta el secret GEMINI_API_KEY")
    for g, voces in (("m", VOCES_M), ("f", VOCES_F)):
        autor, cita, fuente = EJEMPLOS[g]
        trozos = [texto_voz(t) for t in guion(autor, cita, fuente)]
        texto = " ".join(t if re.search(r"[.,;:?!…]$", t) else t + ":" for t in trozos)  # pausa tras el gancho
        for i, voz in enumerate(voces, 1):
            try:
                wav, modelo = gemini(voz, texto)
                a_mp3(wav, os.path.join(SALIDA, f"{g}-{i}-gemini-{voz.lower()}.mp3"))
                res = f"ok ({modelo})"
            except Exception as e:
                res = f"error: {str(e)[:200]}"
            print(f"{autor} · {voz}: {res}", flush=True)
            filas.append(f"| {autor} | Gemini {voz} | {res} |")

    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as f:
            f.write(f"### Prueba de voces\n\nEstilo: {ESTILO}\n\n| Cita | Voz | Resultado |\n|---|---|---|\n"
                    + "\n".join(filas) + "\n")
    print("\n".join(filas))


if __name__ == "__main__":
    main()
