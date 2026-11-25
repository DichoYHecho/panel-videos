"""Subida directa de los Shorts a YouTube con su API (24 nov 2026), sin pasar por Buffer.

Por qué: Buffer (plan gratis) solo deja 2 Shorts de YouTube al día y a veces falla («daily posting limit»), y
la API deja elegir la hora exacta. Instagram y TikTok siguen igual (Make → Buffer).

Qué hace (cada hora, workflow «Subir Shorts a YouTube»):
- Busca en Airtable las publicaciones «Publicado» con vídeo del formato quiz cuyo «Comentario YouTube» no tiene
  aún enlace de YouTube. (Se usa ese campo porque el token de Airtable no puede crear campos nuevos: guarda el
  enlace del Short y, después, el del comentario; comentar_youtube.py nunca borra el enlace del vídeo.)
- Si Buffer ya tiene su Short de YouTube (programado o enviado), no la sube. Así no hay duplicados mientras Make
  siga mandando YouTube a Buffer. Si Buffer falló («daily posting limit»), sí la sube.
- Si el canal ya tiene un vídeo con el mismo título (p. ej. subido a mano), apunta ese enlace y no sube nada.
- Si no, lo sube en privado con hora de publicación (publishAt) en el siguiente hueco libre de HORAS (Madrid),
  «no creado para niños», con el título y la descripción de Airtable, y apunta en «Comentario YouTube»:
    📅 https://youtu.be/<id> · sale 25/11 20:00
Cupo: cada subida gasta ~1.600 unidades de las 10.000 diarias; como mucho MAXIMO por ejecución.
Secrets: AIRTABLE_TOKEN, BUFFER_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Variables: SOLO_MIRAR=1 (no sube ni escribe nada; solo dice qué haría)."""
import json, os, re, sys, urllib.parse
from datetime import datetime, timedelta, timezone

import requests

from comprobar import CANAL, MADRID, T_PUB, BASE, airtable, clase, letras, norm, posts_buffer

CAMPO = "Comentario YouTube"
HORAS = [(20, 0), (2, 0)]   # horas de Madrid (el público está en América: picos 19-23 h y 1-3 h de Madrid)
MAXIMO = int(os.environ.get("MAXIMO") or 4)
SOLO_MIRAR = os.environ.get("SOLO_MIRAR") == "1"
YT = "https://www.googleapis.com/youtube/v3"
CATEGORIA = "27"  # Educación


def tiene_video(texto):
    return bool(re.search(r"youtu\.be/|youtube\.com/(watch|shorts)", texto or ""))


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
    ultima = max((i["snippet"].get("publishedAt") or "" for i in items), default="")
    return {norm(i["snippet"]["title"]): i["contentDetails"]["videoId"] for i in items}, ultima


