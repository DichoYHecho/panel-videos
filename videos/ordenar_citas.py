"""Orden de las citas que aún no se han usado (24 nov 2026). Make (escenario 01, domingo y miércoles a las 02:00)
coge las 7 primeras por el campo «Orden» de Citas; este script recalcula ese campo antes, para que salgan primero:

1. Efemérides: autores con aniversario de nacimiento o muerte en los próximos DIAS días (más si es redondo).
2. Público: 72 % mayor de 45 años, sobre todo de México, España, EE. UU., Argentina y Colombia. Suben los autores
   de América Latina (y algo los de España) y las frases de fe, consuelo y sabiduría (las que más suscriptores dan).
3. Lo conocido que es el autor (número de Wikipedias con artículo suyo, de Wikidata).
4. Variedad: nunca dos citas del mismo autor en el mismo lote de 7, ni un autor publicado en las últimas 2 semanas.

Solo cambia «Orden» de las citas sin usar. Variables: SOLO_MIRAR=1 (no escribe nada; enseña las primeras 30).
Secrets: AIRTABLE_TOKEN. Coste: 0 € (API pública de Wikidata)."""
import datetime as dt, json, math, os, re, time, unicodedata, urllib.error, urllib.parse, urllib.request

BASE, T_CITAS, T_PUB = "appeuC0uIAlqqp1h9", "tbluECdgOggDiZIFJ", "tbl7ynqI9bJrWtR0m"
SOLO_MIRAR = os.environ.get("SOLO_MIRAR") == "1"
DIAS = 4            # Make genera 7 publicaciones (2 al día) que salen en los 3-4 días siguientes
LOTE = 7
UA = {"User-Agent": "DichoYHechoBot/1.1 (dichoyhecho66@gmail.com) GitHubActions"}
# ciudadanía (Wikidata P27): América Latina y España
LATAM = {"Q96", "Q414", "Q739", "Q298", "Q419", "Q241", "Q77", "Q717", "Q811", "Q774", "Q736", "Q750", "Q733",
         "Q786", "Q1183", "Q800", "Q783", "Q792", "Q804", "Q155"}  # … y Brasil (Q155)
ESPANA = {"Q29"}
TEMAS_BUENOS = re.compile(r"\b(dios|fe|alma|almas|esperanza|oraci[oó]n|rezar|cielo|consuelo|consolar|perd[oó]n|perdonar|"
                          r"bondad|gracia|sabidur[ií]a|sabio|sabia|virtud|paciencia|humildad|gratitud|agradecer)\b", re.I)


# Norma de engagement (27 nov 2026): lo religioso es lo que más funciona (Santa Teresa, el Short más visto y con
# más comentarios), seguido de la «sabiduría para la vida» (Feynman, Hipócrates, Frankl, Marco Aurelio, Sócrates…).
RELIGIOSOS = re.compile(r"\b(San|Santa|Santo|Sor|Fray|Papa|Madre Teresa|Teresa de Calcuta|Juan Pablo|John Donne)\b")
SABIOS = re.compile(r"S[oó]crates|S[eé]neca|Marco Aurelio|Epicteto|Confucio|Lao[- ]?Ts[eé]|Arist[oó]teles|Plat[oó]n|"
                    r"Hip[oó]crates|Cicer[oó]n|Di[oó]genes|Mart[ií]|Frankl|Feynman|Einstein|Pascal|Gandhi|Luther King")


def airtable(metodo, ruta, datos=None):
    for _ in range(4):
        req = urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{ruta}", method=metodo,
                                     data=json.dumps(datos).encode() if datos is not None else None,
                                     headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}",
                                              "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(31)
                continue
            raise RuntimeError(f"Airtable {e.code}: {e.read().decode()[:300]}")
    raise RuntimeError("Airtable sigue contestando 429")


def todas(tabla, campos, formula=None):
    out, offset = [], None
    while True:
        q = [("pageSize", "100")] + [("fields[]", c) for c in campos] + ([("filterByFormula", formula)] if formula else [])
        if offset:
            q.append(("offset", offset))
        d = airtable("GET", f"{tabla}?{urllib.parse.urlencode(q)}")
        out += d["records"]
        offset = d.get("offset")
        if not offset:
            return out


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def wikidata(titulos):
    """{título enwiki: {fama, ciudadania, nace (m, d), muere (m, d), anio_nace, anio_muere}}."""
    res = {}
    for i in range(0, len(titulos), 50):
        q = urllib.parse.urlencode({"action": "wbgetentities", "format": "json", "sites": "enwiki", "redirects": "yes",
                                    "titles": "|".join(titulos[i:i + 50]), "props": "claims|sitelinks"})
        with urllib.request.urlopen(urllib.request.Request("https://www.wikidata.org/w/api.php?" + q, headers=UA), timeout=60) as r:
            ents = json.load(r).get("entities", {})
        for e in ents.values():
            if "missing" in e:
                continue
            c = e.get("claims", {})

            def fecha(p):
                for x in c.get(p, []):
                    v = x["mainsnak"].get("datavalue", {}).get("value", {})
                    if v.get("precision", 0) >= 11:
                        y, m, d = v["time"].lstrip("+-").split("T")[0].split("-")
                        return (-int(y) if v["time"].startswith("-") else int(y), int(m), int(d))
                return None

            tit = e.get("sitelinks", {}).get("enwiki", {}).get("title")
            res[tit] = {"fama": sum(1 for k in e.get("sitelinks", {}) if k.endswith("wiki") and k not in ("commonswiki", "specieswiki")),
                        "ciudadania": {x["mainsnak"]["datavalue"]["value"]["id"] for x in c.get("P27", []) if x["mainsnak"].get("datavalue")},
                        "nace": fecha("P569"), "muere": fecha("P570")}
        time.sleep(0.5)
    return res


