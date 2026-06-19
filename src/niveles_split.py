"""
Split por nivel de cada celda día×franja, a partir de latam_conexiones_raw.csv.

Nivel desde la etiqueta del nombre: N1..N7, CE (esperanza), CF (felicidad).
Sin etiqueta → N1. Básico = N1+N2; Avanzado = N3..N7 + CE + CF.

Salida: latam_niveles_por_celda.csv
    dia_semana, slot, n_sesiones, basico_prom, avanzado_prom, total_prom
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from paths import DATA_DIR

MX = ZoneInfo("America/Mexico_City")
SLOTS = ["06:30", "11:00", "17:00", "19:00", "21:00"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def slot_of(dt):
    mins = dt.hour * 60 + dt.minute
    for s in SLOTS:
        h, mm = map(int, s.split(":"))
        ini = h * 60 + mm
        if ini - 10 <= mins <= ini + 60:
            return s
    return None


def nivel(s):
    t = str(s).lower()
    if re.search(r'(^|[^a-z])cf([^a-z]|$)|c/f', t):
        return "CF"
    if re.search(r'(^|[^a-z])ce([^a-z]|$)|c/e', t):
        return "CE"
    m = (re.search(r'n[\s\-]?([1-7])(?![0-9])', t)
         or re.search(r'nivel\s*([1-7])', t)
         or re.search(r'(?<![0-9])([1-7])(?![0-9])', t))
    return "N" + m.group(1) if m else "N1"


def run():
    df = pd.read_csv(DATA_DIR / "latam_conexiones_raw.csv")
    d = df["join_utc"].apply(
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(MX)
        if isinstance(s, str) and s else None)
    df = df[d.notna()].copy()
    d = d[d.notna()]
    df["dia_semana"] = d.apply(lambda x: DIAS[x.weekday()])
    df["slot"] = d.apply(slot_of)
    df["fecha"] = d.apply(lambda x: x.date().isoformat())
    df["persona"] = df["persona"].fillna("").astype(str)
    df = df[(df["slot"].notna()) & (df["persona"] != "")
            & (df["dia_semana"].isin(DIAS[:5]))]
    df["basico"] = df["persona"].apply(nivel).isin(["N1", "N2"])

    # persona distinta por sesión (grupo, fecha, dia, slot)
    pers = (df.groupby(["dia_semana", "slot", "grupo", "fecha", "persona"])
            ["basico"].first().reset_index())
    ses = (pers.groupby(["dia_semana", "slot", "grupo", "fecha"])
           .agg(bas=("basico", "sum"), tot=("persona", "size")).reset_index())
    ses["av"] = ses["tot"] - ses["bas"]

    out = (ses.groupby(["dia_semana", "slot"])
           .agg(n_sesiones=("tot", "size"),
                basico_prom=("bas", "mean"),
                avanzado_prom=("av", "mean"),
                total_prom=("tot", "mean")).reset_index())
    for c in ["basico_prom", "avanzado_prom", "total_prom"]:
        out[c] = out[c].round(1)
    out.to_csv(DATA_DIR / "latam_niveles_por_celda.csv", index=False)
    print("✓ latam_niveles_por_celda.csv")
    print(out.sort_values("total_prom", ascending=False).head(8).to_string(index=False))

    # --- escenarios de corte: nº de AVANZADOS por sesión según dónde se corta ---
    df["nivel"] = df["persona"].apply(nivel)
    pers2 = (df.groupby(["dia_semana", "slot", "grupo", "fecha", "persona"])
             ["nivel"].first().reset_index())
    escen = {"av_A": ["N1"], "av_B": ["N1", "N2"], "av_C": ["N1", "N2", "N3"]}
    base = (pers2.groupby(["dia_semana", "slot", "grupo", "fecha"])
            .size().reset_index(name="tot"))
    for col, bas in escen.items():
        pers2["_av"] = ~pers2["nivel"].isin(bas)
        s = (pers2.groupby(["dia_semana", "slot", "grupo", "fecha"])["_av"]
             .sum().reset_index(name=col))
        base = base.merge(s, on=["dia_semana", "slot", "grupo", "fecha"])
    esc = (base.groupby(["dia_semana", "slot"])
           .agg(total=("tot", "mean"), av_A=("av_A", "mean"),
                av_B=("av_B", "mean"), av_C=("av_C", "mean")).reset_index())
    for c in ["total", "av_A", "av_B", "av_C"]:
        esc[c] = esc[c].round(1)
    esc.sort_values("av_A", ascending=False).to_csv(
        DATA_DIR / "latam_avanzados_escenarios.csv", index=False)
    print("\n✓ latam_avanzados_escenarios.csv")


if __name__ == "__main__":
    run()
