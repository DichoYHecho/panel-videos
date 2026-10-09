"""Funciones compartidas: frases de la cita, texto para la voz y gancho inicial.
El gancho sale SOLO de los datos del banco (Autor y Fuente); nunca se inventa nada."""
import re
from datetime import date

ELIPSIS = "⁣"  # marca temporal para que «[…]» no corte la frase


def frases(cita):
    """Divide la cita por signos de puntuación (cada trozo aparece y se lee por separado)."""
    t = cita.replace("[…]", ELIPSIS).replace("[...]", ELIPSIS)
    trozos = re.findall(r"[^,;:.?!…]+[,;:.?!…]*", t)
    out = [x.strip().replace(ELIPSIS, "[…]") for x in trozos]
    return [x for x in out if re.search(r"\w", x)]


def texto_voz(frase):
    """Lo que lee la voz: sin «[…]» ni corchetes ni comillas."""
    t = frase.replace("[…]", " ").replace("[...]", " ")
    t = re.sub(r"[\[\]«»“”\"]", "", t)
    return re.sub(r"\s+", " ", t).strip()


TIPOS = {"discurso": "en un discurso", "mensaje": "en un mensaje",
         "conferencia": "en una conferencia", "entrevista": "en una entrevista"}


def gancho(autor, fuente, hoy=None):
    """Devuelve (frase del gancho, línea pequeña o None).
    - «Carta a su…/Carta a Nombre…» → «Hace N años, X le escribió esto a …:»
    - «Discurso/Mensaje/Conferencia/Entrevista…» → «Hace N años, X lo dijo en un discurso:»
    - En los demás casos no se supone nada: «Una frase de X» y debajo la Fuente tal cual."""
    hoy = hoy or date.today().year
    fuente = (fuente or "").strip()
    m = re.search(r"\b(1\d{3}|20\d{2})\b", fuente)
    años = hoy - int(m.group(1)) if m else 0
    hace = f"Hace {años} años, " if años >= 2 else ""
    mc = re.match(r"Carta a (su [^,(;]+|[A-ZÁÉÍÓÚÑ][^,(;]*)", fuente)
    if mc:
        return f"{hace}{autor} le escribió esto a {mc.group(1).strip()}:", None
    md = re.match(r"(discurso|mensaje|conferencia|entrevista)\b", fuente, re.I)
    if md:
        return f"{hace}{autor} lo dijo {TIPOS[md.group(1).lower()]}:", None
    sub = fuente
    if len(sub) > 95:
        sub = sub[:95].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return f"Una frase de {autor}", (sub or None)
