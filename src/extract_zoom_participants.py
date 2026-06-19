"""
Extracción de participantes con ubicación desde Zoom Dashboard API.

Filtra participantes conectados desde Chile (CL) en un rango de fechas.

Requisitos:
- Plan Zoom Business o superior (ya lo tienes)
- Server-to-Server OAuth app en Zoom Marketplace con scopes granulares:
    * dashboard:read:list_meetings:admin
    * dashboard:read:list_meeting_participants:admin
  (Los scopes clásicos `dashboard_meetings:read:admin` / `dashboard:read:admin`
   ya no aplican en apps nuevas; Zoom migró a scopes granulares.)
- Credenciales: ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET

Instalación:
    pip install requests python-dotenv pandas openpyxl

Uso:
    1. Crea un archivo .env en la misma carpeta con:
        ZOOM_ACCOUNT_ID=xxxxx
        ZOOM_CLIENT_ID=xxxxx
        ZOOM_CLIENT_SECRET=xxxxx
    2. Ajusta FROM_DATE, TO_DATE y FILTRO_PAIS abajo
    3. python extract_zoom_participants.py
"""

import os
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

from paths import OUTPUT_DIR, ENV_FILE

load_dotenv(ENV_FILE)

# ========== CONFIGURACIÓN ==========
ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

# Zoom devuelve timestamps en UTC. Convertimos a hora de Chile (maneja DST:
# UTC-4 en invierno, UTC-3 en verano) para que la columna `dia` y el rango
# FROM_DATE/TO_DATE reflejen realmente la zona del participante.
CHILE_TZ = ZoneInfo("America/Santiago")

# Fechas interpretadas en hora de Chile (no UTC). El script compensa al
# consultar Zoom para que una sesión a las 22:00 del 31-may Chile (que en
# UTC ya es 1-jun) quede asignada al día Chile correcto.
FROM_DATE = "2026-06-01"
TO_DATE = datetime.now(CHILE_TZ).date().isoformat()  # hasta hoy en hora Chile

# El campo location de Zoom devuelve nombre de país completo ("Chile") y
# a veces código ISO. Filtramos ambos por seguridad.
FILTRO_PAIS = ["Chile", "CL"]

# Si se define, solo se procesan reuniones cuyo topic contenga alguno de
# estos substrings (case-insensitive). Útil para acotar debug o análisis.
# Lista vacía = procesar todas.
FILTRO_TOPIC = ["Sesión Grupal Latam 06"]

def utc_iso_to_chile_date(iso_str: str) -> str:
    """Convierte un timestamp ISO UTC (ej. '2026-05-19T02:55:02Z') al día
    correspondiente en America/Santiago en formato YYYY-MM-DD."""
    if not iso_str:
        return None
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.astimezone(CHILE_TZ).date().isoformat()


# ========== AUTENTICACIÓN ==========
def get_access_token() -> str:
    """Obtiene un access token vía Server-to-Server OAuth."""
    url = "https://zoom.us/oauth/token"
    params = {"grant_type": "account_credentials", "account_id": ACCOUNT_ID}
    resp = requests.post(url, params=params, auth=(CLIENT_ID, CLIENT_SECRET))
    resp.raise_for_status()
    return resp.json()["access_token"]


# ========== CLIENTE HTTP CON MANEJO DE RATE LIMIT ==========
class ZoomClient:
    BASE = "https://api.zoom.us/v2"

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self._refreshes = 0

    def _refresh_token(self):
        """Renueva el token S2S (expira a los 60 min) y actualiza la sesión."""
        self._refreshes += 1
        token = get_access_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"  Token renovado (#{self._refreshes}).")

    def get(self, path: str, params: dict = None, retries: int = 5) -> dict:
        url = f"{self.BASE}{path}"
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as e:
                wait = min(2 ** attempt, 30)
                print(f"  Red inestable ({type(e).__name__}). Reintento en {wait}s...")
                time.sleep(wait)
                continue
            # Token expirado → renovar y reintentar
            if resp.status_code == 401:
                self._refresh_token()
                continue
            # Rate limit → esperar y reintentar
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                print(f"  Rate limit. Esperando {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Falló después de {retries} intentos: {path}")

    def paginate(self, path: str, params: dict = None, data_key: str = None):
        """Itera por todas las páginas de un endpoint."""
        params = dict(params or {})
        params.setdefault("page_size", 300)
        while True:
            data = self.get(path, params=params)
            yield data
            token = data.get("next_page_token")
            if not token:
                break
            params["next_page_token"] = token


# ========== EXTRACCIÓN ==========
def list_past_meetings(client: ZoomClient, from_date: str, to_date: str) -> list:
    """Lista reuniones pasadas en el rango Chile-local [from_date, to_date].

    Zoom filtra por UTC. Para no perder sesiones de fin de día Chile que en
    UTC caen al día siguiente, consultamos UTC = [from_date, to_date + 1d]
    y luego filtramos en post por la fecha Chile derivada de `start_time`.
    """
    utc_to = (date.fromisoformat(to_date) + timedelta(days=1)).isoformat()
    raw = []
    for page in client.paginate(
        "/metrics/meetings",
        params={"from": from_date, "to": utc_to, "type": "past"},
    ):
        meetings = page.get("meetings", [])
        raw.extend(meetings)
        print(f"  Reuniones acumuladas (UTC): {len(raw)}")
    filtered = [
        m for m in raw
        if (d := utc_iso_to_chile_date(m.get("start_time")))
        and from_date <= d <= to_date
    ]
    print(f"  Tras filtro Chile [{from_date} .. {to_date}]: {len(filtered)}")
    return filtered


