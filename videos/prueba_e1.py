"""Prueba de la fase E1 (subtítulos siempre legibles), 29 oct 2026. NO publica ni cambia Airtable (solo lee).

Coge publicaciones sin publicar que ya tienen vídeo (por defecto las 4 más antiguas, o las de los autores de
AUTORES, separados por comas) y monta cada una dos veces: como ahora («antes») y con E1 («e1»). La voz sale de la
caché (no gasta audios de Gemini si el vídeo ya se hizo con la voz nueva). Deja en salida_e1/ los vídeos, una hoja
de fotogramas por publicación (arriba antes, abajo E1) e informe.txt."""
import json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generar as G

OUT = "salida_e1"
N = int(os.environ.get("N") or 4)
AUTORES = [a.strip().lower() for a in (os.environ.get("AUTORES") or "").split(",") if a.strip()]


def hoja(antes, e1, dur, destino):
    """3 momentos (gancho, cita, autor): arriba antes, abajo E1."""
    filas = []
    for i, v in enumerate((antes, e1)):
        png = destino + f".{i}.png"
        t = [0.6, dur * 0.45, dur - 1.3]
        sel = "+".join(f"eq(n\\,{int(x * 30)})" for x in t)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", v, "-vf", f"select='{sel}',scale=360:-1,tile=3x1",
                        "-frames:v", "1", png], check=True)
        filas.append(png)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", filas[0], "-i", filas[1], "-filter_complex", "vstack",
                    "-q:v", "3", destino], check=True)
    for f in filas:
        os.remove(f)


def main():
    os.makedirs(OUT, exist_ok=True)
    regs = G.listar(G.T_PUB, ["Frase", "Autor", G.CAMPO_CREDITO, "Estado", G.CAMPO_VIDEO, G.CAMPO_QUIEN],
                    formula="{Estado}!='Publicado'", orden="Fecha de Creación")
    pubs = [(r["id"], r["fields"]) for r in regs if r["fields"].get(G.CAMPO_VIDEO) and r["fields"].get("Frase")]
    if AUTORES:
        pubs = [p for p in pubs if any(a in (p[1].get("Autor") or "").lower() for a in AUTORES)]
    pubs = pubs[:N]
    citas = G.listar(G.T_CITAS, ["Cita", "Autor", "Wikipedia", "Fuente", "Foto manual"])
    informe = []
    for rec_id, pub in pubs:
        autor = pub.get("Autor", "?")
        try:
            cita = G.buscar_cita(pub, citas)
            if cita is None:
                raise RuntimeError("no encuentro su cita en la tabla Citas")
            vids = {}
            for modo in ("antes", "e1"):
                os.environ["SUBS"] = "e1" if modo == "e1" else ""
                with tempfile.TemporaryDirectory() as tmp:
                    estado, info, _ = G.hacer_video(rec_id, pub, cita, tmp)  # los cambios para Airtable se ignoran
                    if estado != "ok":
                        raise RuntimeError(info)
                    dest = os.path.join(OUT, f"{G.slug(autor)}_{modo}.mp4")
                    shutil.move(info["salida"], dest)
                    vids[modo] = (dest, info)
            hoja(vids["antes"][0], vids["e1"][0], vids["e1"][1]["duracion"], os.path.join(OUT, f"{G.slug(autor)}_hoja.jpg"))
            linea = f"{autor}: {vids['e1'][1]['duracion']} s · voz {vids['e1'][1]['voz']} · E1 {json.dumps(vids['e1'][1].get('e1'))}"
        except Exception as e:
            linea = f"{autor}: ⚠️ {str(e)[:300]}"
        print(linea, flush=True)
        informe.append(linea)
    os.environ["SUBS"] = ""
    open(os.path.join(OUT, "informe.txt"), "w").write("\n".join(informe) + "\n")
    if not any("⚠️" not in l for l in informe):
        sys.exit("No se pudo montar ninguna prueba")


if __name__ == "__main__":
    main()
