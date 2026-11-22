"""Vídeo largo «¿Quién lo dijo? · El gran quiz de las frases» (22 nov 2026). SOLO LEE Airtable: no escribe ni publica.

Elige 20 preguntas del banco verificado (tabla Citas) repartidas en 4 niveles (5 por nivel) y lo monta con Remotion
(composición QuizLargo, 1920x1080). Lo deja en salida_largo/ con un .txt para la descripción (créditos de las fotos).
- Dificultad: por lo conocido que es el autor (número de Wikipedias en las que tiene artículo, de Wikidata).
- Tipos: quién lo dijo, completa la frase, verdadero o falso, de qué país era, en qué siglo vivió y adivina por pistas.
- Todo lo que se afirma sale de la tabla Citas y de Wikidata. Las opciones falsas son autores REALES del banco.
  En «Completa la frase», las dos palabras falsas las propone Gemini texto (nivel gratuito); si no contesta,
  esa pregunta se cambia por otra de otro tipo.
- Narración (23 nov 2026): una voz lee cada pregunta y cuenta la respuesta; gasta 5 audios del cupo de la
  voz de Gemini (los guarda en cache/voces: repetir el montaje con las mismas preguntas no gasta más).
Ajustes en .github/quiz_largo.txt (cambiarlo y subirlo lanza el montaje). Coste: 0 €."""
import json, os, random, re, shutil, subprocess, sys, tempfile, urllib.parse

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generar as g
import quiz
import tts

SALIDA = "salida_largo"
PUB = os.path.join(quiz.REMOTION, "public", "largo")
BANDERAS = os.path.join(quiz.REMOTION, "node_modules", "flag-icons", "flags", "4x3")
MUJER = {"Q6581072", "Q1052281"}
# tipos de cada nivel (si un autor no vale para un tipo, se cambia por «quien»)
REPARTO = [
    ["quien", "completa", "vf", "quien", "completa"],
    ["pais", "siglo", "quien", "vf", "completa"],
    ["pistas", "pais", "siglo", "quien", "vf"],
    ["pistas", "siglo", "pais", "completa", "quien"],
]
SITIO_TIPO = {"Carta": "en una carta", "Discurso": "en un discurso", "Entrevista": "en una entrevista",
              "Conferencia": "en una conferencia", "Mensaje": "en un mensaje", "Poema": "en un poema",
              "Ensayo": "en un ensayo", "Novela": "en una novela", "Obra": "en una de sus obras"}


def ajustes():
    a = {"SEMILLA": "1", "PREGUNTAS_POR_NIVEL": "5"}
    ruta = os.path.join(quiz.RAIZ, ".github", "quiz_largo.txt")
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            if "=" in linea and not linea.startswith("#"):
                k, v = linea.split("=", 1)
                a[k.strip().upper()] = v.strip()
    return a["SEMILLA"], int(a["PREGUNTAS_POR_NIVEL"] or 5)


def romano(n):
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def siglo_de(anio):
    return (anio - 1) // 100 + 1


# ---------------------------------------------------------------- Wikidata
def autores_wikidata(titulos):
    """{título enwiki: datos} con lo conocido que es (n.º de Wikipedias), años, lugar, ciudadanía, sexo y descripción."""
    res = {}
    titulos = [t for t in dict.fromkeys(titulos) if t]
    for i in range(0, len(titulos), 50):
        d = quiz._get({"action": "wbgetentities", "sites": "enwiki", "titles": "|".join(titulos[i:i + 50]),
                       "props": "claims|sitelinks|descriptions", "languages": "es", "redirects": "yes"})
        for e in d.get("entities", {}).values():
            if "missing" in e:
                continue
            c = e.get("claims", {})
            tit = e.get("sitelinks", {}).get("enwiki", {}).get("title")

            def valores(p):
                return [x["mainsnak"] for x in c.get(p, []) if x.get("mainsnak", {}).get("datavalue")]

            nace, muere, lugar = valores("P569"), valores("P570"), valores("P19")
            res[tit] = {
                "qid": e["id"],
                "fama": sum(1 for k in e.get("sitelinks", {}) if k.endswith("wiki") and k not in ("commonswiki", "specieswiki")),
                "nace": quiz._anio(nace[0]) if nace else None,
                "muere": quiz._anio(muere[0]) if muere else None,
                "lugar": lugar[0]["datavalue"]["value"]["id"] if lugar else None,
                "ciudadania": [x["datavalue"]["value"]["id"] for x in valores("P27")],
                "mujer": bool({x["datavalue"]["value"]["id"] for x in valores("P21")} & MUJER),
                "desc": e.get("descriptions", {}).get("es", {}).get("value", ""),
            }
    return res


