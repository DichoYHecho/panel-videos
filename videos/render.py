"""Vídeo vertical 1080x1920 (formato B, desde el 11 de octubre de 2026).
- La voz lee el gancho desde el primer segundo y después la cita (subtítulos palabra a palabra).
- Al final: autor en amarillo, quién era, crédito de la foto (y de la voz, si toca).
- Sin tarjeta final: en los últimos 0,55 s se va la cita y vuelve el gancho, y el zoom de la foto
  es de ida y vuelta, así que el último fotograma coincide con el primero (bucle natural).
Python dibuja los fotogramas y FFmpeg codifica y mezcla el audio.
Uso: python3 render.py config.json"""
import glob, json, math, os, re, subprocess, sys
from comun import frases, gancho
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

W, H, FPS = 1080, 1920, 30
AMARILLO = (245, 197, 24)
BLANCO = (255, 255, 255)
GRIS = (210, 210, 210)
FD = next((d for d in ["/usr/share/fonts/opentype/inter/", os.path.join(os.path.dirname(__file__), "fuentes/")]
           if glob.glob(d + "Inter-Bold.*")), "/usr/share/fonts/opentype/inter/")
F_BOLD, F_SEMI, F_MED = FD + "Inter-Bold.otf", FD + "Inter-SemiBold.otf", FD + "Inter-Medium.otf"
TEXT_W, CX = 860, 530  # ancho útil y centro (algo a la izquierda por los botones de TikTok)
LOOP = 0.55            # segundos finales en los que se vuelve al primer fotograma

cfg = json.load(open(sys.argv[1]))


# ---------- Texto: maquetación por palabras ----------
class Palabra:
    def __init__(self, txt, font, color, x, base):
        self.txt, self.grupo, self.t_on = txt, 0, 0.0
        pad = 26
        x0, y0, x1, y1 = font.getbbox(txt, anchor="ls")
        im = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad - x0, pad - y0), txt, font=font, fill=color + (255,), anchor="ls")
        a = np.asarray(im, dtype=np.float32)[..., 3] / 255.0
        sh = gaussian_filter(np.roll(a, 4, axis=0), 7) * 0.6
        self.a = (a + sh * (1 - a))[..., None]
        self.c = np.array(color, np.float32)[None, None, :] / 255.0 * a[..., None]
        self.x, self.y = int(x + x0 - pad), int(base + y0 - pad)

    def pintar(self, F, op, dy=0):
        if op <= 0.003: return
        y = self.y + int(round(dy)); h, w = self.a.shape[:2]
        ya, yb, xa, xb = max(y, 0), min(y + h, H), max(self.x, 0), min(self.x + w, W)
        if ya >= yb or xa >= xb: return
        a = self.a[ya - y:yb - y, xa - self.x:xb - self.x] * op
        c = self.c[ya - y:yb - y, xa - self.x:xb - self.x] * op
        F[ya:yb, xa:xb] = F[ya:yb, xa:xb] * (1 - a) + c


def partir(tokens, font, ancho):
    esp = font.getlength(" ")
    lineas, cur, wcur = [], [], 0
    for t in tokens:
        w = font.getlength(t[0])
        if cur and wcur + esp + w > ancho:
            lineas.append((cur, wcur)); cur, wcur = [], 0
        wcur += (esp if cur else 0) + w; cur.append((t, w))
    if cur: lineas.append((cur, wcur))
    return lineas


def maquetar(tokens, font, ancho, cy, interlinea=1.24):
    """tokens = [(texto, color, grupo)]; líneas equilibradas, centradas en CX y en cy."""
    esp = font.getlength(" ")
    lineas = partir(tokens, font, ancho)
    lo, hi = ancho * 0.45, ancho  # el ancho mínimo que mantiene el mismo número de líneas
    for _ in range(14):
        mid = (lo + hi) / 2
        if len(partir(tokens, font, mid)) <= len(lineas): hi = mid
        else: lo = mid
    lineas = partir(tokens, font, hi)
    lh = font.size * interlinea
    alto = lh * len(lineas)
    base0 = cy - alto / 2 + font.size * 0.95
    out = []
    for i, (ln, lw) in enumerate(lineas):
        x = CX - lw / 2
        for (txt, color, g), w in ln:
            p = Palabra(txt, font, color, x, base0 + i * lh); p.grupo = g
            out.append(p); x += w + esp
    return out, alto


