# Optimizador Multiagente de Flota Anchovetera

Proyecto académico para la **asignación y ruteo de una flota homogénea de 15 cerqueros anchoveteros** que operan desde Malabrigo, Chimbote y Callao.

> **Regla de evidencia:** el repositorio distingue explícitamente entre datos del proyecto, fuentes oficiales descargadas, parámetros de escenario y simulaciones. Nunca se presenta una simulación como si fuera una observación real.

## Qué incluye

El pipeline principal puede ejecutarse de extremo a extremo y genera:

1. carga de `MapProbabilidad_adulto.csv` o una grilla demo marcada como simulada;
2. selección de zonas candidatas espacialmente separadas;
3. intento opcional de incorporar **ANP y Zonas Reservadas de SERNANP**;
4. grafo navegable y rutas A*;
5. asignación simultánea de los 15 barcos mediante **Greedy** y **MILP**;
6. cálculo de distancia, tiempo de viaje, combustible y costo económico de escenario;
7. mapas de probabilidad, zonas y asignaciones;
8. gráficos de costos, combustible, ocupación y trade-off distancia/probabilidad;
9. simulación GIF del movimiento de la flota;
10. tablas resumen, auditoría de procedencia y reporte HTML en español.

## Importante: qué es real y qué es simulado

### Dato del proyecto

Si colocas:

```text
data/raw/MapProbabilidad_adulto.csv
```

la probabilidad queda registrada como:

```text
CLIENT_INPUT
```

### Datos oficiales opcionales

El modo `--sernanp auto` intenta descargar capas oficiales de SERNANP. Si la fuente no responde, el pipeline **continúa** pero deja registrado que la restricción oficial no pudo aplicarse.

Para exigirla:

```bash
python scripts/run_pipeline.py --sernanp estricto
```

### Simulación

- Las rutas asignadas y el movimiento de los barcos son **salidas simuladas del modelo**.
- Si se usa `--demo`, también la superficie de probabilidad es simulada y se etiqueta como `SIMULATED_DEMO`.
- El precio del combustible es un **parámetro económico de escenario**, no un precio observado, salvo que el usuario lo reemplace.

## Instalación

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Ejecución con la base del proyecto

Coloca el CSV en:

```text
data/raw/MapProbabilidad_adulto.csv
```

y ejecuta:

```bash
python scripts/run_pipeline.py
```

Ejemplo definiendo un precio de combustible para el escenario:

```bash
python scripts/run_pipeline.py --precio-combustible 5.00
```

## Ejecución demo totalmente reproducible

```bash
python scripts/run_pipeline.py --demo
```

## Salidas

```text
outputs/
├── zonas_candidatas.csv
├── costos_rutas.csv
├── asignacion_greedy.csv
├── asignacion_milp.csv
├── resumen_metodos.csv
├── costos_por_barco.csv
├── costos_por_puerto.csv
├── mapa_probabilidad_zonas.png
├── mapa_asignacion_greedy.png
├── mapa_asignacion_milp.png
├── grafico_comparacion_metodos.png
├── grafico_costos_por_barco.png
├── grafico_combustible_por_puerto.png
├── grafico_ocupacion_zonas.png
├── grafico_distancia_vs_probabilidad.png
├── simulacion_flota.gif
├── reporte_resultados.html
└── auditoria.json
```

## Costos

Para cada ruta se calculan:

```text
distancia_salida_nm
distancia_retorno_nm
distancia_total_nm
horas_salida
horas_retorno
horas_total
combustible_salida_l
combustible_retorno_l
combustible_total_l
costo_combustible_pen
costo_operativo_pen
costo_total_pen
```

La fórmula base es:

```text
combustible = tasa_referencia_L/h × horas_de_viaje
```

y:

```text
costo_combustible = combustible_total_L × precio_combustible_S/L
```

El precio puede modificarse por línea de comandos.

## Estructura

```text
anchoveta-marl-optimizer/
├── src/anchoveta_marl/
│   ├── config.py
│   ├── data.py
│   ├── official_data.py
│   ├── routing.py
│   ├── optimization.py
│   ├── reporting.py
│   └── simulation.py
├── scripts/
│   └── run_pipeline.py
├── notebooks/
│   └── 01_analisis_completo_es.ipynb
├── tests/
├── docs/
└── .github/workflows/
```

## GitHub Actions

Cada push ejecuta:

- tests unitarios;
- pipeline demo funcional;
- auditoría de simulación;
- generación de gráficos, tablas y reporte;
- carga de `outputs/` como artifact descargable.

## Límite metodológico

`Prob` es probabilidad/puntuación de presencia del mapa suministrado. **No equivale directamente a toneladas de captura**.

Para optimizar toneladas se necesitaría una segunda capa de CPUE, biomasa o captura condicional observada.

## Privacidad

El repositorio actualmente es público. El archivo `MapProbabilidad_adulto.csv` está excluido mediante `.gitignore` y **no debe subirse** salvo que tengas autorización para publicarlo.
