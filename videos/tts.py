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
# Formato quiz: desde el 27 nov 2026, voz en castellano de España, como el resto de vídeos (decisión de Adrià:
# nada de español neutro ni latino, aunque gran parte del público sea de América). Mismas voces que la frase célebre.
VOCES_QUIZ = {"m": "Koda", "f": "Kore"}
ESTILO_QUIZ = ("A real person from Spain telling a friend a curious fact over coffee. Native Castilian Spanish "
               "accent from Spain (peninsular Spanish), never Latin American or neutral Spanish. "
               "Not a narrator, not an announcer, not an advert. Relaxed, warm and "
               "close to the microphone, with natural breathing. Unhurried and very clear, because many listeners "
               "are older. Ask the opening question with genuine curiosity; read the quote slower, savouring it; "
               "say the three options as a playful little quiz; reveal the author's name with a hint of a smile.")
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


def _interactions(modelo, voz, texto, estilo=None):
    d = _post(f"{API}/interactions", {
        "model": modelo,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": texto,
            "annotations": [{"type": "speech_metadata", "style": estilo or ESTILO}]}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voz}]}})
    audios = [c for s in d.get("steps", []) if s.get("type") == "model_output"
              for c in s.get("content", []) if c.get("type") == "audio" and c.get("data")]
    if not audios:
        raise RuntimeError("la respuesta no trae audio: " + json.dumps(d)[:200])
    datos = base64.b64decode(audios[-1]["data"])
    return datos if datos[:4] == b"RIFF" else _wav(datos)


