"""Formato quiz «¿Quién escribió esto?» (21 nov 2026). Prepara los datos de un Short y lo renderiza con Remotion.

- Opciones falsas: dos autores REALES del banco de citas (tabla Citas), de época y país parecidos al autor de la
  frase y con foto libre en Wikipedia. Nada inventado.
- País, ciudad, años de vida y firma: de Wikidata (P19 → P625/P17 → P299; P569; P570; P109).
- Tema (color del vídeo): lo clasifica Gemini texto (nivel gratuito); si falla, por palabras clave.
- Dónde lo dijo (chapa): de la Fuente. Las fuentes y los créditos de las fotos NO salen en el vídeo: se
  devuelven para la descripción.
- Voz: Gemini Enceladus/Achernar en español neutro (tts.sintetizar_quiz), con el tiempo de cada palabra.
Coste: 0 € (Wikidata, Wikipedia y Commons son públicos; Gemini en el nivel gratuito)."""
import json, os, random, re, shutil, subprocess, sys, time, unicodedata, urllib.parse
import requests

from comun import frases, texto_voz
import tts

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
REMOTION = os.path.join(RAIZ, "remotion")
UA = "DichoYHechoBot/1.1 (https://www.instagram.com/dichoyhechoo_/) GitHubActions"
WD = "https://www.wikidata.org/w/api.php"
PREGUNTA = "¿Quién escribió esto?"
TEMAS = ("fe", "vida", "amor", "ciencia", "coraje", "sociedad")
CLAVES_TEMA = {  # plan B si Gemini no contesta
    "fe": r"\bdios|alma|fe\b|oraci|cielo|esperanz|señor|santo",
    "amor": r"\bam(or|ar|o)\b|querer|coraz[oó]n|bes|amig",
    "ciencia": r"cienci|raz[oó]n|verdad|saber|conocim|investig|natural",
    "coraje": r"libertad|libre|valor|miedo|luch|coraje|derecho|justici",
    "sociedad": r"dinero|poder|pueblo|gobiern|pol[ií]tic|patria|sociedad|riqueza",
}


def _get(params):
    for intento in range(3):
        try:
            r = requests.get(WD, params={**params, "format": "json"}, headers={"User-Agent": UA}, timeout=40)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if intento == 2:
                raise
            time.sleep(3)


def _anio(snak):
    """(año, precisión) de un valor de fecha de Wikidata; año negativo = a. C."""
    v = snak.get("datavalue", {}).get("value", {})
    t = v.get("time")
    if not t:
        return None
    y = int(t[1:].split("-")[0]) * (-1 if t.startswith("-") else 1)
    return y, v.get("precision", 0)


def entidades(titulos):
    """{título enwiki: datos} con qid, años de nacimiento y muerte, lugar de nacimiento y firma."""
    res = {}
    titulos = [t for t in dict.fromkeys(titulos) if t]
    for i in range(0, len(titulos), 50):
        d = _get({"action": "wbgetentities", "sites": "enwiki", "titles": "|".join(titulos[i:i + 50]),
                  "props": "claims|sitelinks", "sitefilter": "enwiki", "redirects": "yes"})
        for e in d.get("entities", {}).values():
            if "missing" in e:
                continue
            c = e.get("claims", {})
            tit = e.get("sitelinks", {}).get("enwiki", {}).get("title")

            def primero(p):
                for x in c.get(p, []):
                    if x.get("mainsnak", {}).get("datavalue"):
                        return x["mainsnak"]
                return None

            nace, muere = primero("P569"), primero("P570")
            lugar = primero("P19")
            firma = primero("P109")
            ciud = [x["mainsnak"]["datavalue"]["value"]["id"] for x in c.get("P27", []) if x.get("mainsnak", {}).get("datavalue")]
            res[tit] = {
                "qid": e["id"],
                "nace": _anio(nace) if nace else None,
                "muere": _anio(muere) if muere else None,
                "lugar": lugar["datavalue"]["value"]["id"] if lugar else None,
                "firma": firma["datavalue"]["value"] if firma else None,
                "ciudadania": ciud,
            }
    return res


