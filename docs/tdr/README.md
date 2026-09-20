# TDR resuelto — Moises Alcantara

Esta carpeta contiene la propuesta técnica y económica en **LaTeX**, los resultados derivados usados en el informe y un generador reproducible de figuras.

## Estructura

```text
docs/tdr/
├── main.tex
├── sections/
├── data/
├── generar_figuras.py
└── figures/              # se genera automáticamente
```

## Compilar localmente

Desde la raíz del repositorio:

```bash
python docs/tdr/generar_figuras.py
cd docs/tdr
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

El PDF resultante será:

```text
docs/tdr/main.pdf
```

## GitHub Actions

El workflow `compilar-tdr.yml` genera automáticamente las figuras, compila el LaTeX y publica un artifact llamado:

```text
tdr-resuelto-moises-alcantara
```

## Evidencia

- Los CSV de esta carpeta son **resultados derivados** de la ejecución realizada con el archivo del proyecto.
- El archivo bruto `MapProbabilidad_adulto.csv` no se publica.
- Las trayectorias y movimientos de la flota son simulaciones del modelo.
- Los valores de combustible son estimaciones de referencia.
- La corrida reportada no materializó SERNANP; por eso el documento lo declara expresamente y no presenta los resultados como rutas legales finales.