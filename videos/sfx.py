"""Efectos de sonido del formato quiz, creados con código (sin licencias de terceros, como musica.py).
pop (entra una tarjeta o una chapa), whoosh (transición), campana (revelación), subida (cuenta atrás) y
golpe (comillas que se cierran). Uso: python3 sfx.py <carpeta>"""
import os, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(11)


def env(n, ataque, caida):
    t = np.arange(n) / SR
    return np.minimum(t / max(ataque, 1e-4), 1) * np.exp(-t * caida)


def pop():
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 18) + 380  # tono que cae: «pop» suave
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 30) * 0.7


def whoosh():
    n = int(0.55 * SR)
    ruido = rng.standard_normal(n)
    # filtro paso banda que sube y baja (media móvil de longitud variable ≈ barrido)
    t = np.arange(n) / SR
    forma = np.sin(np.pi * t / t[-1]) ** 2
    suave = np.convolve(ruido, np.ones(24) / 24, mode="same")
    agudo = ruido - suave
    return (suave * (1 - forma) * 0.5 + agudo * forma * 0.35) * forma * 0.8


def campana():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * 880 * k * t) * np.exp(-t * (2.5 + 2 * k)) for k, a in ((1, 1), (2.76, 0.45), (5.4, 0.25), (8.9, 0.12)))
    return s * np.minimum(t / 0.003, 1) * 0.45


def subida():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 300 + 600 * (t / t[-1]) ** 2
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(t / 0.05, 1) * (t / t[-1]) * 0.35


def golpe():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    cuerpo = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-t * 6) + 45) / SR) * env(n, 0.003, 9)
    chasquido = rng.standard_normal(n) * env(n, 0.001, 60) * 0.25
    return (cuerpo + chasquido) * 0.8


def guardar(ruta, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    st = np.stack([x, x], 1)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for nombre, fn in (("pop", pop), ("whoosh", whoosh), ("campana", campana), ("subida", subida), ("golpe", golpe)):
        guardar(os.path.join(out, f"{nombre}.wav"), fn())
    print("efectos en", out)
