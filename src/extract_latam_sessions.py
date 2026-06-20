"""
Extracción CRUDA de conexiones a sesiones "Sesión Grupal Latam 0N" (ene-jun 2026).

Vuelca UNA fila por conexión de participante (no agrega todavía), con la hora
de ingreso, para poder filtrar por horario y deduplicar personas en
post-proceso SIN tener que re-descargar (~50 min) cada vez que ajustamos un
criterio.

Salida cruda: latam_conexiones_raw.csv
    grupo, meeting_uuid, topic, start_utc, persona, pais,
    join_utc, leave_utc, dur_seg

`persona` (nombre/email) se usa solo para deduplicar en el análisis; los CSV
analíticos finales NO incluyen detalle de personas.

El análisis (conteo por sesión/país, filtro de horarios en hora de Chile,
heatmap) vive en analyze_latam_sessions.py y se alimenta de este CSV crudo.
"""

import csv
import re
import time
from datetime import date, datetime, timedelta

from extract_zoom_participants import (
    get_access_token,
    ZoomClient,
    get_participants,
    utc_iso_to_chile_date,
)
from paths import DATA_DIR

# Ventanas mensuales (<=30 días, límite del endpoint metrics/meetings).
WINDOWS = [
    ("2026-01-01", "2026-01-31"),
    ("2026-02-01", "2026-02-28"),
    ("2026-03-01", "2026-03-31"),
    ("2026-04-01", "2026-04-30"),
    ("2026-05-01", "2026-05-31"),
    ("2026-06-01", date.today().isoformat()),
]

TOPIC_RE = re.compile(r"Sesi[oó]n Grupal Latam\s*0?([1-9])", re.IGNORECASE)
COUNTRY_RE = re.compile(r"\(([A-Z]{2})\)")

OUTPUT_CSV = str(DATA_DIR / "latam_conexiones_raw.csv")


def country_of(location: str) -> str:
    if not location:
        return "??"
    m = COUNTRY_RE.search(str(location))
    return m.group(1) if m else "??"


def person_key(p: dict) -> str:
    return (p.get("email") or p.get("user_name") or p.get("id") or "").strip()


def list_latam_meetings(client: ZoomClient) -> list:
    """Lista reuniones Latam 0N en ene-jun, deduplicadas por uuid (filtro día Chile)."""
    seen = set()
    meetings = []
    for fr, to in WINDOWS:
        utc_to = (date.fromisoformat(to) + timedelta(days=1)).isoformat()
        raw = []
        for page in client.paginate(
            "/metrics/meetings", params={"from": fr, "to": utc_to, "type": "past"}
        ):
            raw.extend(page.get("meetings", []))
        added = 0
        for m in raw:
            uuid = m.get("uuid")
            if not uuid or uuid in seen:
                continue
            mt = TOPIC_RE.search(m.get("topic") or "")
            if not mt:
                continue
            d = utc_iso_to_chile_date(m.get("start_time"))
            if not d or not (fr <= d <= to):
                continue
            seen.add(uuid)
            m["_grupo"] = f"Latam 0{mt.group(1)}"
            meetings.append(m)
            added += 1
        print(f"  {fr}..{to}: {added} reuniones Latam (acum {len(meetings)})")
    return meetings


def run():
    token = get_access_token()
    client = ZoomClient(token)

    print("1. Listando sesiones Latam 0N (ene-jun)...")
    meetings = list_latam_meetings(client)
    print(f"   Total: {len(meetings)} reuniones\n")

    print(f"2. Volcando conexiones crudas → {OUTPUT_CSV}")
    n_rows = 0
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["grupo", "meeting_uuid", "topic", "start_utc", "persona",
             "pais", "join_utc", "leave_utc", "dur_seg"]
        )
        for i, m in enumerate(meetings, 1):
            uuid = m["uuid"]
            grupo = m["_grupo"]
            topic = m.get("topic", "")
            start = m.get("start_time", "")
            try:
                parts = get_participants(client, uuid)
            except Exception as e:
                print(f"   [{i}/{len(meetings)}] {grupo} {start} ⚠ {e}")
                continue

            for p in parts:
                writer.writerow([
                    grupo, uuid, topic, start,
                    person_key(p), country_of(p.get("location")),
                    p.get("join_time", ""), p.get("leave_time", ""),
                    p.get("duration", ""),
                ])
                n_rows += 1
            fh.flush()

            if i % 50 == 0:
                print(f"   [{i}/{len(meetings)}] procesadas, {n_rows} conexiones")
            time.sleep(1.0)

    print(f"\n✓ Exportado: {OUTPUT_CSV}  ({n_rows} conexiones)")


if __name__ == "__main__":
    run()