def subir(tok, f, cuando):
    url = f["Vídeo"][0]["url"]
    datos = requests.get(url, timeout=300).content
    # sin hora (None): público ya, a la vez que Instagram y TikTok; con hora: privado y programado
    estado = {"privacyStatus": "public"} if cuando is None else \
        {"privacyStatus": "private", "publishAt": cuando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    # voz sintética (Gemini): se declara, como hacía Buffer con isAiGenerated
    estado.update(selfDeclaredMadeForKids=False, embeddable=True, license="youtube", containsSyntheticMedia=True)
    cuerpo = {"snippet": {"title": f["Título vídeo"][:100],
                          "description": (f.get("Caption") or "").replace("<", "‹").replace(">", "›")[:4900],
                          "categoryId": CATEGORIA, "defaultLanguage": "es", "defaultAudioLanguage": "es"},
              "status": estado}
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
    esperado = "public" if cuando is None else "private"
    if st.get("privacyStatus") != esperado:  # p. ej. «private» bloqueado por ser una app sin verificar
        raise RuntimeError(f"subido como https://youtu.be/{vid} pero su estado es {st.get('privacyStatus')} "
                           f"y debía ser {esperado}: {st}")
    return vid


def main():
    pubs = publicaciones()
    # diagnóstico: las 6 últimas publicadas (para ver por qué una no se sube)
    for p in sorted(pubs, key=lambda p: p.get("createdTime", ""), reverse=True)[:6]:
        f = p["fields"]
        print(f"  · {f.get('Autor')}: quiz={es_quiz(f)} · vídeo={[a.get('filename') for a in f.get('Vídeo') or []]} "
              f"· título={'sí' if f.get('Título vídeo') else 'NO'} · {CAMPO}={(f.get(CAMPO) or '')[:60]!r}", flush=True)
    candidatas =[p for p in pubs if es_quiz(p["fields"]) and not tiene_video(p["fields"].get(CAMPO))
                  and p["fields"].get("Título vídeo")]
    print(f"Publicaciones «Publicado» con quiz y sin enlace de YouTube: {len(candidatas)}")
    # 25 nov 2026: nada puede fallar en silencio. Cualquier fallo deja la ejecución en rojo (GitHub avisa por correo).
    fallos = []
    tok = token()
    canal, ultima = subidos(tok)
    if not candidatas:
        vigilar(ultima, fallos)
        terminar(fallos, [])
        return
    desde = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = [p for p in posts_buffer(desde) if CANAL.get(p.get("channelId")) == "youtube"]
    ocupados = huecos_ocupados(pubs)
    filas, hechas = [], 0
    for p in candidatas:
        f, autor = p["fields"], p["fields"].get("Autor", "?")
        if en_buffer(f, posts):
            print(f"- {autor}: vía Buffer (no se toca)", flush=True)
            filas.append(f"| {autor} | vía Buffer (no se toca) |")
            continue  # no se escribe nada: comentar_youtube.py lo busca en Buffer como siempre
        elif norm(f["Título vídeo"]) in canal:
            txt = f"📅 https://youtu.be/{canal[norm(f['Título vídeo'])]} · ya estaba en el canal"
        elif hechas >= MAXIMO:
            filas.append(f"| {autor} | se sube en la siguiente ejecución (máximo {MAXIMO}) |")
            continue
        else:
            # 24 nov 2026: Make ya publica a las 20:00 y 02:00 (Madrid); YouTube sale enseguida, a la vez.
            # (Con PROGRAMAR=1 se vuelve a los huecos de HORAS.)
            cuando = siguiente_hueco(ocupados) if os.environ.get("PROGRAMAR") == "1" else None
            ahora = datetime.now(MADRID)
            if SOLO_MIRAR:
                txt = f"(solo mirar) se subiría {'para el ' + format(cuando, '%d/%m %H:%M') if cuando else 'ya, en público'}"
            else:
                try:
                    vid = subir(tok, f, cuando)
                    txt = f"📅 https://youtu.be/{vid} · sale {(cuando or ahora):%d/%m %H:%M}"
                except Exception as e:
                    filas.append(f"| {autor} | ⚠️ {str(e)[:200]} |")
                    print(f"- {autor}: ⚠️ {e}", flush=True)
                    fallos.append(f"{autor}: no se ha podido subir a YouTube ({str(e)[:200]})")
                    continue
            if cuando:
                ocupados.add(cuando)
            hechas += 1
        if not txt.startswith("(solo mirar)"):
            guardar(p["id"], txt)  # en el momento: nunca se sube dos veces
        print(f"- {autor}: {txt}", flush=True)
        filas.append(f"| {autor} | {txt} |")
        if txt.startswith("📅 https://youtu.be/") and "sale" in txt:
            ultima = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    vigilar(ultima, fallos)
    terminar(fallos, filas)


def vigilar(ultima, fallos):
    """Alarma si el canal lleva más de 26 h sin un Short nuevo (se publica 2 veces al día)."""
    if not ultima:
        return
    horas = (datetime.now(timezone.utc) - datetime.fromisoformat(ultima.replace("Z", "+00:00"))).total_seconds() / 3600
    print(f"Último vídeo subido al canal: hace {horas:.0f} h", flush=True)
    if horas > 26:
        fallos.append(f"YouTube lleva {horas:.0f} h sin ningún Short nuevo. Revisa qué ha publicado Make "
                      "(¿una publicación que ya estaba en YouTube?) y si hay Shorts en «Aprobado».")


def terminar(fallos, filas):
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a") as out:
            out.write("## Shorts subidos a YouTube por la API\n\n| Autor | Resultado |\n|---|---|\n" + "\n".join(filas) + "\n")
            if fallos:
                out.write("\n### ⚠️ Fallos\n\n" + "\n".join(f"- {x}" for x in fallos) + "\n")
    if fallos and not SOLO_MIRAR:
        sys.exit("FALLO: " + " | ".join(fallos))


if __name__ == "__main__":
    main()
