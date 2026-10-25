"""Tarea 6.16 (25 oct 2026): el comentario propio de cada publicación, para publicarlo en YouTube.

- Busca en Publicaciones las que no están «Publicado» y tienen vacío el campo «Comentario».
- Para cada una saca de la tabla Citas la Fuente y el título de Wikipedia, y de Wikipedia el resumen
  del artículo del autor (en español si existe; si no, en inglés).
- Gemini (texto, nivel gratuito) escribe UN comentario que aporte algo sobre ESA cita: un dato de
  contexto sacado solo de la Fuente o del resumen y una pregunta, o una pregunta concreta para debatir
  la idea. Nunca genérico ni aleatorio, sin hashtags, sin enlaces y sin pedir likes.
- Control contra datos inventados: si el comentario lleva un número (un año, una cifra) que no está en
  los datos que se le dan a Gemini, se descarta y se pide otro.
- Se guarda en «Comentario» (lo reviso yo en la ficha de «Revisión», como el caption). Si lo borro,
  se vuelve a escribir en la siguiente ejecución. Si lo corrijo, se respeta mi texto.

Variables: AIRTABLE_TOKEN y GEMINI_API_KEY (secrets de GitHub), LIMITE_COMENTARIOS (máximo por
ejecución, 20 por defecto; 0 = ninguno) y SOLO_MIRAR=1 (los escribe en el resumen sin tocar Airtable).
Solo usa la biblioteca estándar de Python: no hace falta instalar nada.
"""
import difflib, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request, zlib

BASE = "appeuC0uIAlqqp1h9"
T_PUB = "tbl7ynqI9bJrWtR0m"      # Publicaciones
T_CITAS = "tbluECdgOggDiZIFJ"    # Citas
CAMPO = "Comentario"
UA = "DichoYHechoBot/1.1 (https://www.instagram.com/dichoyhechoo_/; dichoyhecho66@gmail.com) GitHubActions"
API = "https://generativelanguage.googleapis.com/v1beta"
MODELOS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]   # los mismos del escenario 1 (texto)
LIMITE = int(os.environ.get("LIMITE_COMENTARIOS") or 20)
SOLO_MIRAR = os.environ.get("SOLO_MIRAR") == "1"
ESPERA = 5          # segundos entre peticiones a Gemini (muy por debajo del límite gratuito)
MAX, MIN = 400, 80  # longitud del comentario (caracteres)

TIPOS = {
    "contexto": "Empieza con UN dato de contexto concreto sacado de la fuente o del resumen (de dónde "
                "sale la frase, en qué momento de su vida la dijo o escribió el autor, a qué se dedicaba) "
                "y termina con una pregunta que conecte ese dato con la idea de la cita.",
    "debate": "Plantea la idea de la cita como un pequeño debate: señala un matiz o una objeción "
              "razonable a lo que dice y termina preguntando de qué lado está quien lo lee.",
    "experiencia": "Relaciona la idea de la cita con una situación cotidiana de hoy (trabajo, estudios, "
                   "amistad, familia…) y termina con una pregunta sobre la experiencia de quien lo lee.",
}


# ---------- Airtable ----------
def airtable(metodo, ruta, datos=None):
    for _ in range(4):
        req = urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{ruta}", method=metodo,
                                     data=json.dumps(datos).encode() if datos is not None else None,
                                     headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}",
                                              "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429:            # demasiadas peticiones: Airtable pide esperar 30 s
                time.sleep(31)
                continue
            raise RuntimeError(f"Airtable {e.code}: {e.read()[:300]!r}")
    raise RuntimeError("Airtable sigue contestando 429")


def listar(tabla, campos, formula=None, orden=None):
    params = [("pageSize", "100")] + [("fields[]", c) for c in campos]
    if formula:
        params.append(("filterByFormula", formula))
    if orden:
        params += [("sort[0][field]", orden), ("sort[0][direction]", "asc")]
    out, offset = [], None
    while True:
        q = urllib.parse.urlencode(params + ([("offset", offset)] if offset else []))
        d = airtable("GET", f"{tabla}?{q}")
        out += d["records"]
        offset = d.get("offset")
        if not offset:
            return out


