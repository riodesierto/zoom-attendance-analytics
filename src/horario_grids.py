"""
Grillas semanales de facilitadores (datos de demostración, nombres ficticios).
Clave = fecha de inicio efectivo (lunes siguiente). Cada grilla rige hasta el
inicio de la siguiente; los huecos los cubre la anterior.
Estructura: { "YYYY-MM-DD": { slot: {dia: facilitador} } }  (solo Lun-Vie)
"""

SLOTS = ["06:30", "11:00", "17:00", "19:00", "21:00"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes"]


def _g(filas):
    """filas: lista de 5 listas [L,Ma,Mi,J,V] en orden de SLOTS."""
    return {SLOTS[i]: dict(zip(DIAS, filas[i])) for i in range(5)}


# Cada entrada: efectivo_desde -> grilla
GRIDS = {
    # foto 13-feb (vie) → rige 16-feb
    "2026-02-16": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Diego", "Ana", "Carla", "Paula"],
        ["Valentina", "Daniela", "Matías", "Fernanda", "Carla"],
        ["Diego", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Fernanda", "Sofía", "Javiera", "Daniela", "Sofía"],
    ]),
    # foto 20-feb → rige 23-feb (idéntica a la anterior)
    "2026-02-23": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Diego", "Ana", "Carla", "Paula"],
        ["Valentina", "Daniela", "Matías", "Fernanda", "Carla"],
        ["Diego", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Fernanda", "Sofía", "Javiera", "Daniela", "Sofía"],
    ]),
    # foto 27-feb → rige 02-mar (cubre tb 09-mar: no hay foto 05-mar)
    "2026-03-02": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Diego", "Ana", "Carla", "Paula"],
        ["Valentina", "Fernanda", "Matías", "Daniela", "Carla"],
        ["Diego", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Daniela", "Sofía", "Javiera", "Fernanda", "Sofía"],
    ]),
    # foto 12-mar (jue) → rige 16-mar
    "2026-03-16": _g([
        ["Sofía", "Valentina", "Diego", "Valentina", "Matías"],
        ["Matías", "Diego", "Diego", "Carla", "Paula"],
        ["Valentina", "Fernanda", "Matías", "Daniela", "Carla"],
        ["Diego", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Daniela", "Sofía", "Fernanda", "Fernanda", "Sofía"],
    ]),
    # foto 19-mar → rige 23-mar
    "2026-03-23": _g([
        ["Valentina", "Ana", "Diego", "Ana", "Matías"],
        ["Matías", "Diego", "Ana", "Carla", "Paula"],
        ["Valentina", "Fernanda", "Matías", "Daniela", "Carla"],
        ["Diego", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Daniela", "Sofía", "Fernanda", "Fernanda", "Sofía"],
    ]),
    # foto 26-mar (jue) → rige 30-mar. "" = celda vacía (sin facilitador)
    "2026-03-30": _g([
        ["Nicolás", "Ana", "Carla", "Ana", "Ana"],
        ["Matías", "Matías", "Fernanda", "", "Paula"],
        ["Daniela", "Fernanda", "Matías", "Pablo", "Carla"],
        ["Sofía", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Daniela", "Sofía", "Fernanda", "Fernanda", ""],
    ]),
    # foto 02-abr → rige 06-abr
    "2026-04-06": _g([
        ["Ana", "Nicolás", "Ana", "Ana", "Matías"],
        ["Matías", "Carla", "Diego", "Carla", "Paula"],
        ["Daniela", "Fernanda", "Matías", "Pablo", "Diego"],
        ["Sofía", "Matías", "Daniela", "Tomás", "Andrés"],
        ["Daniela", "Sofía", "Fernanda", "Sofía", "Fernanda"],
    ]),
    # foto 09-abr → rige 13-abr
    "2026-04-13": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Diego", "Ana", "Nicolás", "Paula"],
        ["Valentina", "Fernanda", "Matías", "Pablo", "Carla"],
        ["Diego", "Matías", "Tomás", "Daniela", "Andrés"],
        ["Daniela", "Sofía", "", "Fernanda", "Sofía"],
    ]),
    # foto 16-abr → rige 20-abr
    "2026-04-20": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Valentina", "Fernanda", "Valentina", "Pablo", "Daniela"],
        ["Diego", "Matías", "Tomás", "Daniela", "Andrés"],
        ["Sofía", "Sofía", "Javiera", "Fernanda", "Daniela"],
    ]),
    # foto 23-abr → rige 27-abr
    "2026-04-27": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Valentina", "Fernanda", "Valentina", "Pablo", "Daniela"],
        ["Fernanda", "Matías", "Tomás", "Daniela", "Andrés"],
        ["Sofía", "Sofía", "Javiera", "Sofía", ""],
    ]),
    # foto 30-abr → rige 04-may
    "2026-05-04": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Valentina", "Fernanda", "Valentina", "Pablo", "Carla"],
        ["Fernanda", "Matías", "Tomás", "Daniela", "Andrés"],
        ["Felipe", "Diego", "Javiera", "Fernanda", "Daniela"],
    ]),
    # foto 07-may → rige 11-may (cubre tb 18-may: no hay foto 14-may)
    "2026-05-11": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Valentina", "Fernanda", "Valentina", "Pablo", "Carla"],
        ["Fernanda", "Daniela", "Tomás", "Matías", "Andrés"],
        ["Felipe", "Diego", "Daniela", "Fernanda", "Javiera"],
    ]),
    # foto 21-may → rige 25-may
    "2026-05-25": _g([
        ["Ana", "Diego", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Valentina", "Fernanda", "Valentina", "Matías", "Carla"],
        ["Daniela", "Daniela", "Tomás", "Pablo", "Andrés"],
        ["Javiera", "Sofía", "Daniela", "Fernanda", "Sofía"],
    ]),
    # foto 28-may → rige 01-jun (idéntica a la anterior)
    "2026-06-01": _g([
        ["Ana", "Diego", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Valentina", "Fernanda", "Valentina", "Matías", "Carla"],
        ["Daniela", "Daniela", "Tomás", "Pablo", "Andrés"],
        ["Javiera", "Sofía", "Daniela", "Fernanda", "Sofía"],
    ]),
    # foto 04-jun → rige 08-jun
    "2026-06-08": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Nicolás", "Ana", "Diego", "Paula"],
        ["Diego", "Fernanda", "Valentina", "Matías", "Carla"],
        ["Daniela", "Daniela", "Nicolás", "Matías", "Andrés"],
        ["Javiera", "Sofía", "Daniela", "Fernanda", "Sofía"],
    ]),
    # foto 11-jun (13:53, definitiva del día) → rige 15-jun
    "2026-06-15": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Valentina", "Ana", "Diego", "Paula"],
        ["Diego", "Fernanda", "Valentina", "Matías", "Carla"],
        ["Daniela", "Daniela", "Antonia", "Carla", "Andrés"],
        ["Javiera", "Sofía", "Daniela", "Fernanda", "Sofía"],
    ]),
    # foto 18-jun → rige 22-jun (fuera del rango de datos: ene-18 jun)
    "2026-06-22": _g([
        ["Ana", "Valentina", "Diego", "Ana", "Matías"],
        ["Matías", "Valentina", "Ana", "Diego", "Paula"],
        ["Diego", "Fernanda", "Valentina", "Matías", "Carla"],
        ["Daniela", "Daniela", "Antonia", "Sofía", "Andrés"],
        ["Javiera", "Sofía", "Daniela", "Fernanda", "Sofía"],
    ]),
}
