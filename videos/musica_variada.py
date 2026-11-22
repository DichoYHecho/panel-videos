"""Música variada para el vídeo largo quiz, creada con código (sin licencias de terceros, como musica.py).
Cada tramo tiene su carácter: intro luminosa, un estilo por nivel (cada vez con más energía) y un final alegre.
Solo numpy y la biblioteca estándar. Uso: python3 musica_variada.py <estilo> <segundos> <salida.wav> [semilla]
Estilos: intro, facil, medio, dificil, experto, final."""
import sys, wave
import numpy as np

SR = 44100


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


# acordes (MIDI), duración de cada acorde (s), paso del arpegio (s), golpe de bombo cada (s, 0 = sin),
# platillo cada (s), timbre del arpegio, volumen del bajo
ESTILOS = {
    "intro":   dict(acordes=[[60, 64, 67, 72], [57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67]], largo=2.0, paso=0.25, bombo=0, plato=0, timbre="campana", bajo=0.6),
    "facil":   dict(acordes=[[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]], largo=2.0, paso=0.3, bombo=1.0, plato=0.5, timbre="punteo", bajo=0.7),
    "medio":   dict(acordes=[[57, 60, 64], [53, 57, 60], [60, 64, 67], [55, 59, 62]], largo=2.0, paso=0.25, bombo=0.5, plato=0.25, timbre="punteo", bajo=0.8),
    "dificil": dict(acordes=[[50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 49, 52]], largo=2.0, paso=0.1875, bombo=0.375, plato=0.1875, timbre="sintetico", bajo=1.0),
    "experto": dict(acordes=[[52, 55, 59], [48, 52, 55], [50, 54, 57], [47, 51, 54]], largo=1.5, paso=0.125, bombo=0.375, plato=0.125, timbre="sintetico", bajo=1.1),
    "final":   dict(acordes=[[53, 57, 60, 65], [55, 59, 62, 67], [52, 55, 59, 64], [57, 60, 64, 69]], largo=2.0, paso=0.25, bombo=1.0, plato=0.5, timbre="campana", bajo=0.7),
}


def nota(f, n, timbre, rng):
    t = np.arange(n) / SR
    if timbre == "campana":
        s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2.2 + k)) for k, a in ((1, 1), (2.01, 0.4), (3.98, 0.15)))
    elif timbre == "sintetico":
        s = (np.sign(np.sin(2 * np.pi * f * t)) * 0.35 + np.sin(2 * np.pi * f * t)) * np.exp(-t * 7)
    else:  # punteo (tipo guitarra/marimba)
        s = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in ((1, 1), (2, 0.3), (3, 0.08))) * np.exp(-t * 5)
    return s * np.minimum(t / 0.004, 1)


def generar(estilo, dur, semilla=1):
    e = ESTILOS[estilo]
    rng = np.random.default_rng(semilla)
    N = int(dur * SR)
    L = np.zeros(N); R = np.zeros(N)
    nac = len(e["acordes"])
    # colchón (pad) suave con los acordes
    for i in range(int(np.ceil(dur / e["largo"]))):
        ac = e["acordes"][i % nac]
        a = int(i * e["largo"] * SR); b = min(int((i + 1) * e["largo"] * SR + 0.3 * SR), N)
        if a >= N: break
        tt = np.arange(b - a) / SR
        env = np.minimum(tt / 0.4, 1) * np.minimum((tt[-1] - tt) / 0.4 + 0.01, 1)
        for m in ac:
            for det, pan in ((-0.08, 0.35), (0.08, 0.65)):
                s = np.sin(2 * np.pi * hz(m + det) * tt) * env * 0.035
                L[a:b] += s * (1 - pan); R[a:b] += s * pan
        # bajo: la tónica una octava abajo, en negras
        for k in range(int(e["largo"] / 0.5)):
            a2 = a + int(k * 0.5 * SR); n2 = min(int(0.45 * SR), N - a2)
            if n2 <= 0: break
            t2 = np.arange(n2) / SR
            s = np.sin(2 * np.pi * hz(ac[0] - 12) * t2) * np.exp(-t2 * 4) * 0.16 * e["bajo"]
            L[a2:a2 + n2] += s; R[a2:a2 + n2] += s
    # arpegio
    for k in range(int(dur / e["paso"])):
        ac = e["acordes"][int(k * e["paso"] / e["largo"]) % nac]
        m = ac[k % len(ac)] + 12 * (1 if (k // len(ac)) % 2 else 0)
        a = int(k * e["paso"] * SR); n = min(int(1.2 * SR), N - a)
        if n <= 0: break
        s = nota(hz(m), n, e["timbre"], rng) * 0.07
        p = 0.3 + 0.4 * ((k % 4) / 3)
        L[a:a + n] += s * (1 - p); R[a:a + n] += s * p
    # percusión suave: bombo (seno que cae) y platillo (ruido corto filtrado)
    if e["bombo"]:
        for k in range(int(dur / e["bombo"])):
            a = int(k * e["bombo"] * SR); n = min(int(0.3 * SR), N - a)
            if n <= 0: break
            t = np.arange(n) / SR
            s = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 25) + 45) / SR) * np.exp(-t * 12) * 0.22
            L[a:a + n] += s; R[a:a + n] += s
    if e["plato"]:
        for k in range(int(dur / e["plato"])):
            a = int((k * e["plato"] + e["plato"] / 2) * SR); n = min(int(0.06 * SR), N - a)
            if n <= 0: break
            ruido = rng.standard_normal(n)
            ruido = ruido - np.convolve(ruido, np.ones(8) / 8, mode="same")  # solo agudos
            s = ruido * np.exp(-np.arange(n) / SR * 60) * 0.03
            L[a:a + n] += s * 0.8; R[a:a + n] += s
    # fundidos para encadenar tramos
    t = np.arange(N) / SR
    fade = np.minimum(np.minimum(t / 0.6, 1), np.minimum((dur - t) / 0.8, 1))
    st = np.stack([L, R], 1) * fade[:, None]
    return st / (np.max(np.abs(st)) + 1e-9) * 0.8


if __name__ == "__main__":
    estilo, dur, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    st = generar(estilo, dur, int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    print("ok", estilo, dur, out)