def ajustar(tokens, fichero, tam, minimo, alto_max, cy):
    while True:
        f = ImageFont.truetype(fichero, tam)
        pals, alto = maquetar(tokens, f, TEXT_W, cy)
        if alto <= alto_max or tam <= minimo: return pals, alto, f
        tam -= 4


def linea(texto, fichero, tam, color, top):
    """Texto (una línea, o varias si no cabe) que empieza en «top». Devuelve (palabras, y de abajo)."""
    if not texto: return [], top
    f = ImageFont.truetype(fichero, tam)
    toks = [(w, color, 0) for w in texto.split()]
    alto = f.size * 1.24 * len(partir(toks, f, TEXT_W))
    pals, _ = maquetar(toks, f, TEXT_W, top + alto / 2)
    return pals, top + alto


def tokens_gancho(texto, autor):
    """El nombre del autor en amarillo (y sin partir si es corto)."""
    i_a = texto.find(autor)
    if i_a < 0: return [(w, BLANCO, 0) for w in texto.split()]
    antes, despues = texto[:i_a].split(), texto[i_a + len(autor):]
    nombre = [autor.replace(" ", "\u00a0")] if len(autor) <= 18 else autor.split()
    if despues and not despues.startswith(" "):  # signo pegado al nombre («Séneca:»)
        pegado, _, despues = despues.partition(" ")
        nombre[-1] += pegado
    return ([(w, BLANCO, 0) for w in antes] + [(w, AMARILLO, 0) for w in nombre]
            + [(w, BLANCO, 0) for w in despues.split()])


def suave(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def rampa(t, a, d): return suave((t - a) / d)


# ---------- Datos y tiempos ----------
cita, autor = cfg["cita"], cfg["autor"]
fr = frases(cita)
g_txt, g_sub = gancho(autor, cfg.get("fuente", ""))
tv = json.load(open(cfg["voz_json"]))  # gancho + frases de la cita + autor
assert len(tv) == len(fr) + 2, "la voz no tiene gancho + frases + autor"
V0 = 0.12                               # la voz empieza casi en el primer fotograma
t_fin_gancho = V0 + tv[0]["fin"]
tv_cita = tv[1:-1]
ini = [V0 + v["ini"] for v in tv_cita]
t_autor = V0 + tv[-1]["ini"]
DUR = round(V0 + tv[-1]["fin"] + 1.05, 2)
N = int(DUR * FPS)
T_LOOP = (N - 1) / FPS - LOOP           # en el último fotograma ya se ha vuelto del todo al primero

# ---------- Capas de texto ----------
CY = 880
toks = []
for g, f in enumerate(fr):
    ws = f.split()
    for k, w in enumerate(ws):
        if g == 0 and k == 0: w = "“" + w
        if g == len(fr) - 1 and k == len(ws) - 1: w = w + "”"
        toks.append((w, BLANCO, g))
cita_p, alto_c, f_cita = ajustar(toks, F_BOLD, 80, 52, 700, CY)
for g, v in enumerate(tv_cita):  # cada palabra se ilumina cuando la lee la voz
    ps = [p for p in cita_p if p.grupo == g]
    pesos = np.array([len(re.sub(r"\W", "", p.txt)) + 2 for p in ps], float)
    acum = np.concatenate([[0], np.cumsum(pesos)[:-1]]) / pesos.sum()
    for p, a in zip(ps, acum):
        p.t_on = V0 + v["ini"] + a * (v["fin"] - v["ini"]) - 0.05

gancho_p, alto_g, _ = ajustar(tokens_gancho(g_txt, autor), F_BOLD, 76, 52, 440, CY - 60)
if g_sub:
    sub_p, _ = linea(g_sub, F_MED, 36, (215, 215, 215), CY - 60 + alto_g / 2 + 30)
    gancho_p += sub_p

fin_p, y = linea("— " + autor, F_SEMI, 50, AMARILLO, CY + alto_c / 2 + 40)
p2, y = linea(cfg.get("quien", ""), F_MED, 38, BLANCO, y + 4); fin_p += p2
p3, y = linea(cfg.get("credito", ""), F_MED, 32, GRIS, y + 18); fin_p += p3
p4, y = linea(cfg.get("credito_voz", ""), F_MED, 32, GRIS, y + 2); fin_p += p4

# ---------- Fondo: foto con zoom de ida y vuelta ----------
if cfg.get("foto"):
    foto = Image.open(cfg["foto"]).convert("RGB")
else:  # sin foto libre: fondo gris oscuro neutro
    g = np.linspace(70, 25, H, dtype=np.float32)[:, None, None] * np.ones((1, W, 3), np.float32)
    foto = Image.fromarray(g.astype(np.uint8))
ZMAX = 1.10
s0 = max(W / foto.width, H / foto.height) * ZMAX
S = foto.resize((round(foto.width * s0), round(foto.height * s0)), Image.LANCZOS)
fx, fy = cfg.get("foco", [0.5, 0.38])
yy = np.arange(H, dtype=np.float32)[:, None]
xx = np.arange(W, dtype=np.float32)[None, :]
grad = np.clip(0.5 + yy / 700, 0, 1) * np.clip(0.42 + (H - yy) / 820, 0, 1)
vig = 1 - 0.35 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.8)) ** 2)
MASK = (grad * vig)[..., None].astype(np.float32)


