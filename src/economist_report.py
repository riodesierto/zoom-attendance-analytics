"""
Informe PDF en estilo The Economist (visual styleguide v1.2) de la asistencia
a sesiones Latam, a partir de los CSV que genera analyze_latam_sessions.py.

Estilo: tag rojo, títulos condensados, gridlines mínimas, paleta oficial,
escala secuencial azul (equal-lightness) para heatmaps.

Salida: informe_latam.pdf  (+ PNGs intermedios para revisión)
"""

import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from paths import DATA_DIR, REPORTS_DIR, FONTS_DIR

# ---------- Paleta Economist (web hex) ----------
ECON_RED = "#E3120B"
BLACK = "#0C0C0C"
BLUE = "#006BA2"
CYAN = "#3EBCD2"
TEAL = "#379A8B"
BKGD = "#E9EDF0"        # print background
GREY = "#758D99"
GREY_LT = "#B7C6CF"
NAVY = "#3F5661"
SRC = "#5A6A72"         # source text ~75% black sobre fondo claro

# Escala secuencial azul (equal-lightness), claro→oscuro
BLUE_SCALE = ["#CFE3F3", "#98DAFF", "#5DA4DF", "#1270A8", "#00588D"]
CMAP_BLUE = LinearSegmentedColormap.from_list("econ_blue", BLUE_SCALE)
RED_SCALE = ["#FDE0DE", "#FF8785", "#E64E53", "#C7303C", "#A81829"]
CMAP_RED = LinearSegmentedColormap.from_list("econ_red", RED_SCALE)

# ---------- Tipografía ----------
# Roboto Condensed: alternativa libre (Apache) cercana a Econ Sans Condensed.
# La fuente real de The Economist (Econ Sans / Milo) es propietaria.
COND = "PT Sans Narrow"  # fallback
if FONTS_DIR.is_dir():
    for _f in ("RobotoCondensed-Regular.ttf", "RobotoCondensed-Medium.ttf",
               "RobotoCondensed-Bold.ttf"):
        _p = FONTS_DIR / _f
        if _p.exists():
            fm.fontManager.addfont(str(_p))
    if any(f.name == "Roboto Condensed" for f in fm.fontManager.ttflist):
        COND = "Roboto Condensed"

plt.rcParams.update({
    "font.family": COND,
    "font.size": 11,
    "text.color": BLACK,
    "axes.edgecolor": BLACK,
    "axes.labelcolor": BLACK,
    "xtick.color": BLACK,
    "ytick.color": BLACK,
    "figure.dpi": 150,
})

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes"]
DIAS_LBL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
SLOTS = ["06:30", "11:00", "17:00", "19:00", "21:00"]

# Código ISO → nombre completo de país (es).
PAIS_NOMBRE = {
    "MX": "México", "CO": "Colombia", "AR": "Argentina", "GT": "Guatemala",
    "SV": "El Salvador", "CL": "Chile", "US": "Estados Unidos", "ES": "España",
    "PE": "Perú", "BR": "Brasil", "DO": "Rep. Dominicana", "BE": "Bélgica",
    "GB": "Reino Unido", "JP": "Japón", "MT": "Malta", "IN": "India",
    "PY": "Paraguay", "EC": "Ecuador", "VE": "Venezuela", "UY": "Uruguay",
    "CA": "Canadá", "FR": "Francia", "IT": "Italia", "DE": "Alemania",
    "NL": "Países Bajos", "CR": "Costa Rica", "PA": "Panamá", "BO": "Bolivia",
    "HN": "Honduras", "NI": "Nicaragua", "CH": "Suiza", "AU": "Australia",
    "PR": "Puerto Rico", "??": "Sin ubicación",
}


def nombre_pais(code):
    return PAIS_NOMBRE.get(str(code), str(code))


def _econ_header(fig, x, y, titulo, subtitulo):
    """Tag rojo + título + subtítulo, estilo Economist, en coords de figura."""
    # tag rojo
    fig.add_artist(plt.Rectangle((x, y), 0.055, 0.011, color=ECON_RED,
                                 transform=fig.transFigure, zorder=5, clip_on=False))
    fig.text(x, y - 0.055, titulo, fontsize=21, fontweight="bold",
             family=COND, color=BLACK, va="top")
    fig.text(x, y - 0.105, subtitulo, fontsize=12.5, family=COND,
             color=BLACK, va="top")


def _source(fig, x, y, texto):
    fig.text(x, y, texto, fontsize=9, family=COND, color=SRC, va="bottom")


