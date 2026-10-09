"""Vídeo vertical 1080x1920 (formato B): foto con zoom lento, gancho, voz y subtítulos palabra a palabra.
Python dibuja los fotogramas y FFmpeg codifica y mezcla el audio.
Uso: python3 render.py config.json"""
import glob, json, os, re, subprocess, sys
from comun import frases, gancho
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

W, H, FPS = 1080, 1920, 30
AMARILLO = (245, 197, 24)
BLANCO = (255, 255, 255)
FD = next((d for d in ["/usr/share/fonts/opentype/inter/", os.path.join(os.path.dirname(__file__), "fuentes/")]
           if glob.glob(d + "Inter-Bold.*")), "/usr/share/fonts/opentype/inter/")
F_BOLD, F_SEMI, F_MED = FD + "Inter-Bold.otf", FD + "Inter-SemiBold.otf", FD + "Inter-Medium.otf"
TEXT_W, CX = 860, 530  # ancho útil y centro (algo a la izquierda por los botones de TikTok)

cfg = json.load(open(sys.argv[1]))
modo = "B"

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
    """tokens = [(texto, color, grupo)]; líneas equilibradas, centradas en CX."""
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

# ---------- Tiempos ----------
cita = cfg["cita"]; autor = cfg["autor"]
fr = frases(cita)
g_txt, g_sub = gancho(autor, cfg.get("fuente", ""))
T0 = 2.4 if g_sub else 2.1  # empieza la cita (antes, el gancho)
if True:
    tv = json.load(open(cfg["voz_json"]))
    assert len(tv) == len(fr) + 1, "la voz no tiene las mismas frases que la cita"
    ini = [T0 + v["ini"] for v in tv[:-1]]
    t_autor = T0 + tv[-1]["ini"]
    t_cierre = max(T0 + tv[-1]["fin"] + 1.8, 12.0 - 2.4)
DUR = round(t_cierre + 2.4, 2)

# ---------- Capas de texto ----------
CY = 880
# Cita con comillas, una palabra por token, agrupada por frase
toks = []
for g, f in enumerate(fr):
    ws = f.split()
    for k, w in enumerate(ws):
        if g == 0 and k == 0: w = "“" + w
        if g == len(fr) - 1 and k == len(ws) - 1: w = w + "”"
        toks.append((w, BLANCO, g))
cita_p, alto_c, f_cita = ajustar(toks, F_BOLD, 80, 52, 720, CY)
f_aut = ImageFont.truetype(F_SEMI, 50)
autor_p, _ = maquetar([("— " + autor, AMARILLO, 0)], f_aut, TEXT_W, CY + alto_c / 2 + 70)

# Tiempos por palabra (B: reparto proporcional dentro de cada frase según su duración de voz)
if modo == "B":
    for g, v in enumerate(tv[:-1]):
        ps = [p for p in cita_p if p.grupo == g]
        pesos = np.array([len(re.sub(r"\W", "", p.txt)) + 2 for p in ps], float)
        acum = np.concatenate([[0], np.cumsum(pesos)[:-1]]) / pesos.sum()
        for p, a in zip(ps, acum):
            p.t_on = T0 + v["ini"] + a * (v["fin"] - v["ini"]) - 0.05

# El nombre del autor va en amarillo (y en una sola línea si es corto)
i_a = g_txt.find(autor)
if i_a >= 0:
    antes, despues = g_txt[:i_a].split(), g_txt[i_a + len(autor):]
    nombre = [autor.replace(" ", "\u00a0")] if len(autor) <= 18 else autor.split()
    if despues and not despues.startswith(" "):  # signo pegado al nombre («Séneca:»)
        pegado, _, despues = despues.partition(" ")
        nombre[-1] += pegado
    g_toks = ([(w, BLANCO, 0) for w in antes] + [(w, AMARILLO, 0) for w in nombre]
              + [(w, BLANCO, 0) for w in despues.split()])
else:
    g_toks = [(w, BLANCO, 0) for w in g_txt.split()]
gancho_p, alto_g, _ = ajustar(g_toks, F_BOLD, 76, 52, 440, CY - 60)
if g_sub:
    sub_p, _ = maquetar([(w, (215, 215, 215), 0) for w in g_sub.split()],
                        ImageFont.truetype(F_MED, 36), TEXT_W, CY - 60 + alto_g / 2 + 60)
    gancho_p += sub_p

