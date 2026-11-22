"""Vídeo largo «¿Quién lo dijo? · El gran quiz de las frases» (22 nov 2026). SOLO LEE Airtable: no escribe ni publica.

Elige 20 preguntas del banco verificado (tabla Citas) repartidas en 4 niveles (5 por nivel) y lo monta con Remotion
(composición QuizLargo, 1920x1080). Lo deja en salida_largo/ con un .txt para la descripción (créditos de las fotos).
- Dificultad: por lo conocido que es el autor (número de Wikipedias en las que tiene artículo, de Wikidata).
- Tipos: quién lo dijo, completa la frase, verdadero o falso, de qué país era, en qué siglo vivió y adivina por pistas.
- Todo lo que se afirma sale de la tabla Citas y de Wikidata. Las opciones falsas son autores REALES del banco.
  En «Completa la frase», las dos palabras falsas las propone Gemini texto (nivel gratuito); si no contesta,
  esa pregunta se cambia por otra de otro tipo.
- Sin voz por ahora (no gasta cupo de la voz de Gemini).
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
def dato_fuente(fuente):
    """«Aparece en «El segundo sexo» (1949).» / «La escribió en una carta.» o None."""
    et = quiz.etiqueta_fuente(fuente or "")
    if not et:
        return None
    a = quiz.anio_fuente(fuente)
    if et in SITIO_TIPO:
        return f"Lo dejó escrito {SITIO_TIPO[et]}" + (f" en {a}." if a else ".")
    return f"Aparece en «{et}»" + (f" ({a})." if a else ".")


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
    if len(palabras) > 1 and re.search(r"(és|esa|ano|ana|ino|ina|ense|o|a)$", palabras[-1]) and palabras[-1][0].islower() \
            and palabras[-2] not in ("y", "e", "de", "del"):
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
                preguntas.append(hecha)
                print(f"[ok] nivel {nivel + 1} · {hecha['tipo']} · {hecha['ficha']['autor']}", flush=True)
            else:
                print(f"[falta] nivel {nivel + 1} · {tipo}: ningún autor sirve", flush=True)

    # música variada (creada con código): intro, un estilo por nivel y final
    os.makedirs(os.path.join(PUB, "musica"), exist_ok=True)
    tramo = 2.6 + por_nivel * 13 + 1
    estilos = [("intro", 7), ("facil", tramo), ("medio", tramo), ("dificil", tramo), ("experto", tramo), ("final", 10)]
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
        dato = dato_fuente(c.get("Fuente")) or dato_vida(a)
        return {**base, "cita": c["Cita"].strip(), "opciones": ops, "correcta": [o["nombre"] for o in ops].index(a["nombre"]),
                "ficha": ficha(m, a, dato or a["nombre"])}
    if tipo == "vf":
        c = cita_corta(m, a, 110)
        if not c:
            return None
        verdadero = m.rnd.random() < 0.5
        if verdadero:
            prop, dato = a, dato_fuente(c.get("Fuente")) or dato_vida(a)
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
            dato = dato_fuente(c.get("Fuente")) or dato_vida(a)
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
        cerca = [x for x in (s - 2, s + 2) if x not in vividos and 1 <= x <= 21]
        lejos = [x for x in (s - 3, s + 3) if x not in vividos and 1 <= x <= 21]
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
        dato = (c and dato_fuente(c.get("Fuente"))) or dato_vida(a)
        return {**base, "pistas": [{"icono": "🕰️", "texto": f"Siglo {romano(s)}"}, {"icono": "📍", "texto": a["pais"]["nombre"]},
                                   {"icono": "✒️", "texto": prof}],
                "recorte": None, "proporcion": 1.3, "ficha": ficha(m, a, dato or a["nombre"])}
    return None


if __name__ == "__main__":
    main()
