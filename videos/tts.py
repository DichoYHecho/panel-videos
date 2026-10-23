"""Voz del vídeo y tiempos de cada trozo (gancho, frases de la cita y autor) para los subtítulos.

Fase V2 (23 oct 2026): voz de Gemini, mucho más natural que la de antes (Piper).
- Autor: «Koda». Autora: «Kore». Estilo: narrador de documental tranquilo, acento de España.
- Un solo audio por vídeo con todo el texto. Límite gratis: 3 audios por minuto y 10 al día por
  modelo; se prueban 2 modelos (20 al día en total).
- Los tiempos de cada trozo se sacan con Whisper (transcripción gratuita, dentro de GitHub) y, si
  falla, por las pausas de la voz.
- Si Gemini no da la voz (cupo del día agotado, saturación…), se lanza SinVoz: ese vídeo no se hace
  y la repesca diaria lo reintenta. Decidido el 23 oct: nunca se usa la voz robótica de reserva.
- Los audios se guardan en cache/voces (caché de GitHub): si rehago un vídeo sin cambiar la frase,
  no se gasta otro audio."""
import base64, difflib, hashlib, io, json, os, re, time, unicodedata, wave
import numpy as np, requests, soundfile as sf
from comun import texto_voz

SR = 24000
CLAVE = os.environ.get("GEMINI_API_KEY", "")
API = "https://generativelanguage.googleapis.com/v1beta"
MODELOS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]
VOCES = {"m": "Koda", "f": "Kore"}
ESTILO = ("Calm, warm documentary narrator. Native Castilian Spanish accent from Spain. "
          "Sincere and thoughtful, natural pauses between sentences, never sounds like an advert.")
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "voces")
_ultima = 0.0
_agotados = set()   # modelos sin cupo en esta ejecución
ULTIMO = {}         # datos de la última voz (modelo y método de los subtítulos), para el resumen


class SinVoz(Exception):
    pass


# ---------------------------------------------------------------- Gemini
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
        raise RuntimeError("la respuesta no trae audio: " + json.dumps(d)[:200])
    datos = base64.b64decode(audios[-1]["data"])
    return datos if datos[:4] == b"RIFF" else _wav(datos)


def _generate(modelo, voz, texto):
    """Plan B: la llamada clásica (la del botón «Get code» de AI Studio)."""
    d = _post(f"{API}/models/{modelo}:generateContent", {
        "contents": [{"role": "user", "parts": [{"text": f"## Style:\n{ESTILO}\n\n## Transcript:\n{texto}"}]}],
        "generationConfig": {"temperature": 1, "responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}})
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
    return _wav(base64.b64decode(part["data"]), int(m.group(1)) if m else 24000)


def gemini(voz, texto):
    """Devuelve (wav en bytes, modelo). Como mucho 3 audios por minuto: 21 s entre peticiones."""
    global _ultima
    if not CLAVE:
        raise SinVoz("falta el secret GEMINI_API_KEY")
    errores = []
    for modelo in MODELOS:
        if modelo in _agotados:
            continue
        for forma in (_interactions, _generate):
            falta = 21 - (time.time() - _ultima)
            if falta > 0:
                time.sleep(falta)
            _ultima = time.time()
            try:
                return forma(modelo, voz, texto), modelo
            except Exception as e:
                errores.append(f"{modelo}: {str(e)[:160]}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    _agotados.add(modelo)  # cupo agotado: no se vuelve a probar en esta ejecución
                    break
    raise SinVoz("; ".join(errores) or "cupo de voz agotado hoy en los 2 modelos")


# ---------------------------------------------------------------- tiempos de los trozos
def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9ñ]+", s)


def pausas(x, minimo=0.10):
    win = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + win] ** 2)) for i in range(0, len(x) - win, win)])
    sil = e < max(e.max() * 0.03, 0.004)
    res, i = [], 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]:
                j += 1
            if (j - i) * 0.02 >= minimo:
                res.append((i * 0.02, j * 0.02))
            i = j
        else:
            i += 1
    return res


def por_pausas(x, trozos):
    """Plan B sin Whisper: reparte los trozos por longitud y los ajusta a la pausa más cercana."""
    p = pausas(x)
    dur = len(x) / SR
    ini = p[0][1] if p and p[0][0] == 0 else 0.0
    fin = p[-1][0] if p and p[-1][1] >= dur - 0.05 else dur
    L = [len(t.replace(" ", "")) + 3 for t in trozos]
    tot = sum(L)
    bordes, acc, ult = [ini], 0, ini
    for w in L[:-1]:
        acc += w
        e = ini + (fin - ini) * acc / tot
        cerca = [(a, b) for a, b in p if abs((a + b) / 2 - e) < 0.7 and a > ult]
        if cerca:
            a, b = min(cerca, key=lambda q: abs((q[0] + q[1]) / 2 - e))
            bordes += [a, b]
            ult = b
        else:
            bordes += [e, e]
            ult = e
    bordes.append(fin)
    return [(bordes[2 * i], bordes[2 * i + 1]) for i in range(len(trozos))]