def lugares(qids):
    """{qid lugar: (nombre es, lon, lat, qid país)} y {qid país: (nombre es, ISO numérico)}."""
    out, paises = {}, {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        d = _get({"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]), "props": "claims|labels", "languages": "es|en"})
        for q, e in d.get("entities", {}).items():
            c = e.get("claims", {})
            coord = next((x["mainsnak"]["datavalue"]["value"] for x in c.get("P625", []) if x.get("mainsnak", {}).get("datavalue")), None)
            pais = next((x["mainsnak"]["datavalue"]["value"]["id"] for x in c.get("P17", []) if x.get("mainsnak", {}).get("datavalue")), None)
            nombre = e.get("labels", {}).get("es", e.get("labels", {}).get("en", {})).get("value", "")
            out[q] = (nombre, coord["longitude"] if coord else None, coord["latitude"] if coord else None, pais)
            if pais:
                paises[pais] = None
    ps = [p for p in paises]
    for i in range(0, len(ps), 50):
        d = _get({"action": "wbgetentities", "ids": "|".join(ps[i:i + 50]), "props": "claims|labels", "languages": "es|en"})
        for q, e in d.get("entities", {}).items():
            iso = next((x["mainsnak"]["datavalue"]["value"] for x in e.get("claims", {}).get("P299", []) if x.get("mainsnak", {}).get("datavalue")), None)
            paises[q] = (e.get("labels", {}).get("es", e.get("labels", {}).get("en", {})).get("value", ""), iso)
    return out, paises


def foto_libre(titulo):
    """(url de la miniatura, archivo de Commons) de la foto principal de Wikipedia, solo si es libre y no es .svg."""
    r = requests.get("https://en.wikipedia.org/w/api.php", headers={"User-Agent": UA}, timeout=30, params={
        "action": "query", "format": "json", "formatversion": "2", "prop": "pageimages", "piprop": "thumbnail|name",
        "pithumbsize": "900", "pilicense": "free", "redirects": "1", "titles": titulo})
    r.raise_for_status()
    p = (r.json().get("query", {}).get("pages") or [{}])[0]
    nombre = p.get("pageimage", "")
    if not nombre or nombre.lower().endswith(".svg") or not p.get("thumbnail"):
        return None, None
    return p["thumbnail"]["source"], nombre


def credito_commons(archivo):
    """«Autor (licencia)» de un archivo de Commons, para la descripción."""
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers={"User-Agent": UA}, timeout=30, params={
        "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata", "titles": "File:" + archivo})
    r.raise_for_status()
    info = next(iter(r.json()["query"]["pages"].values())).get("imageinfo", [{}])[0].get("extmetadata", {})
    autor = re.sub(r"<[^>]+>", "", info.get("Artist", {}).get("value", "")).strip() or "Autor desconocido"
    autor = re.sub(r"\s+", " ", autor)[:90]
    lic = info.get("LicenseShortName", {}).get("value", "")
    return f"{autor} ({lic})" if lic else autor


def descargar(url, ruta):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    open(ruta, "wb").write(r.content)
    return ruta


def elegir_opciones(autor_tit, datos, banco, semilla):
    """Dos autores del banco parecidos (época y país) con foto libre. banco = [(Autor, título Wikipedia)]."""
    yo = datos.get(autor_tit) or {}
    y0 = (yo.get("nace") or (None,))[0]
    mios = set(yo.get("ciudadania") or [])
    cand = []
    for nombre, tit in banco:
        if not tit or tit == autor_tit or tit not in datos:
            continue
        o = datos[tit]
        y = (o.get("nace") or (None,))[0]
        dist = abs(y - y0) / 40 if (y is not None and y0 is not None) else 6
        if mios & set(o.get("ciudadania") or []):
            dist -= 1.5
        cand.append((dist + random.Random(f"{semilla}{tit}").random() * 0.8, nombre, tit))
    cand.sort()
    elegidas = []
    for _, nombre, tit in cand:
        url, archivo = foto_libre(tit)
        if url:
            elegidas.append((nombre, tit, url, archivo))
        if len(elegidas) == 2:
            break
    if len(elegidas) < 2:
        raise RuntimeError("no hay dos autores parecidos con foto libre en el banco")
    return elegidas


def clasificar_tema(cita, autor):
    clave = os.environ.get("GEMINI_API_KEY", "")
    if clave:
        prompt = (f"Clasifica esta cita en UNO de estos temas y responde solo con la palabra: {', '.join(TEMAS)}.\n"
                  "fe = fe, espiritualidad, esperanza; vida = la vida, el tiempo, la vejez, la muerte, la felicidad; "
                  "amor = amor y amistad; ciencia = ciencia, razón, conocimiento, educación; coraje = valor, libertad, "
                  "justicia, superación; sociedad = dinero, poder, política, crítica social, ironía.\n"
                  f"Cita: «{cita}» ({autor})")
        for modelo in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
            try:
                r = requests.post(f"{tts.API}/models/{modelo}:generateContent", timeout=60,
                                  headers={"x-goog-api-key": clave, "Content-Type": "application/json"},
                                  json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}})
                if r.status_code < 400:
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
                    m = re.search("|".join(TEMAS), txt)
                    if m:
                        return m.group(0)
            except Exception:
                pass
    low = cita.lower()
    for tema, patron in CLAVES_TEMA.items():
        if re.search(patron, low):
            return tema
    return "vida"