def lugares_y_paises(qids):
    """{qid lugar: (ciudad, lon, lat, qid país)} y {qid país: (nombre, ISO numérico, ISO alfa-2)}."""
    out, paises = {}, {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        d = quiz._get({"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]), "props": "claims|labels", "languages": "es|en"})
        for q, e in d.get("entities", {}).items():
            c = e.get("claims", {})
            coord = next((x["mainsnak"]["datavalue"]["value"] for x in c.get("P625", []) if x.get("mainsnak", {}).get("datavalue")), None)
            pais = next((x["mainsnak"]["datavalue"]["value"]["id"] for x in c.get("P17", []) if x.get("mainsnak", {}).get("datavalue")), None)
            lab = e.get("labels", {})
            out[q] = ((lab.get("es") or lab.get("en") or {}).get("value", ""), coord["longitude"] if coord else None,
                      coord["latitude"] if coord else None, pais)
            if pais:
                paises[pais] = None
    ps = list(paises)
    for i in range(0, len(ps), 50):
        d = quiz._get({"action": "wbgetentities", "ids": "|".join(ps[i:i + 50]), "props": "claims|labels", "languages": "es|en"})
        for q, e in d.get("entities", {}).items():
            c = e.get("claims", {})
            v = lambda p: next((x["mainsnak"]["datavalue"]["value"] for x in c.get(p, []) if x.get("mainsnak", {}).get("datavalue")), None)
            lab = e.get("labels", {})
            paises[q] = ((lab.get("es") or lab.get("en") or {}).get("value", ""), v("P299"), (v("P297") or "").lower())
    return out, paises


# ---------------------------------------------------------------- textos
def dato_fuente(fuente, a):
    """«Aparece en «El segundo sexo» (1949).» / «Lo dejó escrito en una carta.» o None si la fuente no es clara.
    El año solo se pone si cae dentro de su vida (la Fuente puede llevar números de verso o de página)."""
    fuente = fuente or ""
    m = re.search(r"«([^«»]{3,40})»", fuente)  # si la Fuente trae un título entre comillas, ese es la obra
    delante = fuente[:m.start()].strip().rstrip(",;:").strip() if m else ""
    if m and delante and len(delante) <= 34 and a["nombre"].lower() not in delante.lower():
        m = None  # «Fausto, «Gabinete de estudio»»: lo de delante es la obra y lo de las comillas, una parte
    et = m.group(1).strip() if m else quiz.etiqueta_fuente(fuente)
    if not et or re.search(r"[«»\"“”]|t[íi]tulo|exclamaci|famos|atribu|citad|recogid", et, re.I):
        return None
    if a["nombre"].lower() in et.lower():
        return None
    anio = quiz.anio_fuente(fuente)
    if anio and not ((a["nace"] or -9999) < anio <= (a["muere"] or 9999)):
        anio = None
    if et in SITIO_TIPO:
        return f"Lo dejó escrito {SITIO_TIPO[et]}" + (f" en {anio}." if anio else ".")
    if re.match(r"Carta a \w", et):  # «Carta a Meneceo» → «Lo escribió en una carta a Meneceo.»
        return f"Lo escribió en una c{et[1:]}" + (f" en {anio}." if anio else ".")
    if re.match(r"(Art[íi]culo|Poema|Carta|Discurso|Ensayo|Novela|Libro|Obra)\b", et):
        return None  # «Artículo» o «Poema» sin título claro
    return f"Aparece en «{et}»" + (f" ({anio})." if anio else ".")


def dato_vida(a):
    if a.get("ciudad") and a.get("nace") and a.get("muere"):
        return f"Nació en {a['ciudad']} en {a['nace']} y murió en {a['muere']}."
    if a.get("nace") and a.get("muere"):
        return f"Vivió entre {a['nace']} y {a['muere']}."
    return None


def profesion(desc):
    """«escritor, poeta y dramaturgo español (1580-1645)» → «Escritor, poeta y dramaturgo» (sin gentilicio si cabe)."""
    d = re.sub(r"\s*\([^)]*\)", "", desc or "").strip().rstrip(".")
    palabras = d.split()
    if len(palabras) > 1 and re.search(r"(és|esa|ol|ola|ano|ana|ino|ina|ense|o|a)$", palabras[-1]) and palabras[-1][0].islower() \
            and palabras[-2] not in ("y", "e", "de", "del") and not palabras[-2].endswith(","):
        d = " ".join(palabras[:-1])  # quita el gentilicio del final («español», «francesa»…)
    if len(d) > 34:
        d = d[:34].rsplit(" ", 1)[0].rstrip(",; y")
    return d[:1].upper() + d[1:] if d else None


def palabras_falsas(cita, palabra):
    """Dos palabras que encajan en la frase en lugar de `palabra` pero le cambian el sentido (Gemini texto)."""
    clave = os.environ.get("GEMINI_API_KEY", "")
    if not clave:
        return None
    hueco = cita[: cita.rfind(palabra)] + "____" + cita[cita.rfind(palabra) + len(palabra):]
    prompt = ("Juego de completar frases célebres. En esta frase falta una palabra:\n"
              f"«{hueco}» (la correcta es «{palabra}»).\n"
              "Da DOS palabras distintas de la correcta que encajen bien en la frase (misma categoría gramatical, mismo "
              "género y número, sin faltas), que suenen creíbles pero cambien el sentido. Responde solo las dos palabras "
              "separadas por una coma, en minúsculas.")
    for modelo in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
        try:
            r = requests.post(f"{tts.API}/models/{modelo}:generateContent", timeout=60,
                              headers={"x-goog-api-key": clave, "Content-Type": "application/json"},
                              json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}})
            if r.status_code >= 400:
                continue
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
            ws = [re.sub(r"[^\wáéíóúüñ]", "", w) for w in txt.split(",")]
            ws = [w for w in ws if w and w != palabra.lower() and len(w) <= 14 and " " not in w]
            if len(set(ws)) >= 2:
                return list(dict.fromkeys(ws))[:2]
        except Exception:
            pass
    return None


# ---------------------------------------------------------------- narración (23 nov 2026)
# Una voz (Gemini «Enceladus», español neutro) que lee cada pregunta y cuenta la respuesta. 5 audios en total
# (intro y final + uno por nivel), cortados por pregunta en las pausas; se guardan en cache/voces.
VOZ_LARGO = "Enceladus"
ESTILO_LARGO = ("A friendly quiz host talking to people at home, like a relaxed quiz night among friends. Neutral "
                "Spanish (español neutro), with no strong regional accent, easy to understand in Mexico, Colombia, "
                "Argentina, the United States and Spain. Warm, close to the microphone and unhurried, because many "
                "listeners are older. Read each quote slowly, savouring it; say the options in a playful way; "
                "reveal each answer with a hint of a smile, then tell the fact like a curious friend. "
                "Never sounds like an advert or a radio announcer.")
NIVEL_VOZ = ["Nivel uno: fácil. Empezamos con frases muy conocidas.",
             "Nivel dos: medio. Ahora, un poco más difícil.",
             "Nivel tres: difícil. Aquí se separan los que más saben.",
             "Nivel cuatro: experto. Solo para sabios."]
NUM_SIGLO = {1: "primero", 2: "segundo", 3: "tercero", 4: "cuarto", 5: "quinto", 6: "sexto", 7: "séptimo",
             8: "octavo", 9: "noveno", 10: "décimo", 11: "once", 12: "doce", 13: "trece", 14: "catorce",
             15: "quince", 16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve", 20: "veinte",
             21: "veintiuno"}
# tiempos fijos de cada pregunta (s): la voz empieza en VOZ_A; reloj de 5 s; la respuesta, al revelar
VOZ_A, RELOJ, VOZ_B = 0.6, 5.0, 0.25


def de_romano(r):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    n = 0
    for k, c in enumerate(r):
        v = vals[c]
        n += -v if k + 1 < len(r) and vals[r[k + 1]] > v else v
    return n


def siglo_voz(rotulo):
    """«s. XIX» / «Siglo XIX» → «diecinueve»."""
    return NUM_SIGLO[de_romano(rotulo.split()[-1])]


def o_lista(xs):
    return ", ".join(xs[:-1]) + " o " + xs[-1]


def con_quien(a):
    """«Francisco de Goya, pintor y grabador» (sin profesión si Wikidata no la da)."""
    p = profesion(a.get("desc"))
    return f"{a['nombre']}, {p[0].lower() + p[1:]}" if p else a["nombre"]


def guion(n, p, a):
    """Trozos que lee la voz: (planteamiento, respuesta). El índice de cada trozo se usa para sincronizar:
    planteamiento = [enunciado, cita?, opciones] o, en «pistas», [enunciado, pista1, pista2, pista3]."""
    t, dato = p["tipo"], p["ficha"]["dato"]
    # en «país» y «siglo» la respuesta no dice el nombre: el dato lo lleva («Carl Sagan vivió entre…»)
    dato_dicho = (f"{a['nombre']} n{dato[1:]}" if dato.startswith("Nació") else
                  f"{a['nombre']} v{dato[1:]}" if dato.startswith("Vivió") else dato) if t in ("pais", "siglo") else dato
    if t == "quien":
        return ([f"Pregunta {n}. ¿Quién dijo esta frase?", f"«{p['cita']}»", f"¿{o_lista([o['nombre'] for o in p['opciones']])}?"],
                [f"Lo dijo {con_quien(a)}.", dato_dicho])
    if t == "completa":
        return ([f"Pregunta {n}. Completa la frase.", f"«{p['antes']}…»", f"¿{o_lista(p['opciones'])}?"],
                [f"La palabra que falta es «{p['opciones'][p['correcta']]}».", f"Lo dijo {con_quien(a)}. {dato_dicho}"])
    if t == "vf":
        if p["verdadero"]:
            b = ["¡Verdadero!", f"Es de {con_quien(a)}. {dato_dicho}"]
        else:
            b = ["¡Falso!", f"No es de {p['propuesto']['nombre']}, sino de {con_quien(a)}."]
        return [f"Pregunta {n}. ¿Verdadero o falso?", f"«{p['cita']}»", f"¿Es de {p['propuesto']['nombre']}?"], b
    if t == "pais":
        pa = p["paises"][p["correcta"]]["nombre"]
        return ([f"Pregunta {n}. ¿De qué país era {a['nombre']}?", f"¿{o_lista([x['nombre'] for x in p['paises']])}?"],
                [f"{pa}.", dato_dicho])
    if t == "siglo":
        ws = [siglo_voz(o["rotulo"]) for o in p["opciones"]]
        return ([f"Pregunta {n}. ¿En qué siglo vivió {a['nombre']}?", f"¿En el siglo {ws[0]}, en el {ws[1]} o en el {ws[2]}?"],
                [f"En el siglo {ws[p['correcta']]}.", dato_dicho])
    # pistas
    s, pais, prof = (x["texto"] for x in p["pistas"])
    de = {"Reino Unido": "del Reino Unido", "Estados Unidos": "de Estados Unidos", "Países Bajos": "de los Países Bajos"}.get(pais, f"de {pais}")
    return ([f"Pregunta {n}. ¿Quién es? Te doy tres pistas.", f"Vivió en el siglo {siglo_voz(s)}.", f"Era {de}.", f"{prof}."],
            [f"Es {a['nombre']}.", dato_dicho])


def tiempos_pregunta(p, va, vb):
    """Momentos (s) de cada fase de la pregunta según lo que dura la voz."""
    tr = va["trozos"]
    T = {"pregunta": 0.4, "vozA": VOZ_A}
    if p["tipo"] == "pistas":
        T["pistas"] = [round(VOZ_A + x[0], 3) for x in tr[1:4]]
        T["opciones"] = T["pistas"][-1]
    else:
        T["opciones"] = round(VOZ_A + tr[-1][0], 3)
        if len(tr) == 3:
            T["cita"] = [round(VOZ_A + tr[1][0], 3), round(VOZ_A + tr[1][1], 3)]
    T["reloj"] = round(VOZ_A + va["dur"] + 0.4, 3)
    T["rev"] = round(T["reloj"] + RELOJ, 3)
    T["vozB"] = round(T["rev"] + VOZ_B, 3)
    T["dato"] = round(max(T["rev"] + 1.0, T["vozB"] + vb["trozos"][0][1] + 0.15), 3)
    T["fin"] = round(max(T["vozB"] + vb["dur"] + 1.2, T["dato"] + 3.0), 3)
    return T


def narrar(preguntas, total):
    """Genera las voces en public/largo/voz y devuelve (voces, duraciones) para los props.
    Añade a cada pregunta sus tiempos (`T`) y sus audios (`voz`). Lanza tts.SinVoz si no hay voz."""
    carpeta = os.path.join(PUB, "voz")
    os.makedirs(carpeta, exist_ok=True)
    rel = lambda nombre: f"largo/voz/{nombre}.wav"
    # intro y final, en un solo audio
    r = tts.sintetizar_partes(
        ["¿Quién lo dijo?", f"{total} frases célebres en cuatro niveles, de fácil a experto.",
         "Tienes cinco segundos para cada respuesta. Cuenta tus aciertos y, al final, descubre tu nivel.",
         "¿Cuántas acertaste?", f"Si has acertado {total - 2} o más, eres todo un sabio.",
         "Escribe tu resultado en los comentarios, y suscríbete para no perderte el próximo quiz."],
        [3, 3], ["intro", "final"], carpeta, VOZ_LARGO, ESTILO_LARGO, "largo")
    voces = {"intro": rel("intro"), "final": rel("final"), "niveles": []}
    dur = {"intro": round(max(6.0, 0.5 + r["intro"]["dur"] + 1.2), 3), "final": round(max(9.0, r["final"]["dur"] + 4.5), 3),
           "cortinilla": []}
    for nivel in range(4):
        qs = [(k, p) for k, p in enumerate(preguntas) if p["nivel"] == nivel]
        if not qs:
            continue
        trozos, grupos, nombres = [NIVEL_VOZ[nivel]], [1], [f"nivel{nivel}"]
        for k, p in qs:
            a_txt, b_txt = guion(k + 1, p, p["_autor"])
            trozos += a_txt + b_txt
            grupos += [len(a_txt), len(b_txt)]
            nombres += [f"p{k}a", f"p{k}b"]
        r = tts.sintetizar_partes(trozos, grupos, nombres, carpeta, VOZ_LARGO, ESTILO_LARGO, "largo")
        voces["niveles"].append(rel(f"nivel{nivel}"))
        dur["cortinilla"].append(round(max(2.6, 0.3 + r[f"nivel{nivel}"]["dur"] + 0.9), 3))
        for k, p in qs:
            p["T"] = tiempos_pregunta(p, r[f"p{k}a"], r[f"p{k}b"])
            p["voz"] = {"a": rel(f"p{k}a"), "b": rel(f"p{k}b")}
        print(f"[voz] nivel {nivel + 1}: {sum(r[x]['dur'] for x in nombres):.0f} s de voz ({tts.ULTIMO.get('modelo')})", flush=True)
    return voces, dur


# ---------------------------------------------------------------- preparación
class Montaje:
    def __init__(self, semilla):
        self.rnd = random.Random(semilla)
        self.fotos = {}      # título → ruta relativa en public
        self.creditos = {}   # nombre → crédito
        self.banderas = set()

    def foto(self, nombre, tit):
        """Foto libre del autor en public/largo (None si no tiene)."""
        if tit in self.fotos:
            return self.fotos[tit]
        url, archivo = quiz.foto_libre(tit)
        if not url:
            self.fotos[tit] = None
            return None
        rel = f"largo/{g.slug(nombre)}.jpg"
        quiz.descargar(url, os.path.join(quiz.REMOTION, "public", rel))
        try:
            self.creditos[nombre] = quiz.credito_commons(archivo)
        except requests.RequestException:
            self.creditos[nombre] = archivo
        self.fotos[tit] = rel
        return rel

    def bandera(self, iso2):
        ruta = os.path.join(BANDERAS, f"{iso2}.svg")
        if not iso2 or not os.path.exists(ruta):
            return None
        shutil.copy(ruta, os.path.join(PUB, "banderas", f"{iso2}.svg"))
        return f"largo/banderas/{iso2}.svg"


def main():
    semilla, por_nivel = ajustes()
    shutil.rmtree(PUB, ignore_errors=True)
    os.makedirs(os.path.join(PUB, "banderas"))
    os.makedirs(SALIDA, exist_ok=True)
    m = Montaje(semilla)

    citas = [c["fields"] for c in g.listar(g.T_CITAS, ["Cita", "Autor", "Wikipedia", "Fuente"]) if c["fields"].get("Wikipedia") and c["fields"].get("Cita")]
    por_autor = {}
    for c in citas:
        por_autor.setdefault(c["Wikipedia"], {"nombre": c["Autor"].strip(), "citas": []})["citas"].append(c)
    wd = autores_wikidata(list(por_autor))
    lug, paises = lugares_y_paises([d["lugar"] for d in wd.values()])

    autores = []
    for tit, a in por_autor.items():
        d = wd.get(tit)
        if not d:
            continue
        x = {"tit": tit, "nombre": a["nombre"], "citas": a["citas"], **d, "pais": None, "ciudad": None}
        x["nace"] = d["nace"][0] if d["nace"] and d["nace"][1] >= 9 else None
        x["muere"] = d["muere"][0] if d["muere"] and d["muere"][1] >= 9 else None
        if d["lugar"] in lug:
            ciudad, lon, lat, qp = lug[d["lugar"]]
            nom, iso, iso2 = paises.get(qp) or (None, None, None)
            # el país de nacimiento vale si es su ciudadanía o si nació antes de 1850 (estados históricos)
            if lon is not None and iso and (qp in d["ciudadania"] or not d["ciudadania"] or (x["nace"] or 9999) < 1850):
                x["pais"] = {"nombre": nom, "id": str(iso), "ciudad": ciudad if ciudad != nom else "", "lon": lon, "lat": lat, "iso2": iso2, "qid": qp}
            x["ciudad"] = ciudad or None
        autores.append(x)
    autores.sort(key=lambda a: -a["fama"])
    print(f"{len(autores)} autores en el banco; los más conocidos: " + ", ".join(f"{a['nombre']} ({a['fama']})" for a in autores[:8]), flush=True)

    # 4 grupos por fama (cuartiles); cada nivel saca sus autores de su grupo
    n = len(autores)
    grupos = [autores[k * n // 4:(k + 1) * n // 4] for k in range(4)]
    for gr in grupos:
        m.rnd.shuffle(gr)
    usados = set()
    preguntas = []
    for nivel, tipos in enumerate(REPARTO):
        for tipo in tipos[:por_nivel]:
            hecha = None
            for intento_tipo in (tipo, "quien"):
                for a in grupos[nivel]:
                    if a["tit"] in usados:
                        continue
                    try:
                        hecha = pregunta(m, intento_tipo, nivel, a, autores)
                    except Exception as e:
                        print(f"[aviso] {a['nombre']} ({intento_tipo}): {e}", flush=True)
                        hecha = None
                    if hecha:
                        usados.add(a["tit"])
                        break
                if hecha:
                    break
            if hecha:
                hecha["_autor"] = a  # para la narración (se quita antes de montar)
                preguntas.append(hecha)
                print(f"[ok] nivel {nivel + 1} · {hecha['tipo']} · {hecha['ficha']['autor']}", flush=True)
            else:
                print(f"[falta] nivel {nivel + 1} · {tipo}: ningún autor sirve", flush=True)

    # narración: sin voz de Gemini no se monta (se repite otro día; lo ya hecho queda en cache/voces)
    voces, duraciones = narrar(preguntas, len(preguntas))
    for p in preguntas:
        p.pop("_autor", None)

    # música variada (creada con código): intro, un estilo por nivel y final, del largo de cada tramo
    os.makedirs(os.path.join(PUB, "musica"), exist_ok=True)
    tramos = [duraciones["cortinilla"][n] + sum(p["T"]["fin"] for p in preguntas if p["nivel"] == n) + 1 for n in range(4)]
    estilos = [("intro", duraciones["intro"] + 1)] + list(zip(("facil", "medio", "dificil", "experto"), tramos)) + [("final", duraciones["final"] + 1)]
    for k, (est, seg) in enumerate(estilos):
        subprocess.run([sys.executable, os.path.join(quiz.AQUI, "musica_variada.py"), est, f"{seg:.1f}",
                        os.path.join(PUB, "musica", f"{est}.wav"), str(k + 7)], check=True, stdout=subprocess.DEVNULL)
    pub_raiz = os.path.join(quiz.REMOTION, "public")
    if not os.path.exists(os.path.join(pub_raiz, "sfx", "golpe.wav")):
        subprocess.run([sys.executable, os.path.join(quiz.AQUI, "sfx.py"), os.path.join(pub_raiz, "sfx")], check=True, stdout=subprocess.DEVNULL)

    props = {
        "titulo": "¿Quién lo dijo?",
        "subtitulo": "El gran quiz de las frases",
        "total": len(preguntas),
        "preguntas": preguntas,
        "musica": {"intro": "largo/musica/intro.wav", "niveles": [f"largo/musica/{e}.wav" for e in ("facil", "medio", "dificil", "experto")],
                   "final": "largo/musica/final.wav"},
        "voces": voces,
        "duraciones": duraciones,
    }
    with tempfile.TemporaryDirectory() as tmp:
        ruta_props = os.path.join(tmp, "props.json")
        json.dump(props, open(ruta_props, "w", encoding="utf-8"), ensure_ascii=False)
        shutil.copy(ruta_props, os.path.join(SALIDA, "props.json"))
        salida = os.path.abspath(os.path.join(SALIDA, "quiz-largo.mp4"))
        subprocess.run(["npx", "remotion", "render", "src/index.ts", "QuizLargo", salida, f"--props={ruta_props}",
                        "--crf=22", "--log=error", "--concurrency=2"], cwd=quiz.REMOTION, check=True)
    # texto para la descripción: créditos de las fotos (no salen en el vídeo)
    lineas = ["Preguntas:"] + [f"{k + 1}. [{['Fácil', 'Medio', 'Difícil', 'Experto'][p['nivel']]}] {p['tipo']} · {p['ficha']['autor']}"
                               for k, p in enumerate(preguntas)]
    lineas += ["", "Fotos (Wikimedia Commons):"] + [f"{k}: {v}" for k, v in m.creditos.items()]
    lineas += ["", "Banderas: flag-icons (MIT). Mapas: Natural Earth (dominio público). Música: original del canal."]
    open(os.path.join(SALIDA, "descripcion.txt"), "w", encoding="utf-8").write("\n".join(lineas) + "\n")
    print("\n".join(lineas))
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as fh:
            fh.write("### Vídeo largo quiz (no se ha escrito nada en Airtable)\n\n```\n" + "\n".join(lineas) + "\n```\n")
    if len(preguntas) < 4 * por_nivel:
        print(f"[aviso] solo {len(preguntas)} preguntas", flush=True)


def ficha(m, a, dato):
    return {"autor": a["nombre"], "foto": m.foto(a["nombre"], a["tit"]), "foco": [0.5, 0.3], "dato": dato}


def cita_corta(m, a, maximo):
    ok = [c for c in a["citas"] if len(c["Cita"].strip()) <= maximo]
    return m.rnd.choice(ok) if ok else None


def parecidos(m, a, autores, cuantos, con_foto=True):
    """Autores reales del banco de época y país parecidos (como en los Shorts)."""
    cand = []
    for o in autores:
        if o["tit"] == a["tit"]:
            continue
        dist = abs(o["nace"] - a["nace"]) / 40 if (o["nace"] and a["nace"]) else 6
        if set(o["ciudadania"]) & set(a["ciudadania"]):
            dist -= 1.5
        cand.append((dist + m.rnd.random() * 0.8, o))
    cand.sort(key=lambda x: x[0])
    out = []
    for _, o in cand:
        if not con_foto or m.foto(o["nombre"], o["tit"]):
            out.append(o)
        if len(out) == cuantos:
            break
    return out if len(out) == cuantos else None


def tarjeta(m, a):
    return {"nombre": a["nombre"], "foto": m.foto(a["nombre"], a["tit"]), "foco": [0.5, 0.33], "zoom": 1.45}


def pregunta(m, tipo, nivel, a, autores):
    if not m.foto(a["nombre"], a["tit"]):
        return None
    base = {"nivel": nivel, "tipo": tipo}
    if tipo == "quien":
        c = cita_corta(m, a, 110)
        otros = c and parecidos(m, a, autores, 2)
        if not otros:
            return None
        ops = [tarjeta(m, a)] + [tarjeta(m, o) for o in otros]
        m.rnd.shuffle(ops)
        dato = dato_fuente(c.get("Fuente"), a) or dato_vida(a)
        return {**base, "cita": c["Cita"].strip(), "opciones": ops, "correcta": [o["nombre"] for o in ops].index(a["nombre"]),
                "ficha": ficha(m, a, dato or a["nombre"])}
    if tipo == "vf":
        c = cita_corta(m, a, 110)
        if not c:
            return None
        verdadero = m.rnd.random() < 0.5
        if verdadero:
            prop, dato = a, dato_fuente(c.get("Fuente"), a) or dato_vida(a)
        else:
            otros = parecidos(m, a, autores, 1)
            if not otros:
                return None
            prop = otros[0]
            dato = f"No es de {prop['nombre']}, sino de {a['nombre']}."
        return {**base, "cita": c["Cita"].strip(), "propuesto": tarjeta(m, prop), "verdadero": verdadero,
                "ficha": ficha(m, a, dato or a["nombre"])}
    if tipo == "completa":
        cands = [c for c in a["citas"] if len(c["Cita"].strip()) <= 70 and re.search(r"[\wáéíóúñ]{4,}[.»”\"]?$", c["Cita"].strip())]
        m.rnd.shuffle(cands)
        for c in cands:
            txt = c["Cita"].strip().rstrip(".»”\"").strip()
            antes, palabra = txt.rsplit(" ", 1)
            falsas = palabras_falsas(txt, palabra)
            if not falsas:
                continue
            ops = [palabra] + falsas
            m.rnd.shuffle(ops)
            dato = dato_fuente(c.get("Fuente"), a) or dato_vida(a)
            return {**base, "antes": antes, "opciones": ops, "correcta": ops.index(palabra), "ficha": ficha(m, a, dato or a["nombre"])}
        return None
    if tipo == "pais":
        p = a["pais"]
        if not p:
            return None
        otros = {}
        for o in sorted(autores, key=lambda _: m.rnd.random()):
            q = o["pais"]
            if q and q["qid"] != p["qid"] and q["qid"] not in otros and m.bandera(q["iso2"]):
                otros[q["qid"]] = q
            if len(otros) == 2:
                break
        if len(otros) < 2 or not m.bandera(p["iso2"]):
            return None
        ps = [p] + list(otros.values())
        m.rnd.shuffle(ps)
        limpio = [{"nombre": x["nombre"], "id": x["id"], "ciudad": x["ciudad"], "lon": x["lon"], "lat": x["lat"],
                   "bandera": m.bandera(x["iso2"])} for x in ps]
        return {**base, "paises": limpio, "correcta": [x["qid"] for x in ps].index(p["qid"]),
                "ficha": ficha(m, a, dato_vida(a) or f"Nació en {p['nombre']}.")}
    if tipo == "siglo":
        if not (a["nace"] and a["muere"]) or a["nace"] < 1000:
            return None
        s = siglo_de((a["nace"] + a["muere"]) // 2)
        vividos = set(range(siglo_de(a["nace"]), siglo_de(a["muere"]) + 1))
        cerca = [x for x in (s - 2, s + 2) if x not in vividos and 1 <= x <= 20]
        lejos = [x for x in (s - 3, s + 3) if x not in vividos and 1 <= x <= 20]
        m.rnd.shuffle(cerca)
        m.rnd.shuffle(lejos)
        falsos = cerca + lejos
        if len(falsos) < 2:
            return None
        ss = sorted([s] + falsos[:2])
        ops = [{"rotulo": f"s. {romano(x)}", "desde": (x - 1) * 100, "hasta": x * 100} for x in ss]
        return {**base, "opciones": ops, "correcta": ss.index(s), "vida": {"nace": a["nace"], "muere": a["muere"]},
                "ficha": ficha(m, a, f"Vivió entre {a['nace']} y {a['muere']}.")}
    if tipo == "pistas":
        prof = profesion(a["desc"])
        if not (a["nace"] and a["muere"] and a["pais"] and prof):
            return None
        s = siglo_de((a["nace"] + a["muere"]) // 2)
        c = cita_corta(m, a, 110)
        dato = (c and dato_fuente(c.get("Fuente"), a)) or dato_vida(a)
        return {**base, "pistas": [{"icono": "🕰️", "texto": f"Siglo {romano(s)}"}, {"icono": "📍", "texto": a["pais"]["nombre"]},
                                   {"icono": "✒️", "texto": prof}],
                "recorte": None, "proporcion": 1.3, "ficha": ficha(m, a, dato or a["nombre"])}
    return None


if __name__ == "__main__":
    main()
