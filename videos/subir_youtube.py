"""Subida directa de los Shorts a YouTube con su API (24 nov 2026), sin pasar por Buffer.

Por qué: Buffer (plan gratis) solo deja 2 Shorts de YouTube al día y a veces falla («daily posting limit»), y
la API deja elegir la hora exacta. Instagram y TikTok siguen igual (Make → Buffer).

Qué hace (cada hora, workflow «Subir Shorts a YouTube»):
- Busca en Airtable las publicaciones «Publicado» con vídeo del formato quiz y sin nada en el campo «YouTube».
- Si Buffer ya tiene su Short de YouTube (programado o enviado), no la sube: apunta «vía Buffer» y sigue.
  Así no hay duplicados mientras Make siga mandando YouTube a Buffer.
- Si el canal ya tiene un vídeo con el mismo título (p. ej. subido a mano), apunta ese enlace y no sube nada.
- Si no, lo sube en privado con hora de publicación (publishAt) en el siguiente hueco libre de HORAS (Madrid),
  «no creado para niños», con el título y la descripción de Airtable, y apunta en «YouTube»:
    https://youtu.be/<id> · sale 25/11 20:00
Cupo: cada subida gasta ~1.600 unidades de las 10.000 diarias; como mucho MAXIMO por ejecución.
Secrets: AIRTABLE_TOKEN, BUFFER_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Variables: SOLO_MIRAR=1 (no sube ni escribe nada; solo dice qué haría)."""
import json, os, re, urllib.parse
from datetime import datetime, timedelta, timezone

import requests

from comprobar import CANAL, MADRID, T_PUB, BASE, airtable, clase, letras, norm, posts_buffer

CAMPO = "YouTube"
HORAS = [(20, 0), (2, 0)]   # horas de Madrid (el público está en América: picos 19-23 h y 1-3 h de Madrid)
MAXIMO = int(os.environ.get("MAXIMO") or 4)
SOLO_MIRAR = os.environ.get("SOLO_MIRAR") == "1"
YT = "https://www.googleapis.com/youtube/v3"
CATEGORIA = "27"  # Educación


def asegurar_campo():
    """El campo «YouTube» (texto de una línea) tiene que existir en Publicaciones: el token no puede crearlo.
    Sin él no se sube nada (sin dónde apuntarlo, se podría subir dos veces)."""
    r = requests.get(f"https://api.airtable.com/v0/{BASE}/{T_PUB}", timeout=60,
                     headers={"Authorization": f"Bearer {os.environ['AIRTABLE_TOKEN']}"},
                     params={"maxRecords": 1, "fields[]": CAMPO})
    if r.status_code == 422:
        print(f"Falta el campo «{CAMPO}» en Publicaciones (texto de una línea): créalo en Airtable y esto "
              "empezará a funcionar solo en la siguiente hora. Hasta entonces no se sube nada.")
        raise SystemExit(0)
    r.raise_for_status()


def publicaciones():
    out, offset = [], None
    formula = "{Estado}='Publicado'"
    while True:
        q = [("pageSize", "100"), ("filterByFormula", formula)] + \
            [("fields[]", c) for c in ("Frase", "Autor", "Caption", "Vídeo", "Título vídeo", CAMPO)]
        if offset:
            q.append(("offset", offset))
        d = airtable("GET", f"{T_PUB}?{urllib.parse.urlencode(q)}")
        out += d["records"]
        offset = d.get("offset")
        if not offset:
            return out


def guardar(rec_id, texto):
    if not SOLO_MIRAR:
        airtable("PATCH", T_PUB, {"records": [{"id": rec_id, "fields": {CAMPO: texto[:250]}}]})


def es_quiz(f):
    return any("-quiz.mp4" in (a.get("filename") or "") for a in f.get("Vídeo") or [])


def en_buffer(f, posts):
    cap, frase = norm(f.get("Caption")), letras(f.get("Frase"))[:50]
    # solo cuenta si Buffer lo ha enviado o lo va a enviar; si falló («daily posting limit»), se sube por la API
    return any(clase(p) == "YouTube" and p.get("status") in ("sent", "sending", "scheduled")
               and (norm(p.get("text")) == cap or (frase and frase in letras(p.get("text")))) for p in posts)


def huecos_ocupados(pubs):
    """Horas (Madrid) ya usadas por Shorts subidos con este script: «· sale 25/11 20:00»."""
    hoy = datetime.now(MADRID)
    out = set()
    for p in pubs:
        m = re.search(r"sale (\d\d)/(\d\d) (\d\d):(\d\d)", p["fields"].get(CAMPO) or "")
        if m:
            d, mes, h, mi = map(int, m.groups())
            anio = hoy.year + (1 if mes < hoy.month - 6 else 0)
            out.add(datetime(anio, mes, d, h, mi, tzinfo=MADRID))
    return out


