"""
Generador de DATOS DE DEMOSTRACIÓN (sintéticos) para el showcase.

Produce data/latam_conexiones_raw.csv con el mismo esquema que generaría
extract_latam_sessions.py contra la Zoom Dashboard API, pero con datos
totalmente inventados (seed fijo). Permite correr el pipeline completo sin
credenciales ni datos reales.

Esquema: grupo, meeting_uuid, topic, start_utc, persona, pais, join_utc,
          leave_utc, dur_seg

Horarios en hora de Chile. Cada facilitador tiene un "efecto" propio
(FAC_MULT) que se refleja en la asistencia; como rotan mucho entre franjas
(ver horario_grids.py), el análisis puede normalizar por sesión y recuperar
ese desempeño propio.
"""

import csv
import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from paths import DATA_DIR
from horario_grids import GRIDS, FACILITADORES

CL = ZoneInfo("America/Santiago")
UTC = ZoneInfo("UTC")
SEED = 42

SLOTS = {"09:00": 6, "12:00": 7, "15:00": 8, "18:00": 11, "21:00": 9}  # base λ
DAY_FACTOR = {0: 1.0, 1: 1.05, 2: 1.12, 3: 0.98, 4: 0.85}             # Lun..Vie
GROUP_FACTOR = {1: 0.8, 2: 0.9, 3: 1.1, 4: 1.2, 5: 1.15, 6: 0.6}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes"]

# Efecto propio de cada facilitador (define el ranking "real" de desempeño).
_MULT = [1.45, 1.30, 1.25, 1.18, 1.12, 1.06, 1.00, 0.96,
         0.92, 0.88, 0.84, 0.80, 0.76, 0.72, 0.68, 0.62]
FAC_MULT = dict(zip(FACILITADORES, _MULT))

PAISES = {"MX": 30, "CO": 18, "AR": 17, "GT": 8, "SV": 7, "CL": 5, "US": 5,
          "ES": 3, "PE": 2, "BR": 2, "DO": 1, "CR": 1, "BE": 1}

NOMBRES = ["María", "José", "Carlos", "Ana", "Luis", "Sofía", "Diego", "Paula",
           "Andrés", "Valentina", "Jorge", "Rodrigo", "Felipe", "Daniela",
           "Ricardo", "Fernanda", "Pablo", "Antonia", "Tomás", "Javiera",
           "Mateo", "Isidora", "Nicolás", "Florencia", "Gabriel", "Catalina",
           "Constanza", "Renata", "Martín", "Emilia", "Vicente", "Trinidad"]
APELLIDOS = ["González", "Rodríguez", "Pérez", "Soto", "Muñoz", "Rojas",
             "Díaz", "Flores", "Castro", "Vargas", "Reyes", "Morales",
             "Herrera", "Silva", "Núñez", "Torres", "Ramírez", "Gómez",
             "Fuentes", "Espinoza", "Contreras", "Sepúlveda", "Araya", "León"]

_EFF = sorted(GRIDS)


def _weighted(rng, d):
    keys, w = zip(*d.items())
    return rng.choices(keys, weights=w, k=1)[0]


def facilitador(fecha, dia, slot):
    g = None
    for e in _EFF:
        if e <= fecha:
            g = GRIDS[e]
        else:
            break
    return (g.get(slot, {}).get(dia, "") or None) if g else None


def build_pool(rng, n=260):
    combos, pool = set(), []
    while len(pool) < n:
        nom = f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}"
        if nom in combos:
            continue
        combos.add(nom)
        pool.append((nom, _weighted(rng, PAISES)))
    return pool


def run():
    rng = random.Random(SEED)
    pool = build_pool(rng)
    rows = []
    d, d1 = date(2026, 1, 1), date(2026, 6, 30)
    while d <= d1:
        if d.weekday() < 5:
            dia = DIAS[d.weekday()]
            for g in range(1, 7):
                for slot, base in SLOTS.items():
                    fac = facilitador(d.isoformat(), dia, slot)
                    lam = base * DAY_FACTOR[d.weekday()] * GROUP_FACTOR[g]
                    lam *= FAC_MULT.get(fac, 1.0)
                    n = max(0, int(rng.gauss(lam, lam * 0.35)))
                    if n == 0:
                        continue
                    h, m = map(int, slot.split(":"))
                    uuid = f"L0{g}-{d.isoformat()}-{slot.replace(':', '')}"
                    topic = f"Sesión Grupal Latam 0{g}"
                    start_cl = datetime(d.year, d.month, d.day, h, m, tzinfo=CL)
                    su = start_cl.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    for persona, pais in rng.sample(pool, min(n, len(pool))):
                        jitter = rng.randint(-5, 50)
                        dur = rng.randint(8, 58) if rng.random() > 0.18 else rng.randint(0, 2)
                        jm = start_cl + timedelta(minutes=jitter)
                        lv = jm + timedelta(minutes=dur)
                        ju = jm.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                        lo = lv.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                        rows.append([f"Latam 0{g}", uuid, topic, su, persona,
                                     pais, ju, lo, dur * 60])
        d += timedelta(days=1)

    out = DATA_DIR / "latam_conexiones_raw.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["grupo", "meeting_uuid", "topic", "start_utc", "persona",
                    "pais", "join_utc", "leave_utc", "dur_seg"])
        w.writerows(rows)
    print(f"✓ {out}  ({len(rows)} conexiones sintéticas)")


if __name__ == "__main__":
    run()
