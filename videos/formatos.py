"""Motor de los formatos nuevos (fase 3.1, 27 nov 2026). No toca Airtable ni publica nada.

Uso: python videos/formatos.py ficha1.json [ficha2.json …]  →  salida/<id>.mp4 (+ <id>.props.json)

Cada ficha describe un vídeo:
  {"id": "lodijo_einstein", "composicion": "LoDijo",
   "voz": {"nombre": "Koda", "estilo": "…", "texto": "¿Sabías que… ⟦giro⟧nunca la dijo Einstein? ⟦cita⟧La locura … diferentes.⟦/cita⟧ …"},
   "musica": 11,
   "imagenes": [{"destino": "gen/einstein.jpg", "commons": "File:Albert Einstein Head.jpg"}],
   "props": {… "t": {"cita": "@cita", …}, "citaIdx": "@cita.idx", "voz": "@voz", "musica": "@musica" …}}

Marcas del guion: ⟦nombre⟧ va delante de la palabra donde empieza algo; ⟦/nombre⟧ detrás de la última palabra de un
tramo (p. ej. una cita). En «props», cualquier texto «@nombre» se cambia por el segundo en que empieza, «@nombre.idx»
por [primera, última] palabra del tramo, «@voz» por {archivo, dur, palabras} y «@musica» por la ruta de la música.

Los tiempos salen de Whisper (cada palabra) y se AJUSTAN A LAS PAUSAS REALES del audio: Whisper suele adelantar la
primera palabra tras una pausa, y así el tambor, los sellos y los cambios de escena caen justo cuando toca.
La voz se guarda en caché (cache/voces): volver a renderizar sin cambiar el guion no gasta voz."""
import difflib, glob, hashlib, io, json, os, re, shutil, subprocess, sys, unicodedata, urllib.parse, wave

import numpy as np
import requests

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

REMOTION = os.path.join(RAIZ, "remotion")
PUB = os.path.join(REMOTION, "public")
CACHE = os.path.join(RAIZ, "cache", "voces")
SALIDA = os.path.join(RAIZ, "salida")
UA = {"User-Agent": "DichoYHechoBot/1.1 (https://www.instagram.com/dichoyhechoo_/) GitHubActions"}
MARCA = re.compile(r"⟦(/?)([\w.]+)⟧")
COLA = 3.2  # segundos de música tras la voz (cierre animado)


# ---------------------------------------------------------------- guion y marcas
def partir(texto):
    """→ (texto limpio para la voz, palabras del guion, {marca: índice de inicio}, {marca: índice de fin})."""
    inicios, fines, palabras = {}, {}, []
    for trozo in texto.split():
        pre = trozo
        while True:  # marcas delante de la palabra
            m = MARCA.match(pre)
            if not m:
                break
            if m.group(1):
                fines[m.group(2)] = len(palabras) - 1
            else:
                inicios[m.group(2)] = len(palabras)
            pre = pre[m.end():]
        cierres = [m for m in MARCA.finditer(pre)]
        limpio = MARCA.sub("", pre)
        if limpio:
            palabras.append(limpio)
        for m in cierres:  # marcas pegadas detrás
            (fines if m.group(1) else inicios)[m.group(2)] = len(palabras) - (1 if m.group(1) else 0)
    limpio = MARCA.sub("", texto)
    return limpio, palabras, inicios, fines


def norm(p):
    p = unicodedata.normalize("NFKD", p.lower())
    return "".join(c for c in p if c.isalnum())


# ---------------------------------------------------------------- voz, palabras y pausas
def voz(ficha):
    v = ficha["voz"]
    limpio = MARCA.sub("", v["texto"])
    clave = hashlib.sha1(f"formatos|{v['nombre']}|{v.get('estilo', '')}|{limpio}".encode()).hexdigest()[:20]
    os.makedirs(CACHE, exist_ok=True)
    ruta = os.path.join(CACHE, f"{clave}.wav")
    if os.path.exists(ruta):
        print(f"  voz en caché ({clave})", flush=True)
    else:
        import tts  # solo hace falta si no está en caché
        datos, modelo = tts.gemini(v["nombre"], limpio, estilo=v.get("estilo"), solo_principal=True)
        with open(ruta, "wb") as f:
            f.write(datos)
        print(f"  voz nueva: {v['nombre']} ({modelo})", flush=True)
    return ruta


