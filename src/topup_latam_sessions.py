"""
Top-up: completa en latam_conexiones_raw.csv las reuniones que faltaron
(p. ej. por token expirado durante la extracción larga). Re-lista las
reuniones Latam, detecta los meeting_uuid ausentes en el CSV y solo descarga
esos, agregándolos (append). El cliente ahora renueva el token ante 401.
"""

import csv
import time

import pandas as pd

from extract_zoom_participants import get_access_token, ZoomClient, get_participants
from extract_latam_sessions import list_latam_meetings, country_of, person_key, OUTPUT_CSV


def run():
    existentes = set(pd.read_csv(OUTPUT_CSV, usecols=["meeting_uuid"])["meeting_uuid"])
    print(f"Reuniones ya presentes en CSV: {len(existentes)}")

    token = get_access_token()
    client = ZoomClient(token)
    meetings = list_latam_meetings(client)

    faltantes = [m for m in meetings if m["uuid"] not in existentes]
    print(f"Reuniones a completar: {len(faltantes)}")
    if not faltantes:
        print("Nada que completar.")
        return

    n_rows = 0
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for i, m in enumerate(faltantes, 1):
            uuid = m["uuid"]
            grupo = m["_grupo"]
            topic = m.get("topic", "")
            start = m.get("start_time", "")
            try:
                parts = get_participants(client, uuid)
            except Exception as e:
                print(f"   [{i}/{len(faltantes)}] {grupo} {start} ⚠ {e}")
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
            if i % 25 == 0:
                print(f"   [{i}/{len(faltantes)}] completadas, +{n_rows} conexiones")
            time.sleep(1.0)

    print(f"\n✓ Top-up listo: +{n_rows} conexiones agregadas a {OUTPUT_CSV}")


if __name__ == "__main__":
    run()