def efemeride(w, hoy):
    """(puntos, texto) si nació o murió en los próximos DIAS días."""
    mejor = (0, "")
    for tipo, f in (("nació", w.get("nace")), ("murió", w.get("muere"))):
        if not f or f[0] < 1:
            continue
        for k in range(1, DIAS + 2):  # el lote sale desde el día siguiente (Make: 02:00; publicaciones 20:00 y 02:00)
            dia = hoy + dt.timedelta(days=k)
            if (dia.month, dia.day) == (f[1], f[2]):
                n = dia.year - f[0]
                redondo = n % 50 == 0 or (n % 25 == 0 and n <= 300)
                p = 10 + (5 if redondo else 0)
                if p > mejor[0]:
                    mejor = (p, f"{tipo} un {dia:%d/%m}, hace {n} años{' (redondo)' if redondo else ''}")
    return mejor


def main():
    hoy = dt.date.today()
    citas = todas(T_CITAS, ["Cita", "Autor", "Wikipedia", "Orden", "Usada"])
    libres = [c for c in citas if not c["fields"].get("Usada") and c["fields"].get("Cita")]
    print(f"{len(citas)} citas; sin usar: {len(libres)}", flush=True)
    # autores publicados en las últimas 2 semanas (no se repiten tan pronto)
    hace = (hoy - dt.timedelta(days=14)).isoformat()
    recientes = {norm(p["fields"].get("Autor")) for p in
                 todas(T_PUB, ["Autor"], f"IS_AFTER({{Fecha de Creación}}, '{hace}')")}
    wd = wikidata(sorted({c["fields"]["Wikipedia"] for c in libres if c["fields"].get("Wikipedia")}))
    puntuadas = []
    for c in libres:
        f = c["fields"]
        w = wd.get(f.get("Wikipedia"), {})
        p_efe, txt_efe = efemeride(w, hoy)
        fama = math.log2(1 + w.get("fama", 0)) / 2.5          # ~0 a 3,2
        ciud = w.get("ciudadania", set())
        origen = 2.0 if ciud & LATAM else 0.7 if ciud & ESPANA else 0.0
        tema = 1.0 if TEMAS_BUENOS.search(f.get("Cita", "")) else 0.0
        reciente = -4.0 if norm(f.get("Autor")) in recientes else 0.0
        perfil = 3.0 if RELIGIOSOS.search(f.get("Autor", "")) else 1.5 if SABIOS.search(f.get("Autor", "")) else 0.0
        puntos = p_efe + fama + origen + tema + reciente + perfil
        motivo = ", ".join(x for x in (txt_efe, "América Latina" if origen == 2 else "España" if origen else "",
                                       "fe/consuelo/sabiduría" if tema else "",
                                       "autor religioso" if perfil == 3 else "sabiduría para la vida" if perfil else "",
                                       "publicado hace poco" if reciente else "") if x)
        puntuadas.append((puntos, c, motivo))
    puntuadas.sort(key=lambda x: -x[0])
    # variedad: en cada lote de 7, como mucho una cita por autor
    orden, pendientes = [], list(puntuadas)
    while pendientes:
        lote, autores, resto = [], set(), []
        for x in pendientes:
            a = norm(x[1]["fields"].get("Autor"))
            if len(lote) < LOTE and a not in autores:
                lote.append(x)
                autores.add(a)
            else:
                resto.append(x)
        orden += lote
        pendientes = resto
    cambios = []
    for k, (puntos, c, motivo) in enumerate(orden, start=1):
        if k <= 30:
            print(f"{k:3}. {puntos:5.1f}  {c['fields'].get('Autor')}: «{c['fields']['Cita'][:60]}» {('· ' + motivo) if motivo else ''}", flush=True)
        if c["fields"].get("Orden") != k:
            cambios.append({"id": c["id"], "fields": {"Orden": k}})
    print(f"Citas con «Orden» nuevo: {len(cambios)}{' (solo mirar: no se escribe)' if SOLO_MIRAR else ''}", flush=True)
    if not SOLO_MIRAR:
        for i in range(0, len(cambios), 10):
            airtable("PATCH", T_CITAS, {"records": cambios[i:i + 10]})
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as out:
            out.write("## Próximas citas (orden para Make)\n\n| # | Autor | Motivo |\n|---|---|---|\n" +
                      "".join(f"| {k} | {c['fields'].get('Autor')} | {m or '—'} |\n" for k, (_, c, m) in enumerate(orden[:21], 1)))


if __name__ == "__main__":
    main()
