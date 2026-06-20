"""
Análisis de sesiones Latam por horario (Chile) a partir de latam_conexiones_raw.csv.

Reglas:
- Franjas (hora de Chile, Lun-Vie), sesiones de 1 hora:
    09:00, 12:00, 15:00, 18:00, 21:00
- Una conexión cuenta para un slot si su hora de INGRESO (join) cae en
    [slot - MARGEN_MIN, slot + 60min]. Fuera de toda ventana → se descarta.
- Una SESIÓN = (grupo, fecha, slot). Se deduplican personas dentro de la
    sesión (las salas se reinician varias veces al día → varios meetings).

Genera:
- latam_sesiones_por_pais.csv   : grupo, fecha, dia_semana, slot, pais, n_personas
- latam_sesiones_resumen.csv    : grupo, fecha, dia_semana, slot, total_personas
- latam_heatmap_promedio.csv    : matriz slot × día (promedio personas/sesión)
- latam_heatmap_total.csv       : matriz slot × día (total personas)
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from paths import DATA_DIR

CHILE_TZ = ZoneInfo("America/Santiago")
RAW = DATA_DIR / "latam_conexiones_raw.csv"

SLOTS = ["09:00", "12:00", "15:00", "18:00", "21:00"]
MARGEN_MIN = 10           # tolerancia de ingreso antes del inicio
DUR_MIN = 60              # duración de la sesión
DOW = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def to_cl(iso):
    if not isinstance(iso, str) or not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(CHILE_TZ)


def asignar_slot(dt) -> str:
    """Slot al que pertenece la hora de ingreso, o None si está fuera."""
    if dt is None:
        return None
    mins = dt.hour * 60 + dt.minute
    for s in SLOTS:
        h, m = map(int, s.split(":"))
        ini = h * 60 + m
        if ini - MARGEN_MIN <= mins <= ini + DUR_MIN:
            return s
    return None


def run():
    df = pd.read_csv(RAW)
    print(f"Conexiones crudas: {len(df)}")

    dt = df["join_utc"].apply(to_cl)
    df["fecha_mx"] = dt.apply(lambda d: d.date().isoformat() if d else None)
    df["dow_idx"] = dt.apply(lambda d: d.weekday() if d else None)
    df["slot"] = dt.apply(asignar_slot)

    # Solo Lun-Vie y dentro de algún slot.
    m = df["slot"].notna() & df["dow_idx"].isin([0, 1, 2, 3, 4])
    val = df[m].copy()
    val["dia_semana"] = val["dow_idx"].astype(int).map(lambda i: DOW[i])
    print(f"Conexiones dentro de horario Lun-Vie: {len(val)} "
          f"({100*len(val)/len(df):.0f}%)")

    # Dedup persona dentro de la sesión (grupo, fecha, slot).
    val["persona"] = val["persona"].fillna("").astype(str)
    val = val[val["persona"] != ""]
    sesion = ["grupo", "fecha_mx", "dia_semana", "slot"]

    # --- por país ---
    por_pais = (val.drop_duplicates(sesion + ["persona", "pais"])
                .groupby(sesion + ["pais"]).size()
                .reset_index(name="n_personas")
                .sort_values(sesion))
    por_pais.columns = ["grupo", "fecha", "dia_semana", "slot", "pais", "n_personas"]
    por_pais.to_csv(DATA_DIR / "latam_sesiones_por_pais.csv", index=False)

    # --- resumen por sesión (persona única por sesión, sin importar país) ---
    resumen = (val.drop_duplicates(sesion + ["persona"])
               .groupby(sesion).size()
               .reset_index(name="total_personas")
               .sort_values(sesion))
    resumen.columns = ["grupo", "fecha", "dia_semana", "slot", "total_personas"]
    resumen.to_csv(DATA_DIR / "latam_sesiones_resumen.csv", index=False)

    # --- heatmaps: promedio y total por slot × día ---
    dias_orden = DOW[:5]
    piv_prom = (resumen.pivot_table(index="slot", columns="dia_semana",
                                    values="total_personas", aggfunc="mean")
                .reindex(index=SLOTS, columns=dias_orden))
    piv_tot = (resumen.pivot_table(index="slot", columns="dia_semana",
                                   values="total_personas", aggfunc="sum")
               .reindex(index=SLOTS, columns=dias_orden))
    piv_prom.to_csv(DATA_DIR / "latam_heatmap_promedio.csv")
    piv_tot.to_csv(DATA_DIR / "latam_heatmap_total.csv")

    print("\nPromedio de personas por sesión (slot × día):")
    print(piv_prom.round(1).to_string())
    print("\nTotal de personas (slot × día):")
    print(piv_tot.round(0).to_string())

    # ranking de slots
    rank = (resumen.groupby("slot")["total_personas"]
            .agg(["mean", "sum", "count"]).reindex(SLOTS).round(1))
    rank.columns = ["promedio", "total", "n_sesiones"]
    print("\nRanking de slots (todas las sesiones Lun-Vie):")
    print(rank.sort_values("promedio", ascending=False).to_string())

    # --- resumen por país (sobre conexiones dentro de horario) ---
    # Se excluye "Julito Lee": cuenta de monitoreo con cientos de conexiones
    # drop-by (CL) que distorsiona la estadística por país.
    val_pais = val[~val["persona"].str.lower().str.contains("julito", na=False)]
    val_dedup = val_pais.drop_duplicates(sesion + ["persona", "pais"])
    paises = (val_dedup.groupby("pais")
              .agg(personas_distintas=("persona", "nunique"),
                   asistencias=("persona", "size"),
                   sesiones=("fecha_mx", lambda s: s.nunique()))
              .reset_index()
              .sort_values("asistencias", ascending=False))
    paises.to_csv(DATA_DIR / "latam_paises.csv", index=False)
    print("\nTop países por asistencias:")
    print(paises.head(15).to_string(index=False))

    print("\n✓ CSVs exportados.")
    return piv_prom, piv_tot, rank, paises


if __name__ == "__main__":
    run()