def siguiente_hueco(ocupados):
    t = datetime.now(MADRID) + timedelta(minutes=40)
    dia = t.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(60):
        for h, mi in sorted(HORAS):
            c = dia.replace(hour=h, minute=mi)
            if c >= t and c not in ocupados:
                return c
        dia += timedelta(days=1)
    raise RuntimeError("no hay huecos libres en 30 días")


# ---------------------------------------------------------------- YouTube
def token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


def subidos(tok):
    """{título: id} de los últimos 50 vídeos del canal (incluidos los privados y programados)."""
    h = {"Authorization": f"Bearer {tok}"}
    canal = requests.get(f"{YT}/channels", headers=h, params={"part": "contentDetails,snippet", "mine": "true"}, timeout=60).json()
    print("Canal:", canal["items"][0]["snippet"]["title"])
    lista = canal["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = requests.get(f"{YT}/playlistItems", headers=h, timeout=60,
                         params={"part": "snippet,contentDetails", "playlistId": lista, "maxResults": 50}).json().get("items", [])
    return {norm(i["snippet"]["title"]): i["contentDetails"]["videoId"] for i in items}


def subir(tok, f, cuando):
    url = f["Vídeo"][0]["url"]
    datos = requests.get(url, timeout=300).content
    publish = cuando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    cuerpo = {"snippet": {"title": f["Título vídeo"][:100],
                          "description": (f.get("Caption") or "").replace("<", "‹").replace(">", "›")[:4900],
                          "categoryId": CATEGORIA, "defaultLanguage": "es", "defaultAudioLanguage": "es"},
              "status": {"privacyStatus": "private", "publishAt": publish, "selfDeclaredMadeForKids": False,
                         "embeddable": True, "license": "youtube"}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos", timeout=120,
                      params={"uploadType": "resumable", "part": "snippet,status", "notifySubscribers": "true"},
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(datos))},
                      data=json.dumps(cuerpo))
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    r = requests.put(r.headers["Location"], data=datos, timeout=900, headers={"Authorization": f"Bearer {tok}"})
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    vid = r.json()["id"]
    st = requests.get(f"{YT}/videos", headers={"Authorization": f"Bearer {tok}"}, params={"part": "status", "id": vid},
                      timeout=60).json()["items"][0]["status"]
    if st.get("privacyStatus") != "private" or not st.get("publishAt"):
        print(f"  [aviso] estado raro tras subir: {st}", flush=True)
    return vid


def main():
    asegurar_campo()
    pubs = publicaciones()
    candidatas = [p for p in pubs if es_quiz(p["fields"]) and not p["fields"].get(CAMPO) and p["fields"].get("Título vídeo")]
    print(f"Publicaciones «Publicado» con quiz y sin «{CAMPO}»: {len(candidatas)}")
    if not candidatas:
        return
    desde = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = [p for p in posts_buffer(desde) if CANAL.get(p.get("channelId")) == "youtube"]
    tok = token()
    canal = subidos(tok)
    ocupados = huecos_ocupados(pubs)
    filas, hechas = [], 0
    for p in candidatas:
        f, autor = p["fields"], p["fields"].get("Autor", "?")
        if en_buffer(f, posts):
            txt = "vía Buffer"
        elif norm(f["Título vídeo"]) in canal:
            txt = f"https://youtu.be/{canal[norm(f['Título vídeo'])]} · ya estaba en el canal"
        elif hechas >= MAXIMO:
            filas.append(f"| {autor} | se sube en la siguiente ejecución (máximo {MAXIMO}) |")
            continue
        else:
            cuando = siguiente_hueco(ocupados)
            if SOLO_MIRAR:
                txt = f"(solo mirar) se subiría para el {cuando:%d/%m %H:%M}"
            else:
                try:
                    vid = subir(tok, f, cuando)
                    txt = f"https://youtu.be/{vid} · sale {cuando:%d/%m %H:%M}"
                except Exception as e:
                    filas.append(f"| {autor} | ⚠️ {str(e)[:200]} |")
                    print(f"- {autor}: ⚠️ {e}", flush=True)
                    continue
            ocupados.add(cuando)
            hechas += 1
        if not txt.startswith("(solo mirar)"):
            guardar(p["id"], txt)  # en el momento: nunca se sube dos veces
        print(f"- {autor}: {txt}", flush=True)
        filas.append(f"| {autor} | {txt} |")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as out:
            out.write("## Shorts subidos a YouTube por la API\n\n| Autor | Resultado |\n|---|---|\n" + "\n".join(filas) + "\n")


if __name__ == "__main__":
    main()