def leer_wav(ruta):
    with wave.open(ruta) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return x, sr


def pausas(x, sr, minimo=0.2):
    """[(inicio, fin)] de los silencios de al menos `minimo` segundos."""
    h = int(sr * 0.05)
    rms = np.array([np.sqrt(np.mean(x[i:i + h] ** 2)) for i in range(0, len(x) - h, h)])
    umbral = rms.max() * 0.04
    out, ini = [], None
    for k, v in enumerate(rms):
        if v < umbral and ini is None:
            ini = k
        elif v >= umbral and ini is not None:
            if (k - ini) * 0.05 >= minimo:
                out.append((ini * 0.05, k * 0.05))
            ini = None
    return out


_modelo = None


def whisper(x, sr):
    global _modelo
    from faster_whisper import WhisperModel
    if _modelo is None:
        _modelo = WhisperModel(os.environ.get("WHISPER", "medium"), device="cpu", compute_type="int8")
    x16 = np.interp(np.arange(0, len(x), sr / 16000), np.arange(len(x)), x).astype(np.float32)
    segs, _ = _modelo.transcribe(x16, language="es", word_timestamps=True, vad_filter=False)
    return [{"w": p.word.strip(), "a": float(p.start), "b": float(p.end)} for s in segs for p in s.words]


def alinear(guion, oidas):
    """Tiempo de cada palabra del GUION a partir de lo que oyó Whisper (que puede partir o juntar palabras)."""
    a = [norm(p) for p in guion]
    b = [norm(p["w"]) for p in oidas]
    tiempos = [None] * len(guion)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                tiempos[i1 + k] = (oidas[j1 + k]["a"], oidas[j1 + k]["b"])
        elif j2 > j1:  # reparte el tramo oído entre las palabras del guion
            ta, tb = oidas[j1]["a"], oidas[j2 - 1]["b"]
            n = i2 - i1
            for k in range(n):
                tiempos[i1 + k] = (ta + (tb - ta) * k / max(n, 1), ta + (tb - ta) * (k + 1) / max(n, 1))
    # huecos sin nada oído: interpola entre vecinos
    for i, v in enumerate(tiempos):
        if v is None:
            prev = next((tiempos[j] for j in range(i - 1, -1, -1) if tiempos[j]), (0, 0))
            sig = next((tiempos[j] for j in range(i + 1, len(tiempos)) if tiempos[j]), (prev[1] + 0.3, prev[1] + 0.6))
            tiempos[i] = (prev[1], sig[0])
    return tiempos


def ajustar(t, silencios, fin_anterior):
    """Si la palabra es la primera tras una pausa cercana, su inicio real es el final de esa pausa.
    `fin_anterior`: cuándo acaba la palabra de antes; si acaba después de la pausa, esa pausa no es la suya."""
    cand = [b for a, b in silencios if t - 0.4 <= b <= t + 0.9 and fin_anterior <= b + 0.05]
    return min(cand, key=lambda b: abs(b - t)) if cand else t


