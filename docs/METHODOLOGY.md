# Metodología y frontera de evidencia

## Problema central

El proyecto asigna 15 agentes homogéneos que representan cerqueros anchoveteros a zonas espaciales candidatas, equilibrando:

- probabilidad de presencia;
- distancia recorrida;
- tiempo de navegación;
- combustible;
- costo económico de escenario;
- congestión de flota;
- restricciones geográficas cuando SERNANP está disponible.

## Datos observados o suministrados

### Mapa de probabilidad

Cuando existe localmente `MapProbabilidad_adulto.csv`, el sistema lo registra como:

```text
CLIENT_INPUT
```

No se afirma que ese archivo sea un producto oficial del Estado; es un insumo del proyecto.

### SERNANP

El modo `--sernanp auto` intenta descargar:

- ANP Nacional Definitiva;
- Zonas Reservadas.

Si funciona, las celdas interiores se eliminan del grafo navegable. Si falla, el pipeline puede continuar, pero la auditoría registra claramente que la máscara oficial no fue aplicada.

El modo:

```bash
--sernanp estricto
```

obliga a detener la ejecución si SERNANP no puede materializarse.

## Datos simulados

### Modo demo

Con:

```bash
--demo
```

la superficie de probabilidad es artificial y queda marcada como:

```text
SIMULATED_DEMO
```

### Movimiento de embarcaciones

Las trayectorias y la animación GIF siempre son **salidas simuladas del modelo**. No corresponden a AIS, SISESAT ni otra reconstrucción histórica.

## Flota homogénea

El experimento considera:

- 15 agentes;
- 5 con origen Malabrigo;
- 5 con origen Chimbote;
- 5 con origen Callao;
- misma capacidad, velocidad y función de combustible.

Esto es una hipótesis experimental del TDR, no una afirmación de que una empresa real opere exactamente 15 naves idénticas.

## Ruteo

Las rutas se calculan con A* sobre una grilla de celdas válidas.

Si SERNANP está aplicado:

```text
nodo navegable = celda válida AND fuera de exclusión SERNANP
```

La distancia se calcula en millas náuticas mediante Haversine.

## Optimización

### Greedy

Asignación secuencial basada en:

- alta probabilidad;
- bajo combustible;
- penalización por ocupación de zona.

### MILP

Optimización simultánea de toda la flota bajo:

- una zona por barco;
- máximo experimental de barcos por zona;
- costo distancia/combustible.

MILP funciona como benchmark determinístico centralizado.

## Costos

Para cada barco:

```text
distancia_total = distancia_salida + distancia_retorno
horas_salida = distancia_salida / velocidad_salida
horas_retorno = distancia_retorno / velocidad_retorno
combustible_total = combustible_salida + combustible_retorno
costo_combustible = combustible_total × precio_combustible
costo_operativo = horas_total × costo_operativo_hora
costo_total = costo_combustible + costo_operativo
```

El precio de combustible y el costo operativo por hora son **parámetros de escenario**. No deben presentarse como costos observados del cliente salvo que sean reemplazados por datos reales.

## Métricas

Se reportan:

- probabilidad media de zonas asignadas;
- distancia total;
- combustible total;
- costo total;
- cantidad de zonas usadas;
- ocupación máxima;
- costos por puerto;
- trade-off distancia/probabilidad.

## Mapas y simulación

El pipeline genera:

- mapa de probabilidad y zonas candidatas;
- mapa Greedy;
- mapa MILP;
- gráficos de costos y combustible;
- gráfico de ocupación;
- gráfico de trade-off;
- simulación GIF.

## Límite sobre captura

`Prob` no se convierte directamente en toneladas.

La relación correcta requeriría algo como:

```text
E[Captura] = P(Presencia) × E[Captura | Presencia, Ambiente]
```

Para ello hacen falta CPUE, biomasa acústica o registros equivalentes.

## Extensión futura

La arquitectura permite añadir posteriormente:

- MAPPO;
- MAPPO + GAT;
- Copernicus;
- SISESAT;
- batimetría;
- cierres temporales PRODUCE;
- CPUE/biomasa.

Estas extensiones no son necesarias para que el núcleo actual funcione.
