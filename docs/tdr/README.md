# TDR resuelto — Moises Alcantara

El informe se genera de forma reproducible a partir del archivo `MapProbabilidad_adulto.csv` de la raíz del repositorio.

## Flujo

```bash
python scripts/run_pipeline.py --sernanp no --no-gif
python docs/tdr/generar_figuras.py
cd docs/tdr
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

## Importante

- No se usan CSV de resultados estáticos versionados dentro de `docs/tdr/data/`.
- Las tablas y figuras del TDR se generan desde `outputs/` en cada ejecución.
- La superficie de probabilidad viene directamente de `MapProbabilidad_adulto.csv`.
- No se usa una grilla sintética, suavizada o interpolada.
- Las rutas y movimientos de barcos sí son salidas simuladas del modelo.
- Si SERNANP no está aplicado, no se dibujan exclusiones regulatorias ficticias.

## GitHub Actions

El workflow `compilar-tdr` ejecuta el pipeline, genera las figuras, compila el PDF y publica el artifact `tdr-resuelto-map-probabilidad-adulto`.