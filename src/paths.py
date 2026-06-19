"""Rutas centralizadas del proyecto, relativas a la raíz del repositorio.

Permite ejecutar los scripts desde cualquier directorio sin romper las rutas
de datos. La raíz es el directorio que contiene a `src/`.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"          # CSV generados (datos crudos y agregados)
OUTPUT_DIR = ROOT / "output"      # exportaciones Excel por país
FONTS_DIR = ROOT / "fonts"        # tipografías para el informe
REPORTS_DIR = ROOT / "reports"    # PDF del informe
ENV_FILE = ROOT / ".env"          # credenciales Zoom (no versionado)

for _d in (DATA_DIR, OUTPUT_DIR, REPORTS_DIR):
    _d.mkdir(exist_ok=True)
