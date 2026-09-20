# Guía de resultados y análisis

Este documento explica qué produce el pipeline y cómo interpretar cada salida.

## 1. Auditoría primero

Archivo:

```text
outputs/auditoria.json
```

Antes de interpretar cualquier gráfico revisa:

- `procedencia_probabilidad`
- `probabilidad_simulada`
- `rutas_y_movimiento_simulados`
- `sernanp.aplicado`
- parámetros económicos de escenario

### Lectura correcta

Si aparece:

```text
CLIENT_INPUT
```

la superficie de probabilidad proviene del archivo del proyecto.

Si aparece:

```text
SIMULATED_DEMO
```

la superficie fue generada únicamente para demostración.

En ambos casos las rutas y el movimiento de los barcos son decisiones simuladas del optimizador.

## 2. Mapa de probabilidad y zonas

Archivo:

```text
mapa_probabilidad_zonas.png
```

Permite revisar:

- dónde se concentra la probabilidad alta;
- qué puntos fueron seleccionados como zonas candidatas;
- relación espacial entre puertos y zonas.

## 3. Mapas de asignación

Archivos:

```text
mapa_asignacion_greedy.png
mapa_asignacion_milp.png
```

Sirven para comparar la lógica espacial de los dos métodos.

### Greedy

Decide de forma secuencial. Una decisión temprana puede afectar a los barcos posteriores.

### MILP

Optimiza simultáneamente la asignación de los 15 barcos bajo las restricciones del modelo.

## 4. Tabla de costos de rutas

Archivo:

```text
costos_rutas.csv
```

Cada fila representa una combinación:

```text
puerto × zona
```

e incluye:

- probabilidad;
- distancia de salida;
- distancia de retorno;
- distancia total;
- horas;
- combustible;
- costo de combustible;
- costo operativo;
- costo total.

## 5. Costos por barco

Archivo:

```text
costos_por_barco.csv
```

Permite detectar:

- embarcaciones con rutas muy largas;
- zonas costosas para ciertos puertos;
- heterogeneidad de costo causada exclusivamente por la asignación, ya que la flota es homogénea.

## 6. Costos por puerto

Archivo:

```text
costos_por_puerto.csv
```

Resume el esfuerzo agregado de los cinco barcos de cada puerto.

Es útil para responder:

- ¿qué puerto soporta más distancia?
- ¿qué puerto consume más combustible?
- ¿qué puerto tiene mayor costo total?
- ¿qué probabilidad media logra cada grupo?

## 7. Comparación de métodos

Archivo:

```text
resumen_metodos.csv
```

Comparar:

- probabilidad media;
- distancia total;
- combustible total;
- costo total;
- zonas usadas;
- ocupación máxima.

No existe un único indicador universal. La interpretación debe considerar el compromiso entre oportunidad pesquera y costo.

## 8. Trade-off distancia vs probabilidad

Archivo:

```text
grafico_distancia_vs_probabilidad.png
```

Cuadrantes conceptuales:

- alta probabilidad / baja distancia: zonas atractivas;
- alta probabilidad / alta distancia: oportunidad con costo;
- baja probabilidad / baja distancia: alternativa conservadora;
- baja probabilidad / alta distancia: asignación poco atractiva.

## 9. Ocupación de zonas

Archivo:

```text
grafico_ocupacion_zonas.png
```

Permite revisar si la flota se concentra excesivamente.

El máximo de barcos por zona usado por el modelo es una **restricción experimental de coordinación**, no una norma pesquera oficial.

## 10. Simulación animada

Archivo:

```text
simulacion_flota.gif
```

La animación sirve para comunicar:

- salidas desde tres puertos;
- coordinación de la flota;
- direcciones de navegación;
- zonas finales asignadas.

No debe presentarse como un track histórico.

## 11. Costos económicos

El modelo calcula:

```text
Costo_combustible = Litros_totales × Precio_combustible
```

y:

```text
Costo_total = Costo_combustible + Horas_totales × Costo_operativo_hora
```

Por defecto:

- el precio del combustible es un parámetro de escenario;
- el costo operativo adicional por hora es 0 para evitar inventar tripulación, mantenimiento o seguros.

Si cuentas con costos reales, reemplaza los parámetros en la ejecución.

## 12. Qué no debe afirmarse

No afirmar:

```text
Prob = 0.80 => 400 toneladas
```

La probabilidad no es biomasa.

Para estimar toneladas sería necesario añadir:

- CPUE;
- biomasa acústica;
- capturas históricas comparables;
- o un modelo de captura condicional.

## 13. Resultado demo en GitHub

GitHub Actions ejecuta automáticamente el modo demo.

Los archivos generados se publican como artifact:

```text
resultados-demo-anchoveta
```

Ese artifact contiene mapas, tablas, GIF y reporte HTML.

Todo lo que proviene del modo demo debe interpretarse como **resultado de simulación**, no como evidencia empírica.