def fondo(t):
    z = 1.0 + (ZMAX - 1.0) * math.sin(math.pi * min(t / DUR, 1.0))
    r = z / ZMAX
    hw, hh = W / 2 / r, H / 2 / r
    cx = min(max(fx * S.width, hw), S.width - hw)
    cy = min(max(fy * S.height, hh), S.height - hh)
    im = S.transform((W, H), Image.AFFINE, (1 / r, 0, cx - hw, 0, 1 / r, cy - hh), Image.BILINEAR)
    dim = 0.58 - 0.16 * rampa(t, t_fin_gancho, 0.6) + 0.16 * rampa(t, T_LOOP, LOOP)
    return np.asarray(im, dtype=np.float32) / 255.0 * (MASK * dim)


# ---------- Audio (FFmpeg): fundidos cortos para el bucle ----------
aud = cfg["salida"].replace(".mp4", "_audio.wav")
d = int(V0 * 1000)
filt = (f"[0:a]atrim=0:{DUR},afade=t=in:d=0.25,afade=t=out:st={DUR - 0.5}:d=0.5,volume=0.22[m];"
        f"[1:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay={d}|{d},apad=whole_dur={DUR}[v];"
        f"[m][v]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-15:TP=-1.5[out]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", cfg["musica"], "-i", cfg["voz_wav"],
                "-filter_complex", filt, "-map", "[out]", "-ar", "44100", "-ac", "2", aud], check=True)

# ---------- Fotogramas -> FFmpeg ----------
MAXRATE = int(min(2400, 4.4e6 * 8 / DUR / 1000 - 150))
enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", aud,
    "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-maxrate", f"{MAXRATE}k", "-bufsize", f"{2 * MAXRATE}k",
    "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
    "-movflags", "+faststart", "-shortest", cfg["salida"]], stdin=subprocess.PIPE)

for i in range(N):
    t = i / FPS
    F = fondo(t)
    # Gancho: visible desde el primer fotograma; vuelve al final (después de irse la cita)
    op_g = max(1 - rampa(t, t_fin_gancho + 0.1, 0.3), rampa(t, T_LOOP + 0.25, LOOP - 0.25))
    for p in gancho_p: p.pintar(F, op_g)
    salida = 1 - rampa(t, T_LOOP, 0.25)
    for p in cita_p:
        base = 0.36 * rampa(t, ini[p.grupo] - 0.12, 0.15)
        luz = rampa(t, p.t_on, 0.12)
        p.pintar(F, max(base, luz) * salida, dy=8 * (1 - rampa(t, ini[p.grupo] - 0.12, 0.3)))
    k = rampa(t, t_autor, 0.4) * salida
    for p in fin_p: p.pintar(F, k, dy=14 * (1 - k))
    enc.stdin.write((np.clip(F, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()
os.remove(aud)
# Red de seguridad: si aun así pasa de 4,7 MB, se recomprime
if os.path.getsize(cfg["salida"]) > 4.7e6:
    tmp = cfg["salida"] + ".tmp.mp4"
    br = int(4.2e6 * 8 / DUR / 1000 - 140)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", cfg["salida"], "-c:v", "libx264", "-preset", "slow",
                    "-b:v", f"{br}k", "-maxrate", f"{br}k", "-bufsize", f"{2 * br}k", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, cfg["salida"])
print(json.dumps({"salida": cfg["salida"], "duracion": DUR, "mb": round(os.path.getsize(cfg["salida"]) / 1e6, 2),
                  "gancho": g_txt}, ensure_ascii=False))