def por_whisper(x, trozos):
    from faster_whisper import WhisperModel
    x16 = np.interp(np.linspace(0, len(x) - 1, int(len(x) * 16000 / SR)), np.arange(len(x)), x).astype(np.float32)
    modelo = WhisperModel("base", device="cpu", compute_type="int8")
    segs, _ = modelo.transcribe(x16, language="es", word_timestamps=True, vad_filter=False)
    oidas, t_oidas = [], []
    for s in segs:
        for w in (s.words or []):
            for tok in norm(w.word):
                oidas.append(tok)
                t_oidas.append((w.start, w.end))
    guion, de_trozo = [], []
    for k, t in enumerate(trozos):
        for tok in norm(t):
            guion.append(tok)
            de_trozo.append(k)
    if len(oidas) < len(guion) * 0.5:
        raise RuntimeError("Whisper entendió muy poco")
    tiempos = [None] * len(guion)
    for blk in difflib.SequenceMatcher(None, guion, oidas, autojunk=False).get_matching_blocks():
        for q in range(blk.size):
            tiempos[blk.a + q] = t_oidas[blk.b + q]
    conocidos = [i for i, t in enumerate(tiempos) if t]
    if len(conocidos) < len(guion) * 0.5:
        raise RuntimeError("el texto y lo que se oye no coinciden")
    for i in range(len(guion)):  # las palabras sin pareja se interpolan
        if tiempos[i] is None:
            antes = max((j for j in conocidos if j < i), default=None)
            despues = min((j for j in conocidos if j > i), default=None)
            if antes is None:
                tiempos[i] = (tiempos[despues][0], tiempos[despues][0])
            elif despues is None:
                tiempos[i] = (tiempos[antes][1], tiempos[antes][1])
            else:
                f = (i - antes) / (despues - antes)
                t = tiempos[antes][1] + (tiempos[despues][0] - tiempos[antes][1]) * f
                tiempos[i] = (t, t)
    out = []
    for k in range(len(trozos)):
        idx = [i for i, kk in enumerate(de_trozo) if kk == k]
        prev = out[-1][1] if out else 0.0
        out.append((tiempos[idx[0]][0], tiempos[idx[-1]][1]) if idx else (prev, prev))
    return out


def ordenar(t, dur):
    """Tiempos siempre en orden, sin solaparse y con al menos 0,2 s por trozo."""
    res, prev = [], 0.0
    for a, b in t:
        a = min(max(a, prev), dur)
        b = min(max(b, a + 0.2), dur)
        res.append((round(a, 3), round(b, 3)))
        prev = b
    return res


# ---------------------------------------------------------------- función principal
def sintetizar(trozos, out_wav, out_json, voz="m", rapido=()):
    """Lee los trozos (gancho, frases de la cita y autor) con la voz de Gemini y guarda el audio y
    los tiempos de cada trozo. `rapido` se mantiene por compatibilidad (Gemini marca su propio ritmo).
    Lanza SinVoz si Gemini no da la voz."""
    limpios = [texto_voz(t) for t in trozos]
    texto = " ".join(t if re.search(r"[.,;:?!…]$", t) else t + ":" for t in limpios)  # pausa tras el gancho
    # Caché: si el texto y la voz no han cambiado (p. ej. solo cambié «Quién era» o el crédito), se
    # reutiliza el audio y no se gasta otro del cupo de Gemini.
    clave = hashlib.sha1(f"{VOCES[voz]}|{ESTILO}|{texto}".encode()).hexdigest()[:20]
    ruta_cache = os.path.join(CACHE, f"{clave}.wav")
    if os.path.exists(ruta_cache):
        datos, modelo = open(ruta_cache, "rb").read(), "caché"
    else:
        datos, modelo = gemini(VOCES[voz], texto)
        os.makedirs(CACHE, exist_ok=True)
        open(ruta_cache, "wb").write(datos)
    x, sr = sf.read(io.BytesIO(datos), dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.012)[0]  # sin silencios al principio y al final
    if len(idx):
        x = x[max(idx[0] - int(0.02 * SR), 0):min(idx[-1] + int(0.06 * SR), len(x))]
    x = (x / (np.max(np.abs(x)) + 1e-6) * 0.9).astype(np.float32)
    sf.write(out_wav, x, SR, subtype="PCM_16")
    try:
        t, metodo = por_whisper(x, limpios), "Whisper"
    except Exception as e:
        print(f"  (subtítulos por pausas: {str(e)[:120]})", flush=True)
        t, metodo = por_pausas(x, limpios), "pausas"
    t = ordenar(t, len(x) / SR)
    tiempos = [{"texto": f, "ini": a, "fin": b} for f, (a, b) in zip(trozos, t)]
    json.dump(tiempos, open(out_json, "w"), ensure_ascii=False, indent=1)
    ULTIMO.update(modelo=modelo, metodo=metodo, voz=VOCES[voz])
    return tiempos
