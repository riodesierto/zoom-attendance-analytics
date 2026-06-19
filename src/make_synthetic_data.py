"""
Generador de DATOS DE DEMOSTRACIÓN (sintéticos) para el showcase.

Produce data/latam_conexiones_raw.csv con el mismo esquema que generaría
extract_latam_sessions.py contra la Zoom Dashboard API, pero con datos
totalmente inventados (seed fijo). Permite correr el pipeline completo
(analyze → niveles → facilitadores → report) sin credenciales ni datos reales.

Esquema: grupo, meeting_uuid, topic, start_utc, persona, pais, join_utc,
          leave_utc, dur_seg
"""

import csv
import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from paths import DATA_DIR
from horario_grids import GRIDS

MX = ZoneInfo("America/Mexico_City")
SEED = 42

SLOTS = {"06:30": 7, "11:00": 5, "17:00": 11, "19:00": 9, "21:00": 6}  # base λ
DAY_FACTOR = {0: 1.0, 1: 1.05, 2: 1.15, 3: 0.95, 4: 0.80}  # Lun..Vie
GROUP_FACTOR = {1: 0.8, 2: 0.9, 3: 1.1, 4: 1.2, 5: 1.15, 6: 0.6}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes"]

# Efecto facilitador: cada uno convoca distinto (genera ranking disparejo).
FAC_MULT = {"Ana": 1.45, "Valentina": 1.35, "Nicolás": 1.30, "Diego": 1.25,
            "Antonia": 1.20, "Matías": 1.15, "Pablo": 1.10, "Carla": 1.05,
            "Paula": 1.00, "Daniela": 0.95, "Fernanda": 0.90, "Tomás": 0.85,
            "Javiera": 0.80, "Andrés": 0.75, "Sofía": 0.70, "Felipe": 0.62}
_EFF = sorted(GRIDS)


def facilitador(fecha, dia, slot):
    g = None
    for e in _EFF:
        if e <= fecha:
            g = GRIDS[e]
        else:
            break
    return (g.get(slot, {}).get(dia, "") or None) if g else None

# país → peso (mezcla realista, México domina)
PAISES = {"MX": 30, "CO": 18, "AR": 17, "GT": 8, "SV": 7, "CL": 5, "US": 5,
          "ES": 3, "PE": 2, "BR": 2, "DO": 1, "CR": 1, "BE": 1}
# nivel → peso (la base es abrumadoramente N1)
NIVELES = {"": 12, "N1": 58, "N2": 8, "N3": 5, "N4": 4, "N5": 3, "N6": 2,
           "N7": 3, "CE": 1, "CF": 1}

NOMBRES = ["María", "José", "Carlos", "Ana", "Luis", "Sofía", "Diego", "Paula",
           "Andrés", "Valentina", "Jorge", "Rodrigo", "Felipe", "Daniela",
           "Ricardo", "Fernanda", "Pablo", "Antonia", "Tomás", "Javiera",
           "Mateo", "Isidora", "Nicolás", "Florencia", "Gabriel", "Catalina",
           "Constanza", "Renata", "Martín", "Emilia", "Vicente", "Trinidad"]
APELLIDOS = ["González", "Rodríguez", "Pérez", "Soto", "Muñoz", "Rojas",
             "Díaz", "Flores", "Castro", "Vargas", "Reyes", "Morales",
             "Herrera", "Silva", "Núñez", "Torres", "Ramírez", "Gómez",
             "Fuentes", "Espinoza", "Contreras", "Sepúlveda", "Araya", "León"]


def _weighted(rng, d):
    keys, w = zip(*d.items())
    return rng.choices(keys, weights=w, k=1)[0]


def build_pool(rng, n=260):
    """Pool de personas recurrentes: (persona, pais)."""
    combos = set()
    pool = []
    while len(pool) < n:
        nom = f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}"
        if nom in combos:
            continue
        combos.add(nom)
        tag = _weighted(rng, NIVELES)
        persona = f"{nom} {tag}".strip()
        pool.append((persona, _weighted(rng, PAISES)))
    return pool


def run():
    rng = random.Random(SEED)
    pool = build_pool(rng)

    rows = []
    d0, d1 = date(2026, 1, 1), date(2026, 6, 30)
    d = d0
    while d <= d1:
        if d.weekday() < 5:  # Lun-Vie
            for g in range(1, 7):
                dia = DIAS[d.weekday()]
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
                    start_mx = datetime(d.year, d.month, d.day, h, m, tzinfo=MX)
                    start_utc = start_mx.astimezone(ZoneInfo("UTC"))
                    su = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                    for persona, pais in rng.sample(pool, min(n, len(pool))):
                        # ingreso dentro de la ventana [-5, +50] min del inicio
                        jitter = rng.randint(-5, 50)
                        dur = rng.randint(8, 58) if rng.random() > 0.18 else rng.randint(0, 2)
                        join_mx = start_mx + timedelta(minutes=jitter)
                        leave_mx = join_mx + timedelta(minutes=dur)
                        ju = join_mx.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
                        lv = leave_mx.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
                        rows.append([topic.replace("Sesión Grupal ", "Latam "),
                                     uuid, topic, su, persona, pais, ju, lv, dur * 60])
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
