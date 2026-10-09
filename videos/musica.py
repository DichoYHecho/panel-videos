"""Música ambiental generada con código (sin licencias de terceros).
Pad suave + notas tipo piano + reverb. Uso: python3 musica.py salida.wav segundos [semilla]"""
import sys
import numpy as np, soundfile as sf

SR = 44100
out, dur = sys.argv[1], float(sys.argv[2])
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
N = int(dur * SR)
t = np.arange(N) / SR

def hz(m): return 440 * 2 ** ((m - 69) / 12)

# Progresión tranquila: Cmaj7 - Am7 - Fmaj7 - G6 (en MIDI)
acordes = [[48, 55, 64, 71], [45, 52, 60, 67], [41, 48, 57, 64], [43, 50, 59, 64]]
largo = dur / 4
L = np.zeros(N); R = np.zeros(N)
for i, ac in enumerate(acordes):
    a, b = int(i * largo * SR), int(min((i + 1) * largo + 1.5, dur) * SR)
    tt = t[a:b] - t[a]
    env = np.minimum(tt / 1.2, 1) * np.minimum((t[b - 1] - t[a] - tt) / 1.5, 1)
    env = np.clip(env, 0, 1) ** 1.5
    for m in ac:
        for det, pan in ((-0.12, 0.3), (0.12, 0.7)):
            f = hz(m + det / 1)
            s = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)
            L[a:b] += s * env * (1 - pan) * 0.05
            R[a:b] += s * env * pan * 0.05

# Notas sueltas tipo piano (arpegio lento)
paso = 0.8
for k in range(int(dur / paso)):
    if rng.random() < 0.35: continue
    ac = acordes[min(int(k * paso / largo), 3)]
    m = rng.choice(ac) + 12 * rng.choice([1, 2], p=[0.6, 0.4])
    a = int(k * paso * SR); n = min(int(3.5 * SR), N - a)
    tt = np.arange(n) / SR
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * h * tt) * w for h, w in ((1, 1), (2, 0.35), (3, 0.12)))
    s *= np.exp(-tt * 1.6) * np.minimum(tt / 0.006, 1) * 0.11
    p = rng.uniform(0.3, 0.7)
    L[a:a + n] += s * (1 - p); R[a:a + n] += s * p

# Reverb sencilla (ruido con caída exponencial)
ir_t = np.arange(int(2.2 * SR)) / SR
def rev(x, seed):
    ir = np.random.default_rng(seed).standard_normal(len(ir_t)) * np.exp(-ir_t * 2.8)
    y = np.fft.irfft(np.fft.rfft(x, N + len(ir)) * np.fft.rfft(ir, N + len(ir)))[:N]
    return x * 0.6 + y / np.max(np.abs(y)) * np.max(np.abs(x)) * 0.5
L, R = rev(L, 1), rev(R, 2)

# Suavizar agudos (paso bajo de un polo) y fundidos
def lp(x, fc=3500):
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); acc = 0.0
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x)
L, R = lp(L), lp(R)
fade = np.minimum(np.minimum(t / 1.0, 1), np.minimum((dur - t) / 2.0, 1))
st = np.stack([L, R], 1) * fade[:, None]
st = st / np.max(np.abs(st)) * 0.8
sf.write(out, st.astype(np.float32), SR)
print("ok", out, dur)