def get_participants(client: ZoomClient, meeting_uuid: str) -> list:
    """Participantes de una reunión pasada (incluye location)."""
    # Zoom: doble URL-encode SOLO si el UUID empieza con "/" o contiene "//".
    # Caso contrario, encoding simple. Hacerlo siempre rompe los UUIDs que
    # terminan en "==" (la mayoría), devolviendo 400.
    if meeting_uuid.startswith("/") or "//" in meeting_uuid:
        encoded = urllib.parse.quote(
            urllib.parse.quote(meeting_uuid, safe=""), safe=""
        )
    else:
        encoded = urllib.parse.quote(meeting_uuid, safe="")

    # type=past falla con 400 en reuniones de 1 solo usuario; ahí toca pastOne.
    # page_size máx documentado es 30 en este endpoint (no 300 como el listado).
    for meeting_type in ("past", "pastOne"):
        try:
            all_parts = []
            for page in client.paginate(
                f"/metrics/meetings/{encoded}/participants",
                params={
                    "type": meeting_type,
                    "include_fields": "registrant_id",
                    "page_size": 30,
                },
            ):
                all_parts.extend(page.get("participants", []))
            return all_parts
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 400 and meeting_type == "past":
                continue
            raise
    return []


def run():
    if not all([ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET]):
        raise SystemExit(
            "Falta configurar credenciales en .env "
            "(ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET)"
        )

    print(f"Periodo: {FROM_DATE} → {TO_DATE}")
    print(f"Filtro ubicación: {FILTRO_PAIS}\n")

    token = get_access_token()
    client = ZoomClient(token)

    print("1. Listando reuniones pasadas...")
    meetings = list_past_meetings(client, FROM_DATE, TO_DATE)
    print(f"   Total: {len(meetings)} reuniones")

    if FILTRO_TOPIC:
        patt = [t.lower() for t in FILTRO_TOPIC]
        meetings = [
            m for m in meetings
            if any(p in (m.get("topic") or "").lower() for p in patt)
        ]
        print(f"   Filtradas por topic {FILTRO_TOPIC}: {len(meetings)}")
    print()

    print("2. Descargando participantes de cada reunión...")
    rows = []
    for i, m in enumerate(meetings, 1):
        uuid = m["uuid"]
        topic = m.get("topic", "")
        start = m.get("start_time", "")
        print(f"   [{i}/{len(meetings)}] {topic} - {start}")
        try:
            parts = get_participants(client, uuid)
        except requests.HTTPError as e:
            body = ""
            if e.response is not None:
                try:
                    body = e.response.json()
                except Exception:
                    body = e.response.text[:300]
            print(f"     ⚠ Error: {e}")
            print(f"       Body: {body}")
            continue

        for p in parts:
            rows.append({
                "meeting_uuid": uuid,
                "meeting_id": m.get("id"),
                "topic": topic,
                "start_time": start,
                "dia": utc_iso_to_chile_date(start),
                "participant_id": p.get("id"),
                "user_id": p.get("user_id"),
                "name": p.get("user_name"),
                "email": p.get("email"),
                "location": p.get("location"),  # ← ciudad y país
                "ip_address": p.get("ip_address"),
                "network_type": p.get("network_type"),
                "device": p.get("device"),
                "connection_type": p.get("connection_type"),
                "join_time": p.get("join_time"),
                "leave_time": p.get("leave_time"),
                "duration_sec": p.get("duration"),
                "registrant_id": p.get("registrant_id"),
            })
        # Pequeña pausa para no saturar el rate limit (Heavy = 60 req/min)
        time.sleep(1.1)

    if not rows:
        print("No se obtuvieron participantes.")
        return

    df = pd.DataFrame(rows)
    print(f"\n3. Total registros de participación: {len(df)}")

    # Filtrar por Chile
    pattern = "|".join(FILTRO_PAIS)
    df_cl = df[df["location"].fillna("").str.contains(pattern, case=False, na=False)].copy()
    print(f"   Registros desde Chile: {len(df_cl)}")
    print(f"   Personas únicas desde Chile: "
          f"{df_cl['email'].fillna(df_cl['name']).nunique()}")

    # Exportar ambos: completo + solo CL
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_all = OUTPUT_DIR / f"zoom_participantes_{ts}.xlsx"
    out_cl = OUTPUT_DIR / f"zoom_participantes_CL_{ts}.xlsx"

    with pd.ExcelWriter(out_all, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Todos", index=False)
        df_cl.to_excel(w, sheet_name="Solo Chile", index=False)

    # Resumen por persona (solo CL)
    resumen_cl = (df_cl.groupby(
        df_cl["email"].fillna(df_cl["name"]), dropna=False
    ).agg(
        nombre=("name", "first"),
        correo=("email", "first"),
        ubicacion=("location", lambda s: ", ".join(sorted(set(s.dropna())))),
        reuniones=("meeting_uuid", "nunique"),
        dias_distintos=("dia", "nunique"),
        dias=("dia", lambda s: ", ".join(sorted(set(s.dropna())))),
        total_min=("duration_sec", lambda s: round(s.sum() / 60, 1)),
    ).reset_index(drop=True)
    .sort_values("reuniones", ascending=False))

    with pd.ExcelWriter(out_cl, engine="openpyxl") as w:
        df_cl.to_excel(w, sheet_name="Detalle CL", index=False)
        resumen_cl.to_excel(w, sheet_name="Por persona", index=False)

    print(f"\n✓ Exportado: {out_all}")
    print(f"✓ Exportado: {out_cl}")


if __name__ == "__main__":
    run()
