# Política de datos

Este repositorio no contiene `MapProbabilidad_adulto.csv`.

El repositorio es público. Si usas el archivo real del proyecto, colócalo únicamente en tu copia local:

```text
data/raw/MapProbabilidad_adulto.csv
```

La carpeta está excluida mediante `.gitignore`.

## Etiquetas de procedencia

El pipeline genera `outputs/auditoria.json`.

### CLIENT_INPUT

El mapa de probabilidad proviene del archivo suministrado por el proyecto.

### SIMULATED_DEMO

La superficie de probabilidad fue generada artificialmente por el propio código para:

- pruebas;
- CI;
- demostraciones;
- reproducibilidad pública.

## Trayectorias

Las rutas y movimientos de embarcaciones generados por el optimizador son simulaciones.

No son trayectorias históricas AIS o SISESAT.

## SERNANP

Cuando el modo SERNANP funciona, los GeoJSON descargados se guardan en:

```text
data/cache/
```

y también están ignorados por Git.

La auditoría indica si la máscara oficial fue aplicada o no.