def _generate(modelo, voz, texto, estilo=None):
    """Plan B: la llamada clásica (la del botón «Get code» de AI Studio)."""
    d = _post(f"{API}/models/{modelo}:generateContent", {
        "contents": [{"role": "user", "parts": [{"text": f"## Style:\n{estilo or ESTILO}\n\n## Transcript:\n{texto}"}]}],
        "generationConfig": {"temperature": 1, "responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}})
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
    return _wav(base64.b64decode(part["data"]), int(m.group(1)) if m else 24000)


def gemini(voz, texto, estilo=None, solo_principal=False):
    """Devuelve (wav en bytes, modelo). Como mucho 3 audios por minuto: 21 s entre peticiones.
    solo_principal: no usa el modelo «lite» (el quiz necesita la voz buena; sin cupo, se reintenta otro día)."""
    global _ultima
    if not CLAVE:
        raise SinVoz("falta el secret GEMINI_API_KEY")
    errores = []
    for modelo in (MODELOS[:1] if solo_principal else MODELOS):
        if modelo in _agotados:
            continue
        for forma in (_interactions, _generate):
            falta = 21 - (time.time() - _ultima)
            if falta > 0:
                time.sleep(falta)
            _ultima = time.time()
            try:
                return forma(modelo, voz, texto, estilo), modelo
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


def alinear_palabras(x, trozos, modelo="medium"):
    """Formato quiz: segundo en que empieza cada token (norm) de cada trozo. Whisper «medium» con el guion como
    pista acierta los nombres propios («base» confundía «Quevedo»). Al modelo se le pasa el audio en memoria.
    Devuelve [[t, t, ...] por trozo]; los tokens que no encuentra se interpolan."""
    from faster_whisper import WhisperModel
    x16 = np.interp(np.linspace(0, len(x) - 1, int(len(x) * 16000 / SR)), np.arange(len(x)), x).astype(np.float32)
    m = WhisperModel(modelo, device="cpu", compute_type="int8")
    guion, de_trozo = [], []
    for k, t in enumerate(trozos):
        for tok in norm(t):
            guion.append(tok)
            de_trozo.append(k)
    # Con el guion como pista, a veces Whisper da por dicho casi todo y solo transcribe el final (23 nov 2026,
    # vídeo largo): entonces se repite sin pista y se queda el intento que más palabras reconoce.
    mejor = None
    for pista in (" ".join(trozos)[:400], None):
        segs, _ = m.transcribe(x16, language="es", word_timestamps=True, initial_prompt=pista)
        oidas, t_oidas = [], []
        for s in segs:
            for w in (s.words or []):
                for tok in norm(w.word):
                    oidas.append(tok)
                    t_oidas.append(w.start)
        tiempos = [None] * len(guion)
        for blk in difflib.SequenceMatcher(None, guion, oidas, autojunk=False).get_matching_blocks():
            for q in range(blk.size):
                tiempos[blk.a + q] = t_oidas[blk.b + q]
        conocidos = [i for i, t in enumerate(tiempos) if t is not None]
        if mejor is None or len(conocidos) > len(mejor[1]):
            mejor = (tiempos, conocidos, oidas)
        if len(conocidos) >= len(guion) * 0.6:
            break
    tiempos, conocidos, oidas = mejor
    if len(conocidos) < len(guion) * 0.6:
        raise RuntimeError(f"Whisper no reconoce bien la voz: se repite otro día ({len(conocidos)}/{len(guion)} palabras; "
                           f"oyó: {' '.join(oidas)[:300]})")
    for i in range(len(guion)):
        if tiempos[i] is None:
            antes = max((j for j in conocidos if j < i), default=None)
            despues = min((j for j in conocidos if j > i), default=None)
            if antes is None:
                tiempos[i] = tiempos[despues]
            elif despues is None:
                tiempos[i] = tiempos[antes] + 0.3 * (i - antes)
            else:
                tiempos[i] = tiempos[antes] + (tiempos[despues] - tiempos[antes]) * (i - antes) / (despues - antes)
    return [[round(float(tiempos[i]), 3) for i in range(len(guion)) if de_trozo[i] == k] for k in range(len(trozos))]


def sintetizar_quiz(trozos, grupos, carpeta, voz="m"):
    """Formato quiz. `trozos` = textos que lee la voz; `grupos` = nº de trozos de cada parte del vídeo
    (gancho, cita, opciones, autor). Un solo audio de Gemini (prosodia natural) que se corta en las pausas
    entre partes. Guarda <carpeta>/{gancho,cita,opciones,autor}.wav y devuelve, por parte, su duración y el
    segundo (dentro de su archivo) de cada token. Lanza SinVoz si no hay voz."""
    if DIFERIR is not None:  # 1.ª pasada de generar.py: solo se apunta el texto (ver precargar_quiz)
        limpios = [texto_voz(t) for t in trozos]
        texto = " ".join(t if re.search(r"[.,;:?!…]$", t) else t + "." for t in limpios)
        clave = hashlib.sha1(f"quiz|{VOCES_QUIZ[voz]}|{ESTILO_QUIZ}|{texto}".encode()).hexdigest()[:20]
        if not os.path.exists(os.path.join(CACHE, f"{clave}.wav")):
            DIFERIR.append((clave, voz, trozos))
            raise SinVoz("voz diferida: se pide junto con otros Shorts")
    return sintetizar_partes(trozos, grupos, ("gancho", "cita", "opciones", "autor"), carpeta,
                             VOCES_QUIZ[voz], ESTILO_QUIZ, "quiz")


# Varios Shorts en un solo audio (24 nov 2026). El cupo gratis es de 10 PETICIONES al día, no de 10 vídeos: se
# piden hasta POR_LOTE Shorts de la misma voz en una petición, se corta por las pausas entre Shorts y cada trozo
# se guarda en la caché con la clave que buscará sintetizar_quiz (que así no gasta otra petición).
DIFERIR = None
POR_LOTE = 8  # ~2 min de audio por petición


def precargar_quiz(pendientes):
    """`pendientes` = [(clave de caché, voz «m»/«f», trozos)]. Devuelve cuántos Shorts quedan con voz en caché."""
    hechos = 0
    for voz in ("m", "f"):
        suyos = [p for p in pendientes if p[1] == voz]
        for i in range(0, len(suyos), POR_LOTE):
            lote = suyos[i:i + POR_LOTE]
            trozos = [t for _, _, ts in lote for t in ts]
            try:
                sintetizar_partes(trozos, [len(ts) for _, _, ts in lote], [c for c, _, _ in lote], CACHE,
                                  VOCES_QUIZ[voz], ESTILO_QUIZ, "quizlote")
                hechos += len(lote)
                print(f"  voz en lote: {len(lote)} Shorts ({VOCES_QUIZ[voz]}) en 1 petición", flush=True)
            except SinVoz as e:
                print(f"  sin voz para el lote: {str(e)[:120]}", flush=True)
                return hechos
            except Exception as e:  # p. ej. Whisper no separa bien los Shorts: esos se harán uno a uno
                print(f"  lote de voz descartado ({str(e)[:120]}); esos Shorts se harán uno a uno", flush=True)
    return hechos


def sintetizar_partes(trozos, grupos, nombres, carpeta, voz_nombre, estilo, prefijo):
    """Un audio de Gemini con todos los trozos, cortado en partes (`grupos` = nº de trozos de cada parte) por
    las pausas. Guarda <carpeta>/<nombre>.wav por parte y devuelve {nombre: {dur, tokens, trozos}}, con
    `trozos` = (inicio, fin) de cada trozo dentro de su parte. Lanza SinVoz si no hay voz."""
    limpios = [texto_voz(t) for t in trozos]
    texto = " ".join(t if re.search(r"[.,;:?!…]$", t) else t + "." for t in limpios)
    clave = hashlib.sha1(f"{prefijo}|{voz_nombre}|{estilo}|{texto}".encode()).hexdigest()[:20]
    ruta_cache = os.path.join(CACHE, f"{clave}.wav")
    if os.path.exists(ruta_cache):
        datos, modelo = open(ruta_cache, "rb").read(), "caché"
    else:
        datos, modelo = gemini(voz_nombre, texto, estilo=estilo, solo_principal=True)
        os.makedirs(CACHE, exist_ok=True)
        open(ruta_cache, "wb").write(datos)
    x, sr = sf.read(io.BytesIO(datos), dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.012)[0]
    if len(idx):
        x = x[max(idx[0] - int(0.02 * SR), 0):min(idx[-1] + int(0.06 * SR), len(x))]
    if len(x) < int(0.5 * SR):  # 25 nov 2026: un trozo de lote mal cortado (vacío): se borra y se pide de nuevo
        if modelo == "caché":
            os.remove(ruta_cache)
        raise RuntimeError(f"audio vacío o demasiado corto ({len(x) / SR:.2f} s); se pedirá de nuevo")
    x = (x / (np.max(np.abs(x)) + 1e-6) * 0.9).astype(np.float32)
    try:
        por_trozo = alinear_palabras(x, limpios)
    except Exception:
        if modelo == "caché":  # audio guardado que no vale (p. ej. mal cortado de un lote): se pedirá de nuevo
            os.remove(ruta_cache)
        if os.environ.get("DEPURAR_VOZ"):  # guarda el audio para escucharlo/revisarlo
            os.makedirs(os.environ["DEPURAR_VOZ"], exist_ok=True)
            sf.write(os.path.join(os.environ["DEPURAR_VOZ"], f"fallo-{clave}.wav"), x, SR, subtype="PCM_16")
        raise
    # Partes: se corta a mitad de la pausa entre la última palabra de una parte y la primera de la siguiente
    partes, k = [], 0
    for n in grupos:
        partes.append(list(range(k, k + n)))
        k += n
    def ini(p):
        return next(t for i in p for t in por_trozo[i][:1])
    def fin_aprox(p):
        return max(t for i in p for t in por_trozo[i][-1:])
    cortes = [0.0]
    for a, b in zip(partes, partes[1:]):
        fa, ib = fin_aprox(a), ini(b)
        # el último token empieza en fa: la pausa está entre fa+0.25 y ib
        cortes.append(max(fa + 0.25, (fa + 0.25 + ib) / 2) if ib > fa + 0.25 else ib - 0.02)
    cortes.append(len(x) / SR)
    res = {}
    for nombre, p, a, b in zip(nombres, partes, cortes, cortes[1:]):
        trozo = x[int(a * SR):int(b * SR)].copy()
        f = int(0.015 * SR)  # microfundidos para que el corte no haga clic
        if len(trozo) > 2 * f:
            trozo[:f] *= np.linspace(0, 1, f)
            trozo[-f:] *= np.linspace(1, 0, f)
        if len(trozo) < int(0.5 * SR) or np.sqrt(np.mean(trozo ** 2)) < 0.005:
            raise RuntimeError(f"el trozo «{nombre}» ha quedado en silencio")
        sf.write(os.path.join(carpeta, f"{nombre}.wav"), trozo, SR, subtype="PCM_16")
        res[nombre] = {"dur": round(b - a, 3), "tokens": [round(t - a, 3) for i in p for t in por_trozo[i]],
                       "trozos": [(round(max(por_trozo[i][0] - a, 0), 3) if por_trozo[i] else 0.0,
                                   round(min(por_trozo[i][-1] - a + 0.35, b - a), 3) if por_trozo[i] else 0.0) for i in p]}
    ULTIMO.update(modelo=modelo, metodo="Whisper medium", voz=voz_nombre)
    return res


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
