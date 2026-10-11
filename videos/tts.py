"""Voz neutra (Piper) frase a frase -> wav + tiempos de cada trozo.
Voz «m»: es_ES davefx (masculina). Voz «f»: es_ES sharvard, hablante F (femenina; CC BY 3.0).
Ninguna imita a nadie: son voces de narrador genéricas."""
import json, os, re
import numpy as np, soundfile as sf
from comun import texto_voz

SR = 24000
DIR = os.environ.get("MODELOS_VOZ", os.path.join(os.path.dirname(__file__), "..", "modelos"))
VOCES = {  # carpeta, archivo, hablante, lentitud
    "m": ("vits-piper-es_ES-davefx-medium", "es_ES-davefx-medium.onnx", 0, 1.12),
    "f": ("vits-piper-es_ES-sharvard-medium", "es_ES-sharvard-medium.onnx", 1, 1.08),
}
_motores = {}


def _motor(voz):
    if voz not in _motores:
        import sherpa_onnx
        carpeta, onnx, _, lento = VOCES[voz]
        d = os.path.join(DIR, carpeta)
        cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{d}/{onnx}", tokens=f"{d}/tokens.txt",
                                                        data_dir=f"{d}/espeak-ng-data", length_scale=lento),
            num_threads=2))
        _motores[voz] = sherpa_onnx.OfflineTts(cfg)
    return _motores[voz]


def _recortar(x, thr=0.012):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0: return x
    return x[max(idx[0] - int(0.02 * SR), 0):min(idx[-1] + int(0.06 * SR), len(x))]


def sintetizar(trozos, out_wav, out_json, voz="m", rapido=()):
    """Lee cada trozo (gancho, frases de la cita, autor) y guarda el audio y los tiempos.
    rapido = índices de los trozos que se leen un poco más deprisa (el gancho)."""
    tts = _motor(voz)
    sid = VOCES[voz][2]
    partes, tiempos, t = [], [], 0.0
    for i, f in enumerate(trozos):
        a = tts.generate(texto_voz(f), sid=sid, speed=1.12 if i in rapido else 1.0)
        x = np.array(a.samples, dtype=np.float32)
        if a.sample_rate != SR:
            n = int(len(x) * SR / a.sample_rate)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        x = _recortar(x)
        x = x / (np.max(np.abs(x)) + 1e-6) * 0.9
        d = len(x) / SR
        tiempos.append({"texto": f, "ini": round(t, 3), "fin": round(t + d, 3)})
        pausa = 0.45 if re.search(r"[.;:?!…]$", f.strip()) else 0.22
        partes += [x, np.zeros(int(pausa * SR), np.float32)]
        t += d + pausa
    sf.write(out_wav, np.concatenate(partes), SR)
    json.dump(tiempos, open(out_json, "w"), ensure_ascii=False, indent=1)
    return tiempos