def guardar(cambios):
    """cambios = [(rec_id, texto)]; de 10 en 10 (máximo de Airtable por petición)."""
    for i in range(0, len(cambios), 10):
        airtable("PATCH", T_PUB, {"records": [{"id": r, "fields": {CAMPO: t}} for r, t in cambios[i:i + 10]]})


# ---------- La cita y Wikipedia ----------
def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[\W_]+", "", s)


def buscar_cita(pub, citas):
    f = norm(pub.get("Frase"))
    for c in citas:
        if norm(c["fields"].get("Cita")) == f:
            return c["fields"]
    mismos = [c["fields"] for c in citas if norm(c["fields"].get("Autor")) == norm(pub.get("Autor"))]
    mejor = max(mismos, key=lambda c: difflib.SequenceMatcher(None, norm(c.get("Cita")), f).ratio(), default=None)
    if mejor and difflib.SequenceMatcher(None, norm(mejor.get("Cita")), f).ratio() >= 0.85:
        return mejor
    return None


def wiki(dominio, params):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2", "redirects": "1", **params})
    req = urllib.request.Request(f"https://{dominio}/w/api.php?{q}", headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=30))


def resumen_wikipedia(titulo):
    """Introducción del artículo del autor: en español si existe; si no, la inglesa. Como mucho 2.500 caracteres."""
    if not titulo:
        return ""
    d = wiki("en.wikipedia.org", {"prop": "extracts|langlinks", "exintro": "1", "explaintext": "1",
                                  "lllang": "es", "titles": titulo})
    pag = (d.get("query", {}).get("pages") or [{}])[0]
    texto = pag.get("extract") or ""
    es = [l.get("title") for l in pag.get("langlinks") or [] if l.get("lang") == "es"]
    if es:
        d = wiki("es.wikipedia.org", {"prop": "extracts", "exintro": "1", "explaintext": "1", "titles": es[0]})
        texto = ((d.get("query", {}).get("pages") or [{}])[0].get("extract") or "") or texto
    return re.sub(r"\s+", " ", texto).strip()[:2500]