cierre1 = "Una frase cada día · @dichoyhechoo_"
c_toks = [(w, AMARILLO if w.startswith("@") else BLANCO, 0) for w in cierre1.split()]
TEXT_W = 940
cierre_p, _, _ = ajustar(c_toks, F_SEMI, 52, 34, 80, CY - 20)
TEXT_W = 860
cred_p = []
if cfg.get("credito"):
    cred_p, _ = maquetar([(w, (225, 225, 225), 0) for w in cfg["credito"].split()],
                         ImageFont.truetype(F_MED, 32), TEXT_W, CY + 95)

# ---------- Fondo: foto con zoom lento ----------
if cfg.get("foto"):
    foto = Image.open(cfg["foto"]).convert("RGB")
else:  # sin foto libre: fondo gris oscuro neutro
    g = np.linspace(70, 25, H, dtype=np.float32)[:, None, None] * np.ones((1, W, 3), np.float32)
    foto = Image.fromarray(g.astype(np.uint8))
ZMAX = 1.12
s0 = max(W / foto.width, H / foto.height) * ZMAX
S = foto.resize((round(foto.width * s0), round(foto.height * s0)), Image.LANCZOS)
fx, fy = cfg.get("foco", [0.5, 0.38])

yy = np.arange(H, dtype=np.float32)[:, None]
xx = np.arange(W, dtype=np.float32)[None, :]
grad = np.clip(0.5 + yy / 700, 0, 1) * np.clip(0.42 + (H - yy) / 820, 0, 1)
vig = 1 - 0.35 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.8)) ** 2)
MASK = (grad * vig)[..., None].astype(np.float32)

def suave(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def rampa(t, a, d): return suave((t - a) / d)

def fondo(t):
    z = 1.0 + (ZMAX - 1.0) * (t / DUR)
    r = z / ZMAX
    hw, hh = W / 2 / r, H / 2 / r
    cx = min(max(fx * S.width, hw), S.width - hw)
    cy = min(max(fy * S.height, hh), S.height - hh)
    im = S.transform((W, H), Image.AFFINE, (1 / r, 0, cx - hw, 0, 1 / r, cy - hh), Image.BILINEAR)
    dim = 0.58 - 0.16 * rampa(t, T0 - 0.3, 0.8) - 0.10 * rampa(t, t_cierre, 0.6)
    return np.asarray(im, dtype=np.float32) / 255.0 * (MASK * dim)

# ---------- Audio (FFmpeg) ----------
aud = cfg["salida"].replace(".mp4", "_audio.wav")
mus = f"[0:a]atrim=0:{DUR},afade=t=in:d=0.8,afade=t=out:st={DUR - 2.0}:d=2.0"
if True:
    d = int(T0 * 1000)
    filt = (f"{mus},volume=0.22[m];[1:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay={d}|{d},"
            f"apad=whole_dur={DUR}[v];[m][v]amix=inputs=2:normalize=0:duration=first,"
            f"loudnorm=I=-15:TP=-1.5[out]")
    ins = ["-i", cfg["musica"], "-i", cfg["voz_wav"]]
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", filt,
                "-map", "[out]", "-ar", "44100", "-ac", "2", aud], check=True)

# ---------- Fotogramas -> FFmpeg ----------
MAXRATE = int(min(2400, 4.4e6 * 8 / DUR / 1000 - 150))
enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", aud,
    "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-maxrate", f"{MAXRATE}k", "-bufsize", f"{2 * MAXRATE}k",
    "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
    "-movflags", "+faststart", "-shortest", cfg["salida"]], stdin=subprocess.PIPE)

N = int(DUR * FPS)
for i in range(N):
    t = i / FPS
    F = fondo(t)
    op_g = 1 - rampa(t, T0 - 0.35, 0.3)
    for p in gancho_p: p.pintar(F, op_g)
    salida = 1 - rampa(t, t_cierre, 0.35)
    for p in cita_p:
        if True:
            base = 0.36 * rampa(t, ini[p.grupo] - 0.12, 0.15)
            luz = rampa(t, p.t_on, 0.12)
            p.pintar(F, max(base, luz) * salida, dy=8 * (1 - rampa(t, ini[p.grupo] - 0.12, 0.3)))
    k = rampa(t, t_autor, 0.4)
    for p in autor_p: p.pintar(F, k * salida, dy=14 * (1 - k))
    kc = rampa(t, t_cierre + 0.2, 0.45)
    for p in cierre_p + cred_p: p.pintar(F, kc, dy=16 * (1 - kc))
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