def etiqueta_fuente(fuente):
    """Chapa corta con dónde lo dijo o escribió: «Carta a su hermano», «Discurso», «El hombre en busca de sentido»."""
    f = re.sub(r"\s*\([^)]*\)", "", fuente or "").strip()
    f = re.split(r"[,;:.]", f)[0].strip().strip("«»\"“”")
    if not f or len(f) > 34:
        m = re.match(r"(Carta|Discurso|Entrevista|Conferencia|Mensaje|Poema|Ensayo|Novela|Obra)", fuente or "", re.I)
        return m.group(1).capitalize() if m else None
    return f[:1].upper() + f[1:]


def anio_fuente(fuente):
    m = re.search(r"\b(1\d{3}|20\d{2})\b", fuente or "")
    return int(m.group(1)) if m else None


def palabras_a_tokens(texto, tokens):
    """Segundo de cada palabra visible a partir de los tokens de Whisper (una palabra puede tener 0-n tokens)."""
    out, k, ultimo = [], 0, 0.0
    for w in texto.split():
        n = len(tts.norm(w))
        if n and k < len(tokens):
            ultimo = tokens[k]
        out.append(ultimo)
        k += n
    return out


def nombre_corto(nombre):
    return nombre


def preparar(rec_id, frase, autor, cita, quien, mujer, foto_autor, banco, tmp):
    """Datos (props) del Short, archivos en remotion/public/actual y textos para la descripción.
    `cita` = campos de la tabla Citas; `banco` = [(Autor, título Wikipedia)] de todo el banco."""
    pub = os.path.join(REMOTION, "public", "actual")
    shutil.rmtree(pub, ignore_errors=True)
    os.makedirs(pub)
    tit = cita.get("Wikipedia")
    datos = entidades([tit] + [t for _, t in banco])
    yo = datos.get(tit, {})
    opciones = elegir_opciones(tit, datos, banco, rec_id)
    correcta = random.Random(rec_id).randrange(3)
    # fotos: la del autor (la que ya usa el vídeo actual) y las de las opciones
    shutil.copy(foto_autor, os.path.join(pub, "autor.jpg"))
    tarjetas, creditos = [], []
    falsas = iter(opciones)
    for i in range(3):
        if i == correcta:
            tarjetas.append({"nombre": autor, "foto": "actual/autor.jpg", "foco": [0.5, 0.33], "zoom": 1.45})
        else:
            nombre, _, url, archivo = next(falsas)
            descargar(url, os.path.join(pub, f"op{i}.jpg"))
            tarjetas.append({"nombre": nombre, "foto": f"actual/op{i}.jpg", "foco": [0.5, 0.33], "zoom": 1.45})
            creditos.append(f"{nombre}: {credito_commons(archivo)}")
    # país, ciudad y años
    pais = None
    lug, paises = lugares([yo.get("lugar")]) if yo.get("lugar") else ({}, {})
    if yo.get("lugar") in lug:
        ciudad, lon, lat, qp = lug[yo["lugar"]]
        nom_pais, iso = paises.get(qp) or (None, None)
        if lon is not None and iso:
            pais = {"nombre": nom_pais, "id": str(iso), "ciudad": ciudad if ciudad != nom_pais else "", "lon": lon, "lat": lat}
    vida = None
    if yo.get("nace") and yo.get("muere") and yo["nace"][1] >= 9 and yo["muere"][1] >= 9:
        vida = {"nace": yo["nace"][0], "muere": yo["muere"][0]}
        a = anio_fuente(cita.get("Fuente", ""))
        if a and vida["nace"] < a <= vida["muere"]:
            vida.update(tramo=[a, a], rotulo=f"la frase es de {a}")
    firma = None
    if yo.get("firma"):
        try:
            descargar("https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(yo["firma"]) + "?width=700",
                      os.path.join(pub, "firma.png"))
            firma = "actual/firma.png"
        except requests.RequestException:
            pass
    tema = clasificar_tema(frase, autor)
    etiqueta = etiqueta_fuente(cita.get("Fuente", ""))
    # voz: pregunta | frases de la cita | opciones | autor
    fr = frases(frase)
    nombres = [t["nombre"] for t in tarjetas]
    txt_op = f"¿{nombres[0]}, {nombres[1]} o {nombres[2]}?"
    trozos = [PREGUNTA] + fr + [txt_op] + [autor + "."]
    v = tts.sintetizar_quiz(trozos, [1, len(fr), 1, 1], pub, voz="f" if mujer else "m")
    cita_vis = " ".join(texto_voz(f) for f in fr)
    tok_op = v["opciones"]["tokens"]
    # tarjeta i entra con la primera palabra de su nombre en «¿A, B o C?»
    ini_nombre, k = [], 0
    for n in nombres:
        ini_nombre.append(k)
        k += len(tts.norm(n)) + (1 if n == nombres[1] else 0)  # «o» entre la 2.ª y la 3.ª
    props = {
        "pregunta": PREGUNTA,
        "cita": cita_vis,
        "opciones": tarjetas,
        "correcta": correcta,
        "autor": autor,
        "quien": quien or "",
        "etiqueta": etiqueta,
        "tema": tema,
        "pais": pais,
        "vida": vida,
        "foto": "actual/autor.jpg",
        "foco": [0.5, 0.38],
        "firma": firma,
        "musica": "actual/musica.wav",
        "voz": {
            "gancho": {"archivo": "actual/gancho.wav", "dur": v["gancho"]["dur"], "palabras": palabras_a_tokens(PREGUNTA, v["gancho"]["tokens"])},
            "cita": {"archivo": "actual/cita.wav", "dur": v["cita"]["dur"], "palabras": palabras_a_tokens(cita_vis, v["cita"]["tokens"])},
            "opciones": {"archivo": "actual/opciones.wav", "dur": v["opciones"]["dur"], "palabras": tok_op,
                         "tarjetas": [min(i, len(tok_op) - 1) for i in ini_nombre]},
            "autor": {"archivo": "actual/autor.wav", "dur": v["autor"]["dur"], "palabras": palabras_a_tokens(autor, v["autor"]["tokens"])},
        },
    }
    # Los datos que faltan van como null (no se quitan): si no, Remotion los rellenaría con los del ejemplo
    descripcion = {"opciones": nombres, "letra_correcta": "ABC"[correcta], "creditos_opciones": creditos, "tema": tema}
    return props, descripcion


