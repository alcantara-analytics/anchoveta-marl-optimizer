# Política de datos

La fuente espacial principal del proyecto está versionada en:

```text
data/raw/MapProbabilidad_adulto.csv
```

El archivo es la base común para:

- selección de zonas;
- ruteo sobre la grilla;
- Greedy;
- MILP;
- entrenamiento MARL;
- mapas y figuras del TDR.

## Integridad

SHA256 esperado:

```text
3eb0abd9308a2bda62285eb9718485c612e137be13fc51c33bcdfbe2fed3704f
```

El script `scripts/materializar_datos.py` verifica ese hash cuando encuentra el archivo.

## Simulación

La superficie `Prob` no se simula. Lo que sí es simulado/modelado:

- decisiones de asignación;
- rutas planeadas;
- movimiento de los agentes;
- entrenamiento estocástico de la política MARL.

Esas trayectorias no son tracks AIS o SISESAT.

## SERNANP

Las geometrías descargadas por el módulo opcional de SERNANP se guardan en `data/cache/`. La auditoría indica si la máscara legal fue aplicada.
