# Optimizador Multiagente de Flota Anchovetera

Proyecto académico para la **asignación y ruteo de una flota homogénea de 15 cerqueros anchoveteros** que operan desde Malabrigo, Chimbote y Callao.

> **Fuente espacial única:** todo el pipeline usa `data/raw/MapProbabilidad_adulto.csv`. No existe un modo demo que sustituya esa superficie por una probabilidad sintética.

## Qué incluye

El pipeline ejecuta:

1. carga y validación de `MapProbabilidad_adulto.csv`;
2. selección de zonas candidatas sobre esa misma grilla;
3. incorporación opcional de ANP/Zonas Reservadas de SERNANP;
4. grafo navegable y rutas A*;
5. asignación de 15 barcos mediante Greedy, MILP y MARL cooperativo;
6. cálculo de distancia, tiempo, combustible y costo de escenario;
7. mapas sobre la grilla completa;
8. gráficos comparativos y diagnósticos;
9. simulación GIF de las rutas planeadas;
10. auditoría, reporte HTML y TDR en LaTeX.

## Qué es dato y qué es simulación

### Dato base del proyecto

`MapProbabilidad_adulto.csv` está versionado en el repositorio y contiene:

```text
Lon
Lat
Prob
```

El pipeline valida su integridad y registra:

```text
MAP_PROBABILIDAD_ADULTO
```

La superficie de probabilidad **no se reemplaza ni se perturba** durante el entrenamiento principal.

### MARL

El entrenamiento MARL usa la misma grilla estática y real del proyecto. La aleatoriedad se limita al muestreo de acciones propio del aprendizaje por refuerzo; no se generan mapas sintéticos.

### Simulación

Las rutas, asignaciones y movimiento animado de las embarcaciones son **salidas del modelo**. No representan tracks AIS/SISESAT observados.

## Ejecución

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python scripts/run_pipeline.py
```

Para exigir la máscara SERNANP:

```bash
python scripts/run_pipeline.py --sernanp estricto
```

## Salidas principales

```text
outputs/
├── zonas_candidatas.csv
├── costos_rutas.csv
├── asignacion_greedy.csv
├── asignacion_milp.csv
├── asignacion_marl.csv
├── historial_entrenamiento_marl.csv
├── resumen_metodos.csv
├── costos_por_barco.csv
├── costos_por_puerto.csv
├── mapa_probabilidad_zonas.png
├── mapa_asignacion_greedy.png
├── mapa_asignacion_milp.png
├── mapa_asignacion_marl.png
├── simulacion_flota_marl.gif
├── reporte_resultados.html
└── auditoria.json
```

## Costos

[
Combustible = q_{fuel}	imes Horas
]

[
Costo_{combustible}=Litros	imes Precio_{combustible}
]

El precio de combustible y cualquier costo operativo adicional son parámetros de escenario salvo que se sustituyan por datos observados.

## TDR e informe

El proyecto LaTeX está en:

```text
docs/tdr/
```

y los resultados ampliados en:

```text
docs/resultados_ampliados/
```

GitHub Actions compila el TDR y valida el pipeline contra `MapProbabilidad_adulto.csv`.

## Límite metodológico

`Prob` es probabilidad/puntuación de presencia. **No equivale directamente a toneladas de captura.** Para modelar toneladas se requiere CPUE, biomasa acústica o captura condicional.