def duracion(props):
    v = props["voz"]
    return 0.1 + v["gancho"]["dur"] + v["cita"]["dur"] + v["opciones"]["dur"] + 0.9 + 0.5 + v["autor"]["dur"] - 0.2 + 2.0 + 0.7


def renderizar(props, salida, tmp, semilla):
    pub = os.path.join(REMOTION, "public")
    if not os.path.exists(os.path.join(pub, "sfx", "golpe.wav")):
        subprocess.run([sys.executable, os.path.join(AQUI, "sfx.py"), os.path.join(pub, "sfx")], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, os.path.join(AQUI, "musica.py"), os.path.join(pub, "actual", "musica.wav"),
                    f"{duracion(props) + 1:.2f}", str(semilla)], check=True, stdout=subprocess.DEVNULL)
    ruta_props = os.path.join(tmp, "props.json")
    json.dump(props, open(ruta_props, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["npx", "remotion", "render", "src/index.ts", "Quiz", salida, f"--props={ruta_props}",
                    "--crf=26", "--log=error", "--concurrency=2"], cwd=REMOTION, check=True)
    # Airtable admite 5 MB por adjunto: si pasa de 4,7 MB, se recomprime
    if os.path.getsize(salida) > 4.7e6:
        dur = duracion(props)
        br = int(4.2e6 * 8 / dur / 1000 - 140)
        tmp_mp4 = salida + ".tmp.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", salida, "-c:v", "libx264", "-preset", "slow",
                        "-b:v", f"{br}k", "-maxrate", f"{br}k", "-bufsize", f"{2 * br}k", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", tmp_mp4], check=True)
        os.replace(tmp_mp4, salida)
    return round(os.path.getsize(salida) / 1e6, 2), round(duracion(props), 2)
