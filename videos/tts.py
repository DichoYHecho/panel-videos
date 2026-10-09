"""Voz neutra (Piper, voz es_ES «davefx») frase a frase -> wav + tiempos de cada frase.
No imita a nadie: es una voz de narrador genérica, siempre la misma."""
import json, os, re
import numpy as np, soundfile as sf
from comun import texto_voz

SR = 24000
MODELO = os.environ.get("MODELO_VOZ", os.path.join(os.path.dirname(__file__), "..", "modelos",
                                                    "vits-piper-es_ES-davefx-medium"))
_tts = None


def _motor():
    global _tts
    if _tts is None:
        import sherpa_onnx
        d = MODELO
        cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{d}/es_ES-davefx-medium.onnx",
                tokens=f"{d}/tokens.txt", data_dir=f"{d}/espeak-ng-data", length_scale=1.12),
            num_threads=2))
        _tts = sherpa_onnx.OfflineTts(cfg)
    return _tts


def _recortar(x, thr=0.012):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0: return x
    return x[max(idx[0] - int(0.02 * SR), 0):min(idx[-1] + int(0.06 * SR), len(x))]


def sintetizar(frases, autor, out_wav, out_json):
    """Lee cada frase y al final el nombre del autor. Guarda el audio y los tiempos."""
    tts = _motor()
    partes, tiempos, t = [], [], 0.0
    for f in list(frases) + [autor + "."]:
        a = tts.generate(texto_voz(f), sid=0, speed=1.0)
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
