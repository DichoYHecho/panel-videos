"""Prueba del formato quiz con publicaciones reales (21 nov 2026). SOLO LEE Airtable: no escribe nada ni publica.

Monta N Shorts en formato quiz y los deja en salida_quiz/ (artefacto del run). En el resumen: opciones,
letra correcta, tema, país, duración, peso y el texto que iría en la descripción (fuente y créditos).
Qué publicaciones: las primeras N sin publicar, o las de los autores de AUTORES (separados por comas).
Ajustes en .github/prueba_quiz.txt (cambiarlo y subirlo lanza la prueba). Variables: AIRTABLE_TOKEN, GEMINI_API_KEY."""
import os, re, sys, tempfile, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generar as g
import quiz
import tts

SALIDA = "salida_quiz"


def ajustes():
    ruta = os.path.join(quiz.RAIZ, ".github", "prueba_quiz.txt")
    a = {"N": "3", "AUTORES": ""}
    for linea in open(ruta, encoding="utf-8"):
        if "=" in linea and not linea.startswith("#"):
            k, v = linea.split("=", 1)
            a[k.strip().upper()] = v.strip()
    return int(a["N"] or 3), [x.strip() for x in a["AUTORES"].split(",") if x.strip()]


def main():
    n, autores = ajustes()
    pubs = g.listar(g.T_PUB, ["Frase", "Autor", g.CAMPO_CREDITO, g.CAMPO_QUIEN, "Estado"], formula="{Estado}!='Publicado'",
                    orden="Fecha de Creación")
    citas = g.listar(g.T_CITAS, ["Cita", "Autor", "Wikipedia", "Fuente", "Foto manual"])
    banco = list(dict.fromkeys((c["fields"].get("Autor", "").strip(), c["fields"].get("Wikipedia")) for c in citas
                               if c["fields"].get("Wikipedia")))
    elegidas = [p for p in pubs if p["fields"].get("Frase") and (not autores or p["fields"].get("Autor", "").strip() in autores)]
    os.makedirs(SALIDA, exist_ok=True)
    filas, hechos = [], 0
    for p in elegidas:
        if hechos >= n:
            break
        f = p["fields"]
        autor, frase = f["Autor"].strip(), f["Frase"].strip()
        t0 = time.time()
        try:
            cita = g.buscar_cita(f, citas)
            if not cita:
                raise RuntimeError("no encuentro su cita en la tabla Citas")
            with tempfile.TemporaryDirectory() as tmp:
                if cita.get("Foto manual"):
                    foto = g.descargar(cita["Foto manual"][0]["url"], os.path.join(tmp, "foto.jpg"), ua=False)
                else:
                    url = g.foto_wikipedia(cita.get("Wikipedia"))
                    if not url:
                        raise RuntimeError("sin foto libre del autor")
                    foto = g.descargar(url, os.path.join(tmp, "foto.jpg"))
                quien_wd, mujer = g.wikidata(cita.get("Wikipedia"))
                quien = (f.get(g.CAMPO_QUIEN) or "").strip() or quien_wd
                props, desc = quiz.preparar(p["id"], frase, autor, cita, quien, mujer, foto, banco, tmp)
                nombre = f"{g.slug(autor)}-{p['id'][-6:]}-quiz.mp4"
                mb, dur = quiz.renderizar(props, os.path.abspath(os.path.join(SALIDA, nombre)), tmp, sum(p["id"].encode()) % 1000)
            credito = g.limpiar_credito((f.get(g.CAMPO_CREDITO) or "").strip())
            descripcion = (f"Fuente: {cita.get('Fuente', '')} · Foto: {credito} · Otras fotos: " + "; ".join(desc["creditos_opciones"]))
            filas.append(f"| {autor} | {' / '.join(desc['opciones'])} (correcta: {desc['letra_correcta']}) | {desc['tema']} | "
                         f"{(props.get('pais') or {}).get('nombre', '—')} | {dur} s | {mb} MB | {int(time.time() - t0)} s | {descripcion} |")
            print(f"[ok] {autor}: {dur} s, {mb} MB · {desc}", flush=True)
            hechos += 1
        except tts.SinVoz as e:
            filas.append(f"| {autor} | sin voz: {str(e)[:150]} | | | | | | |")
            print(f"[sin voz] {autor}: {e}", flush=True)
            break  # sin cupo de voz: no se sigue gastando
        except Exception as e:
            traceback.print_exc()
            filas.append(f"| {autor} | error: {str(e)[:200]} | | | | | | |")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as fh:
            fh.write("### Prueba del formato quiz (no se ha escrito nada en Airtable)\n\n"
                     "| Autor | Opciones | Tema | País | Duración | Peso | Montaje | Descripción |\n|---|---|---|---|---|---|---|---|\n"
                     + "\n".join(filas) + "\n")
    print("\n".join(filas))
    if not hechos:
        sys.exit("No se ha hecho ningún vídeo")


if __name__ == "__main__":
    main()