def _tz_tag(fig, x=0.92, y=0.06):
    """Etiqueta fija: todos los gráficos usan hora de México."""
    fig.text(x, y, "Horarios en hora de México (UTC-6)", fontsize=9,
             family=COND, color=SRC, va="bottom", ha="right")


def _texto_interpreta(fig, x, y, lead, cuerpo):
    """Bloque interpretativo: título corto en azul + párrafo (pre-envuelto)."""
    fig.text(x, y, lead, fontsize=13, fontweight="bold", family=COND,
             color=BLUE, va="top")
    fig.text(x, y - 0.030, cuerpo, fontsize=11.5, family=COND, color=BLACK,
             va="top", linespacing=1.45)


def heatmap_page(pdf, piv, titulo, subtitulo, fuente, cmap, fmt="{:.0f}",
                 lead=None, cuerpo=None):
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor("white")
    _econ_header(fig, 0.08, 0.93, titulo, subtitulo)

    ax = fig.add_axes([0.20, 0.40, 0.72, 0.38])
    data = piv.reindex(index=SLOTS, columns=DIAS).values.astype(float)
    vmax = np.nanmax(data)
    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=vmax)

    ax.set_xticks(range(len(DIAS)))
    ax.set_xticklabels(DIAS_LBL, fontsize=11.5)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(len(SLOTS)))
    ax.set_yticklabels([f"{s} h" for s in SLOTS], fontsize=12)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    # valores dentro de cada celda
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if np.isnan(v):
                continue
            txt = fmt.format(v)
            color = "white" if v > vmax * 0.55 else BLACK
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=12.5, fontweight="bold", color=color)

    # líneas blancas finas entre celdas (look de tabla)
    ax.set_xticks(np.arange(-.5, len(DIAS), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(SLOTS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=3)
    ax.tick_params(which="minor", length=0)

    if lead or cuerpo:
        _texto_interpreta(fig, 0.08, 0.31, lead or "", cuerpo or "")
    _source(fig, 0.08, 0.06, fuente)
    _tz_tag(fig)
    pdf.savefig(fig)
    plt.close(fig)


def barh_page(pdf, labels, values, titulo, subtitulo, fuente, lead=None,
              cuerpo=None, color=BLUE, fmt="{:.0f}"):
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor("white")
    _econ_header(fig, 0.08, 0.93, titulo, subtitulo)

    ax = fig.add_axes([0.30, 0.30, 0.62, 0.46])
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=color, height=0.7, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.tick_params(length=0)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BLACK)
    ax.xaxis.grid(True, color=GREY_LT, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    # etiqueta de valor al final de cada barra
    for yi, v in zip(y, values):
        ax.text(v + max(values) * 0.01, yi, fmt.format(v), va="center",
                fontsize=11, color=BLACK)

    if lead or cuerpo:
        _texto_interpreta(fig, 0.08, 0.225, lead or "", cuerpo or "")
    _source(fig, 0.08, 0.06, fuente)
    _tz_tag(fig)
    pdf.savefig(fig)
    plt.close(fig)


def split_page(pdf, rows, titulo, subtitulo, fuente, lead, cuerpo, viable=12):
    """rows: lista de (etiqueta, basico, avanzado). Barra apilada con el
    tamaño REAL de cada grupo por nivel + línea de tamaño mínimo viable."""
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor("white")
    _econ_header(fig, 0.08, 0.93, titulo, subtitulo)

    ax = fig.add_axes([0.30, 0.34, 0.60, 0.38])
    y = np.arange(len(rows))[::-1]
    maxv = max(b + a for _, b, a in rows)
    for yi, (lab, bas, av) in zip(y, rows):
        ax.barh(yi, bas, color=BLUE, height=0.62, zorder=3)
        ax.barh(yi, av, left=bas, color=TEAL, height=0.62, zorder=3)
        ax.text(bas / 2, yi, f"{bas:.0f}", ha="center", va="center",
                color="white", fontsize=11.5, fontweight="bold", zorder=5)
        # etiqueta del avanzado: dentro si cabe, si no afuera
        if av >= maxv * 0.10:
            ax.text(bas + av / 2, yi, f"{av:.0f}", ha="center", va="center",
                    color="white", fontsize=11.5, fontweight="bold", zorder=5)
        else:
            ax.text(bas + av + maxv * 0.012, yi, f"{av:.0f}", ha="left",
                    va="center", color=TEAL, fontsize=11, fontweight="bold", zorder=5)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=12)
    ax.tick_params(length=0)
    for s in ["top", "right", "left", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.set_xticks([])
    ax.set_xlim(0, maxv * 1.12)

    # línea de tamaño mínimo viable por grupo
    ax.axvline(viable, color=ECON_RED, lw=1.2, ls=(0, (4, 2)), zorder=6)
    ax.text(viable, len(rows) - 0.35, f"  mínimo viable ({viable})",
            color=ECON_RED, fontsize=10, va="bottom", family=COND)

    # leyenda básico/avanzado
    fig.add_artist(plt.Rectangle((0.30, 0.775), 0.022, 0.011, color=BLUE,
                                 transform=fig.transFigure, clip_on=False))
    fig.text(0.328, 0.781, "Básico (N1-N2)", fontsize=11, family=COND, va="center")
    fig.add_artist(plt.Rectangle((0.50, 0.775), 0.022, 0.011, color=TEAL,
                                 transform=fig.transFigure, clip_on=False))
    fig.text(0.528, 0.781, "Avanzado (N3-N7, CE, CF)", fontsize=11, family=COND, va="center")

    _texto_interpreta(fig, 0.08, 0.265, lead, cuerpo)
    _source(fig, 0.08, 0.06, fuente)
    _tz_tag(fig)
    pdf.savefig(fig)
    plt.close(fig)


def grouped_barh_page(pdf, rows, series, colors, titulo, subtitulo, fuente,
                      lead, cuerpo):
    """rows: lista de (etiqueta, [v_serie1, v_serie2, ...]).
    series: nombres para la leyenda. colors: un color por serie."""
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor("white")
    _econ_header(fig, 0.08, 0.93, titulo, subtitulo)

    ax = fig.add_axes([0.30, 0.32, 0.60, 0.40])
    n = len(series)
    h = 0.8 / n
    base = np.arange(len(rows))[::-1]
    maxv = max(max(v) for _, v in rows)
    for s in range(n):
        ys = base + (n / 2 - 0.5 - s) * h
        vals = [r[1][s] for r in rows]
        ax.barh(ys, vals, height=h, color=colors[s], zorder=3)
        for yy, v in zip(ys, vals):
            ax.text(v + maxv * 0.015, yy, f"{v:.0f}", va="center",
                    fontsize=9.5, color=BLACK)
    ax.set_yticks(base)
    ax.set_yticklabels([r[0] for r in rows], fontsize=12)
    ax.tick_params(length=0)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(BLACK)
    ax.set_xlim(0, maxv * 1.12)
    ax.xaxis.grid(True, color=GREY_LT, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    # leyenda
    lx = 0.30
    for s in range(n):
        fig.add_artist(plt.Rectangle((lx, 0.76), 0.020, 0.010, color=colors[s],
                                     transform=fig.transFigure, clip_on=False))
        fig.text(lx + 0.026, 0.765, series[s], fontsize=10.5, family=COND, va="center")
        lx += 0.026 + 0.013 * len(series[s])

    _texto_interpreta(fig, 0.08, 0.25, lead, cuerpo)
    _source(fig, 0.08, 0.06, fuente)
    _tz_tag(fig)
    pdf.savefig(fig)
    plt.close(fig)


def cover_page(pdf, kpis, periodo, autor, abstract):
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor("white")
    # franja roja superior
    fig.add_artist(plt.Rectangle((0, 0.93), 1, 0.07, color=ECON_RED,
                                 transform=fig.transFigure, clip_on=False))
    fig.text(0.08, 0.875, "Asistencia a sesiones de meditación",
             fontsize=29, fontweight="bold", family=COND, color=BLACK, va="top")
    fig.text(0.08, 0.80, "Sesiones Grupales Latam · qué horarios concentran más participación",
             fontsize=14, family=COND, color=NAVY, va="top")
    fig.text(0.08, 0.765, periodo, fontsize=12, family=COND, color=SRC, va="top")

    # Abstract / resumen ejecutivo
    fig.text(0.08, 0.715, "Resumen", fontsize=13, fontweight="bold",
             family=COND, color=BLUE, va="top")
    fig.text(0.08, 0.685, abstract, fontsize=11.8, family=COND, color=BLACK,
             va="top", linespacing=1.5)

    # KPIs
    y0 = 0.40
    for i, (num, lab) in enumerate(kpis):
        x = 0.08 + (i % 2) * 0.46
        yy = y0 - (i // 2) * 0.135
        fig.text(x, yy, num, fontsize=31, fontweight="bold", family=COND,
                 color=BLUE, va="top")
        fig.text(x, yy - 0.05, lab, fontsize=12, family=COND, color=BLACK, va="top")

    fig.add_artist(plt.Line2D([0.08, 0.92], [0.11, 0.11], color=BLACK,
                              linewidth=0.8, transform=fig.transFigure))
    fig.text(0.08, 0.092, autor, fontsize=11.5, family=COND, color=BLACK, va="top")
    fig.text(0.92, 0.092, "Fuente: Zoom Dashboard API · hora de México",
             fontsize=9.5, family=COND, color=SRC, va="top", ha="right")
    pdf.savefig(fig)
    plt.close(fig)


# Autoría (portada).
AUTOR = "Análisis y visualización: Cristian Esparza"


def _wrap(t, w=96):
    return "\n".join(textwrap.fill(p, w) for p in t.split("\n"))


def m(n):
    """Entero con punto como separador de miles (formato es)."""
    return f"{int(round(n)):,}".replace(",", ".")


def narrativa(resumen, paises, piv_prom, piv_tot,
              n_ses, total, n_paises, n_grupos):
    """Genera abstract + textos interpretativos desde los datos reales."""
    pp = piv_prom.reindex(index=SLOTS, columns=DIAS)
    pt = piv_tot.reindex(index=SLOTS, columns=DIAS)
    lbl = dict(zip(DIAS, DIAS_LBL))

    # Celda promedio máxima
    s_i, d_i = divmod(int(pp.values.argmax()), pp.shape[1])
    best_slot, best_day = SLOTS[s_i], DIAS[d_i]
    best_val = pp.values[s_i, d_i]
    # Mejor franja y mejor día (promedios marginales)
    slot_rank = pp.mean(axis=1).sort_values(ascending=False)
    day_rank = pp.mean(axis=0).sort_values(ascending=False)
    top_slot, top_slot_v = slot_rank.index[0], slot_rank.iloc[0]
    top_day = day_rank.index[0]

    # Top-3 celdas (día × franja) más concurridas
    flat = [(SLOTS[i], DIAS[j], pp.values[i, j])
            for i in range(pp.shape[0]) for j in range(pp.shape[1])]
    flat = [x for x in flat if x[2] == x[2]]  # descarta NaN
    top_cells = sorted(flat, key=lambda x: x[2], reverse=True)[:3]
    top_cells_txt = "; ".join(
        f"{lbl[d]} {s} h ({v:.0f})" for s, d, v in top_cells)

    # Celda total máxima
    ts_i, td_i = divmod(int(pt.values.argmax()), pt.shape[1])
    tot_slot, tot_day, tot_val = SLOTS[ts_i], DIAS[td_i], pt.values[ts_i, td_i]

    # Países
    pais_top = paises.sort_values("asistencias", ascending=False).reset_index(drop=True)
    p1 = pais_top.iloc[0]
    top3 = pais_top.head(3)
    top3_share = 100 * top3["asistencias"].sum() / pais_top["asistencias"].sum()

    abstract = _wrap(
        f"Este informe busca identificar los horarios más populares de las "
        f"sesiones grupales Latam para orientar decisiones sobre su "
        f"programación. Entre enero y junio de 2026 se analizaron {m(n_ses)} "
        f"sesiones de los grupos Latam 01 a 06, contabilizando únicamente "
        f"conexiones de lunes a viernes dentro de las cinco franjas oficiales "
        f"(06:30, 11:00, 17:00, 19:00 y 21:00, hora de México), con {m(total)} "
        f"asistencias desde {n_paises} países. La sesión de mayor convocatoria "
        f"promedio es {lbl[best_day]} a las {best_slot} h "
        f"({best_val:.0f} personas por sesión) y, en el agregado semanal, el "
        f"horario de {top_slot} h es el más concurrido. "
        f"{nombre_pais(p1['pais'])} lidera la participación y, junto "
        f"con {nombre_pais(top3.iloc[1]['pais'])} y "
        f"{nombre_pais(top3.iloc[2]['pais'])}, concentra el {top3_share:.0f}% de "
        f"las asistencias.", 104)

    prom = _wrap(
        f"Cada celda promedia los asistentes por sesión en esa franja y día, lo "
        f"que permite comparar horarios independientemente de cuántas veces se "
        f"repitieron: es la métrica clave para identificar las sesiones más "
        f"populares. Las tres más concurridas son {top_cells_txt}. El horario de "
        f"{top_slot} h sostiene la mejor convocatoria a lo largo de la semana "
        f"({top_slot_v:.0f} personas por sesión en promedio) y el día de mayor "
        f"afluencia tiende a ser {lbl[top_day]}.")

    tot = _wrap(
        f"Aquí se acumula el total de asistencias: combina cuánta gente asiste y "
        f"cuántas veces ocurrió cada franja en el semestre. La mayor masa de "
        f"asistencias se concentra el {lbl[tot_day]} a las {tot_slot} h "
        f"({m(tot_val)} en total). A diferencia del promedio, este mapa premia "
        f"las franjas frecuentes y de alta convocatoria simultáneamente, útil "
        f"para dimensionar carga y priorizar recursos.")

    pais = _wrap(
        f"{nombre_pais(p1['pais'])} encabeza con {m(p1['asistencias'])} "
        f"asistencias de {m(p1['personas_distintas'])} personas distintas. "
        f"Los tres primeros países reúnen el {top3_share:.0f}% del total, lo que "
        f"revela una base de participación fuertemente concentrada en pocos "
        f"mercados. El país se deriva de la ubicación que reporta Zoom.")

    return {"abstract": abstract, "prom": prom, "tot": tot, "paises": pais}


def run():
    resumen = pd.read_csv(DATA_DIR / "latam_sesiones_resumen.csv")
    paises = pd.read_csv(DATA_DIR / "latam_paises.csv")
    piv_prom = pd.read_csv(DATA_DIR / "latam_heatmap_promedio.csv", index_col=0)
    piv_tot = pd.read_csv(DATA_DIR / "latam_heatmap_total.csv", index_col=0)

    n_sesiones = len(resumen)
    total_personas = int(resumen["total_personas"].sum())
    n_paises = paises["pais"].nunique()
    n_grupos = resumen["grupo"].nunique()

    fuente = "Fuente: Zoom Dashboard API · elaboración propia"
    narr = narrativa(resumen, paises, piv_prom, piv_tot,
                     n_sesiones, total_personas, n_paises, n_grupos)

    # Facilitadores: promedio de participantes por sesión (muestra robusta).
    fac = pd.read_csv(DATA_DIR / "ranking_facilitadores.csv")
    fac_top = fac[fac["muestra_robusta"]].sort_values("prom", ascending=False)
    f1, fN = fac_top.iloc[0], fac_top.iloc[-1]
    fac_cuerpo = _wrap(
        f"Cada sesión se atribuye al facilitador que la dirigió esa semana. En "
        f"promedio de participantes por sesión, {f1['facilitador']} encabeza con "
        f"{f1['prom']:.0f}, frente a los {fN['prom']:.0f} de {fN['facilitador']} "
        f"al final de la tabla: una brecha que se sostiene incluso ajustando por "
        f"horario y día. Identificar quién convoca más permite asignar a los "
        f"facilitadores más fuertes a las franjas de mayor potencial.")

    with PdfPages(REPORTS_DIR / "informe_latam.pdf") as pdf:
        cover_page(
            pdf,
            kpis=[
                (f"{n_sesiones:,}".replace(",", "."), "sesiones analizadas (Lun-Vie)"),
                (f"{total_personas:,}".replace(",", "."), "asistencias contabilizadas"),
                (f"{n_paises}", "países conectados"),
                (f"{n_grupos}", "grupos Latam (01–06)"),
            ],
            periodo="Enero – junio 2026 · Lunes a viernes · hora de México",
            autor=AUTOR,
            abstract=narr["abstract"],
        )
        heatmap_page(
            pdf, piv_prom,
            "Las sesiones más concurridas",
            "Promedio de personas por sesión · franja horaria × día (Lun-Vie)",
            fuente, CMAP_BLUE, fmt="{:.0f}",
            lead="Qué muestra", cuerpo=narr["prom"],
        )
        heatmap_page(
            pdf, piv_tot,
            "Dónde se concentra el flujo",
            "Total acumulado de asistencias · franja horaria × día (Lun-Vie)",
            fuente, CMAP_RED, fmt="{:.0f}",
            lead="Qué muestra", cuerpo=narr["tot"],
        )
        top = paises.head(12).copy()
        barh_page(
            pdf, [nombre_pais(c) for c in top["pais"]], top["asistencias"].values,
            "El mapa de la convocatoria",
            "Asistencias contabilizadas por país · sesiones Lun-Vie (top 12)",
            fuente, color=TEAL, fmt="{:.0f}",
            lead="Qué muestra", cuerpo=narr["paises"],
        )
        barh_page(
            pdf, fac_top["facilitador"].tolist(), fac_top["prom"].values,
            "¿Quién convoca más?",
            "Promedio de participantes por sesión, por facilitador (Lun-Vie)",
            fuente, color=BLUE, fmt="{:.1f}",
            lead="Qué muestra", cuerpo=fac_cuerpo,
        )

    print(f"✓ {REPORTS_DIR / 'informe_latam.pdf'} generado")


if __name__ == "__main__":
    run()
