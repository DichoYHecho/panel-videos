"""Aviso «Síguenos» para los vídeos de Dicho y Hecho (versión 2: flechas que se abren).

Animación:
  1. Aparecen solo las dos flechas «» juntas en el centro, dentro de una cápsula de cristal pequeña.
  2. Cada flecha se va hacia su lado (« a la izquierda, » a la derecha) y la cápsula se ensancha.
  3. En el centro aparecen «Síguenos» y los iconos de YouTube, Instagram y TikTok.
  4. Para salir se hace exactamente lo mismo a la inversa.

Se dibuja con Pillow/numpy/scipy (ya están en el proyecto). Uso en render.py:
    from cta import PieCta
    CTA = PieCta(CX, 300, t0, t1)     # t1 - t0 >= PieCta.DUR_MIN
    ...
    CTA.pintar(F, t)                  # F = fotograma float32 (H, W, 3) en 0..1
"""
import glob, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

AMARILLO = (245, 197, 24)
SS = 4  # supersampling de los iconos

FD = next((d for d in ["/usr/share/fonts/opentype/inter/", os.path.join(os.path.dirname(__file__), "fuentes/")]
           if glob.glob(d + "Inter-Bold.*")), "/usr/share/fonts/opentype/inter/")


def _suave(x):
    x = min(max(float(x), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _rampa(t, a, d):
    return _suave((t - a) / d)


def _pop(x):
    """x en 0..1 -> escala con un pequeño rebote (0 -> ~1.06 -> 1)."""
    x = min(max(float(x), 0.0), 1.0)
    if x <= 0: return 0.0
    return 1 - (1 - x) ** 3 + 0.07 * np.sin(np.pi * x) * (1 - x)


# ---------- Iconos (monocromos, dibujados con código) ----------
def _icono(nombre, px):
    n = px * SS
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    u = n / 100.0
    if nombre == "youtube":
        d.rounded_rectangle([4 * u, 20 * u, 96 * u, 80 * u], radius=18 * u, fill=255)
        d.polygon([(41 * u, 35 * u), (41 * u, 65 * u), (66 * u, 50 * u)], fill=0)
    elif nombre == "instagram":
        w = int(8 * u)
        d.rounded_rectangle([8 * u, 8 * u, 92 * u, 92 * u], radius=26 * u, outline=255, width=w)
        d.ellipse([29 * u, 29 * u, 71 * u, 71 * u], outline=255, width=w)
        d.ellipse([68 * u, 22 * u, 80 * u, 34 * u], fill=255)
    elif nombre == "tiktok":
        w = 13 * u
        d.rectangle([55 * u, 8 * u, 55 * u + w, 62 * u], fill=255)
        cx, cy, r = 42 * u, 68 * u, 20 * u
        d.ellipse([cx - r - w / 2, cy - r - w / 2, cx + r + w / 2, cy + r + w / 2], fill=255)
        d.ellipse([cx - r + w / 2, cy - r + w / 2, cx + r - w / 2, cy + r - w / 2], fill=0)
        for k in range(0, 61):
            a = np.pi / 2 * k / 60
            x, y = 61.5 * u + 25 * u * np.sin(a), 8 * u + 24 * u * (1 - np.cos(a))
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
        d.rectangle([55 * u, 0, 55 * u + w, 8 * u], fill=0)
    return np.asarray(im.resize((px, px), Image.LANCZOS), dtype=np.float32) / 255.0


def _flechas(px):
    """Las dos flechas de la marca, « y », como máscaras alfa recortadas a la misma altura."""
    f = ImageFont.truetype(FD + "Inter-Bold.otf", int(px * 2.0))
    out = []
    for ch in ("\u00ab", "\u00bb"):
        im = Image.new("L", (px * 3, px * 3), 0)
        ImageDraw.Draw(im).text((px // 2, px * 2), ch, font=f, fill=255, anchor="ls")
        out.append(np.asarray(im, dtype=np.float32) / 255.0)
    y0 = min(np.where(a > 0.05)[0].min() for a in out)
    y1 = max(np.where(a > 0.05)[0].max() for a in out)
    res = []
    for a in out:
        xs = np.where(a > 0.05)[1]
        res.append(a[y0:y1 + 1, xs.min():xs.max() + 1])
    return res


class PieCta:
    DUR_MIN = 3.9  # segundos que necesita la animación completa (entrada ~1 s, pausa ~1,9 s, salida ~1 s)

    def __init__(self, cx, cy, t0, t1, ancho=1080, alto=1920):
        self.cx, self.cy, self.t0, self.t1 = cx, cy, t0, t1
        self.W, self.H = ancho, alto
        self.izq, self.der = _flechas(34)
        self.aw = max(self.izq.shape[1], self.der.shape[1])
        self.ah = self.izq.shape[0]
        self.ic, self.gap, self.sep = 44, 22, 26
        self.pad, self.inner = 32, 30
        self.h = 92
        f1 = ImageFont.truetype(FD + "Inter-Bold.otf", 40)
        txt_w = f1.getlength("Síguenos")
        self.cw = int(txt_w + self.sep + 2 + self.sep + 3 * self.ic + 2 * self.gap)
        self.w_full = int(2 * (self.pad + self.aw + self.inner) + self.cw)
        self.w_min = int(2 * self.pad + 2 * self.aw + 8)
        self.Wc = self.w_full + 8
        # contenido fijo (texto y raya) ya dibujado
        est = Image.new("L", (self.Wc, self.h), 0)
        d = ImageDraw.Draw(est)
        x = (self.Wc - self.cw) / 2
        d.text((x, self.h // 2 + 14), "Síguenos", font=f1, fill=255, anchor="ls")
        xs = int(x + txt_w + self.sep)
        d.rectangle([xs, self.h // 2 - 19, xs + 1, self.h // 2 + 19], fill=80)
        self.est = np.asarray(est, dtype=np.float32) / 255.0
        self.x_ico = x + txt_w + self.sep + 2 + self.sep
        self.iconos = [_icono(n, self.ic) for n in ("youtube", "instagram", "tiktok")]
        self.amar = np.array(AMARILLO, np.float32)[None, None, :] / 255.0

    # --- utilidades ---
    @staticmethod
    def _poner(dst, mask, x, y, color, op):
        h, w = mask.shape
        ya, yb = max(y, 0), min(y + h, dst.shape[0])
        xa, xb = max(x, 0), min(x + w, dst.shape[1])
        if ya >= yb or xa >= xb: return
        m = mask[ya - y:yb - y, xa - x:xb - x][..., None] * op
        dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - m) + color * m

    @staticmethod
    def _escalar(mask, s):
        h, w = mask.shape
        nh, nw = max(int(round(h * s)), 2), max(int(round(w * s)), 2)
        im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
        return np.asarray(im.resize((nw, nh), Image.LANCZOS), dtype=np.float32) / 255.0

    def _capsula(self, w, borde=False):
        sx = 2
        im = Image.new("L", (self.Wc * sx, self.h * sx), 0)
        xl = (self.Wc - w) / 2 * sx
        xr = (self.Wc + w) / 2 * sx - 1
        r = self.h * sx
        if borde:
            ImageDraw.Draw(im).rounded_rectangle([xl, 0, xr, self.h * sx - 1], radius=r, outline=255, width=3)
        else:
            ImageDraw.Draw(im).rounded_rectangle([xl, 0, xr, self.h * sx - 1], radius=r, fill=255)
        return np.asarray(im.resize((self.Wc, self.h), Image.LANCZOS), dtype=np.float32)[..., None] / 255.0

    # --- animación ---
    def estado(self, t):
        """(a, p): a = visibilidad de cápsula y flechas; p = apertura (0 = flechas juntas, 1 = abierto)."""
        T, D = t - self.t0, self.t1 - self.t0
        a = _rampa(T, 0.0, 0.30) * (1 - _rampa(T, D - 0.30, 0.30))
        p = _rampa(T, 0.35, 0.65) * (1 - _rampa(T, D - 1.00, 0.65))
        return a, p

    def pintar(self, F, t):
        if t < self.t0 - 0.05 or t > self.t1 + 0.05: return
        a, p = self.estado(t)
        if a <= 0.004: return
        Wc, h = self.Wc, self.h
        X0, Y0 = int(self.cx - Wc / 2), int(self.cy - h / 2)
        if X0 < 0 or X0 + Wc > self.W or Y0 < 0 or Y0 + h > self.H: return
        reg = F[Y0:Y0 + h, X0:X0 + Wc]
        w = self.w_min + (self.w_full - self.w_min) * p
        xl = (Wc - w) / 2
        # cristal
        forma = self._capsula(w)
        borroso = gaussian_filter(reg, sigma=(9, 9, 0)) * 0.55
        base = reg * (1 - forma * a) + borroso * (forma * a)
        bd = self._capsula(w, borde=True) * 0.55 * a
        base = base * (1 - bd) + self.amar * bd
        # flechas: nacen juntas y cada una se va a su lado
        s = 0.75 + 0.25 * a
        li, ri = self._escalar(self.izq, s), self._escalar(self.der, s)
        cy = h // 2
        xi = xl + self.pad + self.aw / 2
        xd = xl + w - self.pad - self.aw / 2
        self._poner(base, li, int(round(xi - li.shape[1] / 2)), cy - li.shape[0] // 2, self.amar, a)
        self._poner(base, ri, int(round(xd - ri.shape[1] / 2)), cy - ri.shape[0] // 2, self.amar, a)
        # contenido del centro (se descubre entre las flechas)
        if p > 0.30:
            A = self.est * _rampa(p, 0.45, 0.35)
            for i, ic in enumerate(self.iconos):
                k = _pop((p - (0.45 + 0.10 * i)) / 0.30)
                if k <= 0.01: continue
                m = self._escalar(ic, k)
                x = int(round(self.x_ico + i * (self.ic + self.gap) + self.ic / 2 - m.shape[1] / 2))
                y = cy - m.shape[0] // 2
                ya, yb = max(y, 0), min(y + m.shape[0], h)
                xa, xb = max(x, 0), min(x + m.shape[1], Wc)
                if ya < yb and xa < xb:
                    sub = m[ya - y:yb - y, xa - x:xb - x] * min(k, 1.0)
                    A[ya:yb, xa:xb] = 1 - (1 - A[ya:yb, xa:xb]) * (1 - sub)
            xx = np.arange(Wc, dtype=np.float32)[None, :]
            ix0, ix1 = xl + self.pad + self.aw + 14, xl + w - self.pad - self.aw - 14
            ventana = np.clip((xx - ix0) / 16, 0, 1) * np.clip((ix1 - xx) / 16, 0, 1)
            A = (A * ventana * a)[..., None]
            base = base * (1 - A) + A  # blanco
        F[Y0:Y0 + h, X0:X0 + Wc] = base
