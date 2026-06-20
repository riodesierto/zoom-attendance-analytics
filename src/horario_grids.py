"""
Grillas semanales de facilitadores (datos de demostración, generados).

Asigna facilitadores a las 25 celdas (5 franjas × 5 días) semana a semana con
ROTACIÓN ALTA: cada facilitador termina liderando sesiones muy variadas a lo
largo del periodo. Esto permite, en el análisis, normalizar cada sesión por su
promedio y aislar el desempeño propio de cada facilitador, independiente del
horario que le tocó.

Estructura: { "YYYY-MM-DD": { slot: {dia: facilitador} } }  (efectivo desde)
Horarios en hora de Chile.
"""

import random
from datetime import date, timedelta

SLOTS = ["09:00", "12:00", "15:00", "18:00", "21:00"]   # franjas parejas (cada 3 h)
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes"]

# 16 facilitadores ficticios.
FACILITADORES = ["Ana", "Valentina", "Nicolás", "Diego", "Antonia", "Matías",
                 "Pablo", "Carla", "Paula", "Daniela", "Fernanda", "Tomás",
                 "Javiera", "Andrés", "Sofía", "Felipe"]

_WEEKS = 18
_FIRST_MONDAY = date(2026, 2, 16)


def _build():
    rng = random.Random(7)
    grids = {}
    for w in range(_WEEKS):
        eff = (_FIRST_MONDAY + timedelta(days=7 * w)).isoformat()
        grid = {s: {} for s in SLOTS}
        for s in SLOTS:               # asignación aleatoria por celda → rotación alta
            for d in DIAS:
                grid[s][d] = rng.choice(FACILITADORES)
        grids[eff] = grid
    return grids


GRIDS = _build()