# ---------- Gemini ----------
def gemini(modelo, prompt):
    cuerpo = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json",
                                   "responseSchema": {"type": "OBJECT", "required": ["comentario"],
                                                      "properties": {"comentario": {"type": "STRING"}}}}}
    req = urllib.request.Request(f"{API}/models/{modelo}:generateContent", data=json.dumps(cuerpo).encode(),
                                 method="POST", headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
                                                         "Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{modelo} {e.code}: {e.read()[:200]!r}")
    texto = d["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(texto)["comentario"].strip()


def instrucciones(pub, cita, quien, wikitexto, tipo):
    return f"""Eres quien lleva «Dicho y Hecho», un canal que publica cada día una cita célebre verificada.
Escribe UN comentario que publicaremos nosotros mismos debajo del Short de YouTube de esta cita, para
abrir conversación. Tiene que aportar algo sobre ESTA cita en concreto.

DATOS (son los únicos hechos que puedes usar):
- Cita: «{pub['Frase'].strip()}»
- Autor: {pub['Autor'].strip()}
- Quién era: {quien or '(sin datos)'}
- Fuente de la cita: {cita.get('Fuente') or '(sin datos)'}
- Resumen de Wikipedia sobre el autor: {wikitexto or '(sin datos)'}

ENFOQUE: {TIPOS[tipo]}

REGLAS:
1. Español de España, tuteando, tono cercano y culto. Sin emojis.
2. Entre 120 y 350 caracteres. Una o dos frases y la pregunta final.
3. No inventes NADA: ni fechas, ni cifras, ni anécdotas, ni otras citas, ni datos del autor que no
   estén en los DATOS. Si un dato no está ahí, no lo uses. No digas que el autor «escribió» la frase
   si la fuente no lo deja claro (puede que la dijera).
4. No copies la cita entera, no empieces con «Esta frase» ni con «Qué gran frase», y no resumas el caption.
5. Termina con UNA pregunta abierta y concreta sobre la idea de la cita. Prohibido lo genérico:
   «¿Qué opináis?», «¿Estás de acuerdo?» a secas, «¡Comenta!», «Déjanos tu opinión».
6. Sin hashtags, sin enlaces, sin mencionar likes, suscripciones ni el canal.

Responde solo con JSON: {{"comentario": "..."}}"""


def numeros(s):
    return set(re.findall(r"\d{2,}", (s or "").replace(".", "")))


def problema(texto, datos):
    """Motivo para descartar el comentario, o None si vale."""
    if not MIN <= len(texto) <= MAX:
        return f"longitud {len(texto)}"
    if "#" in texto or "http" in texto.lower() or "www." in texto.lower():
        return "lleva hashtags o enlaces"
    if not texto.rstrip().endswith("?"):
        return "no termina en pregunta"
    if re.search(r"¿\s*(qu[eé] opin[aá]is|qu[eé] opinas|est[aá]s de acuerdo)\s*\?", texto, re.I):
        return "pregunta genérica"
    inventados = numeros(texto) - numeros(datos)
    if inventados:
        return f"números que no están en los datos: {', '.join(sorted(inventados))}"
    return None


def escribir(pub, cita, quien, wikitexto, tipo):
    datos = " ".join([pub.get("Frase", ""), pub.get("Autor", ""), quien or "", cita.get("Fuente") or "", wikitexto])
    motivos = []
    for intento in range(3):
        modelo = MODELOS[intento % len(MODELOS)]
        try:
            texto = re.sub(r"\s+", " ", gemini(modelo, instrucciones(pub, cita, quien, wikitexto, tipo))).strip()
        except Exception as e:
            motivos.append(str(e)[:160])
            time.sleep(ESPERA)
            continue
        time.sleep(ESPERA)
        p = problema(texto, datos)
        if p is None:
            return texto, None
        motivos.append(f"{p}: «{texto[:80]}…»")
    return None, " | ".join(motivos)


def main():
    if LIMITE <= 0:
        print("LIMITE_COMENTARIOS = 0: no se escribe ningún comentario.")
        return
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Falta el secret GEMINI_API_KEY")
    regs = listar(T_PUB, ["Frase", "Autor", "Quién era", CAMPO],
                  formula=f"AND({{Estado}}!='Publicado', {{{CAMPO}}}='', {{Frase}}!='')", orden="Fecha de Creación")
    print(f"Publicaciones sin comentario: {len(regs)}. Se escribirán como mucho {LIMITE}.")
    if not regs:
        return
    citas = listar(T_CITAS, ["Cita", "Autor", "Wikipedia", "Fuente"])
    cambios, filas = [], []
    for r in regs[:LIMITE]:
        pub, autor = r["fields"], r["fields"].get("Autor", "?")
        tipo = list(TIPOS)[zlib.crc32(r["id"].encode()) % len(TIPOS)]
        try:
            cita = buscar_cita(pub, citas)
            if cita is None:
                raise RuntimeError("no encuentro su cita en la tabla Citas")
            try:
                wikitexto = resumen_wikipedia(cita.get("Wikipedia"))
            except Exception as e:
                print(f"  (Wikipedia no contesta para {autor}: {str(e)[:100]}; se usa solo la fuente)")
                wikitexto = ""
            texto, motivo = escribir(pub, cita, pub.get("Quién era"), wikitexto, tipo)
            if texto:
                cambios.append((r["id"], texto))
                estado, detalle = "ok", texto
            else:
                estado, detalle = "saltada", f"se reintenta en la siguiente ejecución · {motivo}"
        except Exception as e:
            estado, detalle = "error", str(e)[:300]
        print(f"[{estado}] {autor} ({tipo}): {detalle}", flush=True)
        filas.append(f"| {autor} | {tipo} | {estado} | {detalle.replace('|', '/')} |")
    if cambios and not SOLO_MIRAR:
        guardar(cambios)
    print(f"Comentarios {'propuestos (sin guardar)' if SOLO_MIRAR else 'guardados en Airtable'}: {len(cambios)}")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as f:
            f.write(f"### Comentarios para YouTube: {len(cambios)}{' (solo mirar, sin guardar)' if SOLO_MIRAR else ''}\n\n"
                    "| Autor | Enfoque | Estado | Comentario |\n|---|---|---|---|\n" + "\n".join(filas) + "\n\n")


if __name__ == "__main__":
    main()
