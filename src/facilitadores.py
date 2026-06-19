"""
Análisis de facilitadores: atribuye cada sesión al facilitador que la dirigió
esa semana (según horario_grids.GRIDS) y rankea su poder de convocatoria.

Tres vistas:
  1. Bruto            — promedio de personas por sesión.
  2. Ajustado hora×día — índice vs lo esperado por efectos marginales de
                         franja y día (descuenta el "tirón" del horario).
  3. Vs misma celda   — índice vs el promedio de quien sea en ese día×franja.

Genera:
  - latam_sesiones_con_facilitador.csv
  - ranking_facilitadores.csv
  - ranking_facilitadores_vs_celda.csv
"""

import pandas as pd

from paths import DATA_DIR
from horario_grids import GRIDS

EFF = sorted(GRIDS.keys())
ROBUSTA_MIN = 30   # nº de sesiones para considerar la muestra robusta


def facilitador(fecha, dia, slot):
    """Facilitador vigente en `fecha` para esa celda (None si no hay grilla)."""
    g = None
    for e in EFF:
        if e <= fecha:
            g = GRIDS[e]
        else:
            break
    if g is None:
        return None
    return g.get(slot, {}).get(dia, "") or None


def run():
    r = pd.read_csv(DATA_DIR / "latam_sesiones_resumen.csv")
    r["facilitador"] = r.apply(
        lambda x: facilitador(x["fecha"], x["dia_semana"], x["slot"]), axis=1)
    r.to_csv(DATA_DIR / "latam_sesiones_con_facilitador.csv", index=False)

    sin = r["facilitador"].isna().sum()
    print(f"Sesiones: {len(r)} · atribuidas: {len(r) - sin} "
          f"· sin facilitador: {sin} ({100*sin/len(r):.0f}%)")

    ra = r[r["facilitador"].notna()].copy()

    # baseline marginal hora×día
    grand = ra["total_personas"].mean()
    sf = ra.groupby("slot")["total_personas"].mean() / grand
    df_ = ra.groupby("dia_semana")["total_personas"].mean() / grand
    ra["esp"] = grand * ra["slot"].map(sf) * ra["dia_semana"].map(df_)
    # baseline por celda (día×franja, cualquier facilitador)
    ra["celda"] = ra["dia_semana"] + " " + ra["slot"]
    ra["celda_prom"] = ra["celda"].map(ra.groupby("celda")["total_personas"].mean())

    g = (ra.groupby("facilitador")
         .agg(sesiones=("total_personas", "size"),
              total=("total_personas", "sum"),
              prom=("total_personas", "mean"),
              esperado_hxd=("esp", "mean"),
              esperado_celda=("celda_prom", "mean")).reset_index())
    g["indice_ajustado"] = (g["prom"] / g["esperado_hxd"]).round(3)
    g["indice_celda"] = (g["prom"] / g["esperado_celda"]).round(3)
    g["prom"] = g["prom"].round(1)
    g["esperado_hxd"] = g["esperado_hxd"].round(1)
    g["esperado_celda"] = g["esperado_celda"].round(1)
    g["muestra_robusta"] = g["sesiones"] >= ROBUSTA_MIN

    aj = g[["facilitador", "sesiones", "total", "prom", "esperado_hxd",
            "indice_ajustado", "muestra_robusta"]].sort_values(
        "indice_ajustado", ascending=False)
    aj.to_csv(DATA_DIR / "ranking_facilitadores.csv", index=False)

    vc = g[["facilitador", "sesiones", "prom", "esperado_celda",
            "indice_celda", "muestra_robusta"]].sort_values(
        "indice_celda", ascending=False)
    vc.to_csv(DATA_DIR / "ranking_facilitadores_vs_celda.csv", index=False)

    print("\nRanking ajustado hora×día (índice 1.00 = lo esperado):")
    print(aj.to_string(index=False))
    print("\n✓ CSVs de facilitadores exportados.")


if __name__ == "__main__":
    run()
