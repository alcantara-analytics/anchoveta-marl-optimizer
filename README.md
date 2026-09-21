# Optimizador Multiagente de Flota Anchovetera

Proyecto académico para la **asignación y ruteo de una flota homogénea de 15 cerqueros anchoveteros** con origen en Malabrigo, Chimbote y Callao.

> **Fuente espacial única:** todo el proyecto usa directamente `MapProbabilidad_adulto.csv`, versionado en la raíz del repositorio. No existe un modo demo, una grilla sintética ni una superficie suavizada de reemplazo.

## Flujo del proyecto

1. carga y validación de `MapProbabilidad_adulto.csv`;
2. selección de zonas candidatas sobre esa misma grilla;
3. máscara SERNANP opcional;
4. construcción del grafo navegable y rutas A*;
5. asignación Greedy, MILP y MARL;
6. cálculo de distancia, horas, combustible y costo de escenario;
7. mapas, tablas, trayectorias, simulación y reporte;
8. compilación del TDR en LaTeX.

## Dataset base

Archivo: `MapProbabilidad_adulto.csv`

Columnas: `Lon`, `Lat`, `Prob`.

La auditoría debe registrar:

```text
procedencia_probabilidad = MAP_PROBABILIDAD_ADULTO
grilla_probabilidad_generada_por_pipeline = false
interpolacion_probabilidad_usada = false
marl_perturbacion_probabilidad = false
```

La probabilidad no se reemplaza ni se perturba para entrenar el modelo principal.

## Qué sí es simulación

Las decisiones, rutas planeadas y movimiento de los barcos son salidas del modelo. La animación no representa tracking AIS/SISESAT histórico.

## Ejecución

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py
```

Para exigir que SERNANP esté disponible:

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
├── resumen_puerto_metodo.csv
├── costos_por_barco_greedy.csv
├── costos_por_barco_milp.csv
├── costos_por_barco_marl.csv
├── trayectorias_greedy.csv
├── trayectorias_milp.csv
├── trayectorias_marl.csv
├── mapa_probabilidad_zonas.png
├── mapa_asignacion_greedy.png
├── mapa_asignacion_milp.png
├── mapa_asignacion_marl.png
├── simulacion_flota_marl.gif
├── reporte_resultados.html
└── auditoria.json
```

## Informe y LaTeX

El TDR está en `docs/tdr/`. El workflow `compilar-tdr` ejecuta primero el pipeline con `MapProbabilidad_adulto.csv`, genera las figuras desde esos resultados y finalmente compila el PDF.

## Límite metodológico

`Prob` es probabilidad/puntuación de presencia. **No equivale directamente a toneladas de captura.** Para estimar toneladas se necesita CPUE, biomasa acústica o captura condicional.