# ---------------------------------------------------------------- imágenes, música y render
def imagenes(ficha):
    for im in ficha.get("imagenes", []):
        destino = os.path.join(PUB, im["destino"])
        if os.path.exists(destino):
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=40, params={
            "action": "query", "titles": im["commons"], "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1280, "format": "json"})
        ii = next(iter(r.json()["query"]["pages"].values()))["imageinfo"][0]
        with open(destino, "wb") as f:
            f.write(requests.get(ii.get("thumburl") or ii["url"], headers=UA, timeout=60).content)
        print(f"  imagen: {im['destino']}", flush=True)


def sustituir(v, valores):
    if isinstance(v, str) and v.startswith("@"):
        if v[1:] not in valores:
            raise KeyError(f"falta la marca {v} en el guion")
        return valores[v[1:]]
    if isinstance(v, dict):
        return {k: sustituir(x, valores) for k, x in v.items()}
    if isinstance(v, list):
        return [sustituir(x, valores) for x in v]
    return v


def hacer(ruta_ficha):
    ficha = json.load(open(ruta_ficha, encoding="utf-8"))
    vid = ficha["id"]
    print(f"== {vid} ({ficha['composicion']})", flush=True)
    _, guion, inicios, fines = partir(ficha["voz"]["texto"])
    wav = voz(ficha)
    x, sr = leer_wav(wav)
    dur = len(x) / sr
    silencios = pausas(x, sr)
    tiempos = alinear(guion, whisper(x, sr))

    valores = {}
    desfase = [0.0] * len(guion)
    for nombre, i in inicios.items():
        i = min(i, len(guion) - 1)
        bruto = tiempos[i][0]
        bueno = round(ajustar(bruto, silencios, tiempos[i - 1][1] if i else 0.0), 3)
        valores[nombre] = bueno
        fin = fines.get(nombre, i)
        for k in range(i, fin + 1):  # el tramo entero se mueve con su inicio
            desfase[k] = bueno - bruto
        if nombre in fines:
            valores[f"{nombre}.idx"] = [i, fines[nombre]]
    palabras = [{"w": w, "a": round(a + d, 3), "b": round(b + d, 3)} for w, (a, b), d in zip(guion, tiempos, desfase)]

    gen = os.path.join(PUB, "gen")
    valores["voz"] = {"archivo": f"gen/{vid}.wav", "dur": round(dur, 3), "palabras": palabras}
    valores["musica"] = f"gen/{vid}_musica.wav"
    props = sustituir(ficha["props"], valores)

    os.makedirs(SALIDA, exist_ok=True)
    rprops = os.path.join(SALIDA, f"{vid}.props.json")
    json.dump(props, open(rprops, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  marcas: " + ", ".join(f"{k}={v}" for k, v in valores.items() if not isinstance(v, (dict, str))), flush=True)
    if os.environ.get("SIN_RENDER"):  # prueba: solo tiempos y props
        return
    os.makedirs(gen, exist_ok=True)
    shutil.copy(wav, os.path.join(gen, f"{vid}.wav"))
    subprocess.run([sys.executable, os.path.join(AQUI, "musica.py"), os.path.join(gen, f"{vid}_musica.wav"), f"{dur + COLA:.1f}", str(ficha.get("musica", 7))], check=True, stdout=subprocess.DEVNULL)
    if not os.path.exists(os.path.join(PUB, "sfx", "golpe.wav")):
        subprocess.run([sys.executable, os.path.join(AQUI, "sfx.py"), os.path.join(PUB, "sfx")], check=True, stdout=subprocess.DEVNULL)
    imagenes(ficha)
    salida = os.path.join(SALIDA, f"{vid}.mp4")
    subprocess.run(["npx", "remotion", "render", "src/index.ts", ficha["composicion"], salida, f"--props={rprops}",
                    "--crf=26", "--log=error", "--concurrency=2"], cwd=REMOTION, check=True)
    print(f"  OK {salida} ({os.path.getsize(salida) / 1e6:.1f} MB, {dur:.1f} s de voz)", flush=True)


if __name__ == "__main__":
    fichas = [f for a in sys.argv[1:] for f in sorted(glob.glob(a))]
    fallos = []
    for f in fichas:
        try:
            hacer(f)
        except Exception as e:  # una ficha mala no para las demás
            print(f"  FALLO {f}: {e}", flush=True)
            fallos.append(f)
    if fallos:
        sys.exit(f"{len(fallos)} ficha(s) con fallo: {', '.join(fallos)}")
