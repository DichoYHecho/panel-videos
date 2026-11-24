"""Estadísticas de los Shorts de YouTube (24 nov 2026), para decidir con datos y no a ojo.

Cada día guarda una foto de todos los vídeos del canal (visitas, «me gusta», comentarios) en datos/youtube.csv
(rama «datos» del repositorio) y escribe datos/informe.md:
- Formato quiz frente al clásico (visitas medianas a los 2 y 7 días de publicarse).
- Visitas por hora de publicación (Madrid) y por día de la semana.
- Los 10 Shorts con más visitas y los 10 con menos de las últimas 4 semanas.
Usa la API de datos de YouTube con la autorización que ya existe (youtube.force-ssl): ~10 unidades al día.
Uso: python estadisticas_youtube.py <carpeta de datos>"""
import csv, datetime as dt, os, re, statistics, sys
from collections import defaultdict
from zoneinfo import ZoneInfo

import requests

YT = "https://www.googleapis.com/youtube/v3"
MADRID = ZoneInfo("Europe/Madrid")
CAMPOS = ["fecha", "video", "titulo", "publicado", "formato", "duracion_s", "vistas", "megusta", "comentarios"]


def token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


def segundos(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def videos(tok):
    h = {"Authorization": f"Bearer {tok}"}
    canal = requests.get(f"{YT}/channels", headers=h, params={"part": "contentDetails", "mine": "true"}, timeout=60).json()
    lista = canal["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, pagina = [], None
    while True:
        d = requests.get(f"{YT}/playlistItems", headers=h, timeout=60, params={
            "part": "contentDetails", "playlistId": lista, "maxResults": 50, **({"pageToken": pagina} if pagina else {})}).json()
        ids += [i["contentDetails"]["videoId"] for i in d.get("items", [])]
        pagina = d.get("nextPageToken")
        if not pagina:
            break
    out = []
    for i in range(0, len(ids), 50):
        d = requests.get(f"{YT}/videos", headers=h, timeout=60, params={
            "part": "snippet,statistics,contentDetails,status", "id": ",".join(ids[i:i + 50])}).json()
        for v in d.get("items", []):
            if v["status"].get("privacyStatus") != "public":
                continue
            s, t = v["statistics"], v["snippet"]["title"]
            out.append({"video": v["id"], "titulo": t, "publicado": v["snippet"]["publishedAt"],
                        "formato": "quiz" if t.startswith("¿Frase de") else "clásico",
                        "duracion_s": segundos(v["contentDetails"].get("duration")),
                        "vistas": int(s.get("viewCount", 0)), "megusta": int(s.get("likeCount", 0)),
                        "comentarios": int(s.get("commentCount", 0))})
    return out


def mediana(xs):
    return int(statistics.median(xs)) if xs else 0


def informe(filas, hoy):
    """Markdown con las comparaciones. `filas` = todas las fotos diarias (de youtube.csv)."""
    por_video = defaultdict(list)
    for f in filas:
        por_video[f["video"]].append(f)
    ultimo = {v: max(fs, key=lambda f: f["fecha"]) for v, fs in por_video.items()}

    def vistas_a(v, dias):
        """Visitas en la foto más cercana a «dias» días después de publicarse (None si aún no hay)."""
        pub = dt.datetime.fromisoformat(ultimo[v]["publicado"].replace("Z", "+00:00")).date()
        fs = [f for f in por_video[v] if (dt.date.fromisoformat(f["fecha"]) - pub).days >= dias]
        return int(min(fs, key=lambda f: f["fecha"])["vistas"]) if fs else None

    lin = [f"# Estadísticas de YouTube · Dicho y Hecho ({hoy:%d/%m/%Y})", "",
           "Visitas medianas (la mitad de los Shorts tiene más y la otra mitad menos).", "",
           "## Formato quiz frente al clásico", "", "| Formato | Shorts | A los 2 días | A los 7 días | Total hoy |", "|---|---|---|---|---|"]
    for fmt in ("quiz", "clásico"):
        vs = [v for v, f in ultimo.items() if f["formato"] == fmt]
        d2 = [x for x in (vistas_a(v, 2) for v in vs) if x is not None]
        d7 = [x for x in (vistas_a(v, 7) for v in vs) if x is not None]
        lin.append(f"| {fmt} | {len(vs)} | {mediana(d2)} ({len(d2)}) | {mediana(d7)} ({len(d7)}) | {mediana([int(ultimo[v]['vistas']) for v in vs])} |")
    lin += ["", "Entre paréntesis, cuántos Shorts tienen ya esa edad (con pocos, el dato aún no es fiable).", "",
            "## Por hora de publicación (Madrid)", "", "| Hora | Shorts | Visitas medianas |", "|---|---|---|"]
    por_hora, por_dia = defaultdict(list), defaultdict(list)
    for f in ultimo.values():
        p = dt.datetime.fromisoformat(f["publicado"].replace("Z", "+00:00")).astimezone(MADRID)
        por_hora[p.hour].append(int(f["vistas"]))
        por_dia[p.weekday()].append(int(f["vistas"]))
    lin += [f"| {h:02d}:00 | {len(xs)} | {mediana(xs)} |" for h, xs in sorted(por_hora.items())]
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    lin += ["", "## Por día de la semana", "", "| Día | Shorts | Visitas medianas |", "|---|---|---|"]
    lin += [f"| {dias[d]} | {len(xs)} | {mediana(xs)} |" for d, xs in sorted(por_dia.items())]
    recientes = [f for f in ultimo.values()
                 if dt.datetime.fromisoformat(f["publicado"].replace("Z", "+00:00")).date() >= hoy - dt.timedelta(days=28)]
    recientes.sort(key=lambda f: -int(f["vistas"]))
    fila = lambda f: f"| {f['titulo'][:70]} | {f['formato']} | {f['vistas']} | {f['megusta']} | {f['comentarios']} |"
    cab = ["| Título | Formato | Visitas | Me gusta | Comentarios |", "|---|---|---|---|---|"]
    lin += ["", "## Los 10 con más visitas (últimas 4 semanas)", ""] + cab + [fila(f) for f in recientes[:10]]
    lin += ["", "## Los 10 con menos visitas (últimas 4 semanas)", ""] + cab + [fila(f) for f in recientes[-10:][::-1]]
    return "\n".join(lin) + "\n"


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "datos"
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "youtube.csv")
    hoy = dt.datetime.now(MADRID).date()
    filas = list(csv.DictReader(open(ruta, encoding="utf-8"))) if os.path.exists(ruta) else []
    filas = [f for f in filas if f["fecha"] != hoy.isoformat()]  # si se repite el mismo día, se sustituye
    nuevos = videos(token())
    filas += [{"fecha": hoy.isoformat(), **v} for v in nuevos]
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    texto = informe(filas, hoy)
    open(os.path.join(carpeta, "informe.md"), "w", encoding="utf-8").write(texto)
    print(f"{len(nuevos)} vídeos públicos; {len(filas)} filas en youtube.csv")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        open(resumen, "a", encoding="utf-8").write(texto)


if __name__ == "__main__":
    main()
