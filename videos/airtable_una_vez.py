"""Cambio puntual en Airtable desde GitHub (21 nov 2026), para quitar de la cola una publicación ya subida a mano.

Lee .github/airtable_una_vez.txt:
  ACCION=leer       → solo lee: la publicación (por AUTOR) y los valores que tiene el campo Estado en la tabla.
  ACCION=escribir   → pone CAMPO=VALOR en esa publicación (y nada más). Solo si la búsqueda da UNA publicación.
Variables: AIRTABLE_TOKEN (secret)."""
import collections, json, os, sys, urllib.parse, urllib.request

BASE, T_PUB = "appeuC0uIAlqqp1h9", "tbl7ynqI9bJrWtR0m"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(metodo, ruta, datos=None):
    req = urllib.request.Request(f"https://api.airtable.com/v0/{ruta}", method=metodo,
                                 data=json.dumps(datos).encode() if datos is not None else None,
                                 headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}",
                                          "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def todas():
    regs, offset = [], None
    while True:
        q = urllib.parse.urlencode([("pageSize", "100")] + ([("offset", offset)] if offset else []))
        d = api("GET", f"{BASE}/{T_PUB}?{q}")
        regs += d["records"]
        offset = d.get("offset")
        if not offset:
            return regs


def main():
    a = {}
    for l in open(os.path.join(RAIZ, ".github", "airtable_una_vez.txt"), encoding="utf-8"):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            a[k.strip().upper()] = v.strip()
    regs = todas()
    estados = collections.Counter(str(r["fields"].get("Estado")) for r in regs)
    suyas = [r for r in regs if r["fields"].get("Autor", "").strip() == a["AUTOR"] and r["fields"].get("Estado") != "Publicado"]
    lineas = [f"Valores de «Estado» en la tabla: {dict(estados)}", f"Publicaciones sin publicar de {a['AUTOR']}: {len(suyas)}"]
    for r in suyas:
        f = {k: (v if not isinstance(v, list) else f"[{len(v)} adjunto(s)]") for k, v in r["fields"].items()
             if k not in ("Caption",)}
        lineas.append(f"{r['id']}: " + json.dumps(f, ensure_ascii=False)[:1500])
    if a.get("ACCION") == "hashtags_quiz":
        # 24 nov 2026: los quiz ya hechos llevaban 8 hashtags; se dejan los 5 de ahora (#quiz, #frasescelebres y los
        # 3 autores). Solo toca la última línea del Caption de los no publicados con vídeo «-quiz».
        sobran = {"#frases", "#culturageneral", "#reflexiones"}
        cambios = []
        for r in regs:
            f = r["fields"]
            if f.get("Estado") == "Publicado" or not any("-quiz.mp4" in (v.get("filename") or "") for v in f.get("Vídeo") or []):
                continue
            cap = f.get("Caption") or ""
            *resto, ultima = cap.split("\n")
            tags = ultima.split()
            if not tags or not all(t.startswith("#") for t in tags) or not (set(tags) & sobran):
                continue
            nueva = " ".join(t for t in tags if t not in sobran)
            cambios.append({"id": r["id"], "fields": {"Caption": "\n".join(resto + [nueva])}})
            lineas.append(f"{r['id']} ({f.get('Autor')}): {ultima}  →  {nueva}")
        for i in range(0, len(cambios), 10):
            api("PATCH", f"{BASE}/{T_PUB}", {"records": cambios[i:i + 10]})
        lineas.append(f"ESCRITO: hashtags corregidos en {len(cambios)} publicación(es)")
    if a.get("ACCION") == "escribir":
        if len(suyas) != 1:
            sys.exit(f"La búsqueda da {len(suyas)} publicaciones: no se escribe nada")
        api("PATCH", f"{BASE}/{T_PUB}", {"records": [{"id": suyas[0]["id"], "fields": {a["CAMPO"]: a["VALOR"]}}]})
        lineas.append(f"ESCRITO: {suyas[0]['id']} · {a['CAMPO']} = {a['VALOR']}")
    texto = "\n".join(lineas)
    print(texto)
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        open(resumen, "a").write("### Airtable (una vez)\n\n```\n" + texto + "\n```\n")


if __name__ == "__main__":
    main()
