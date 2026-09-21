# Resultados ampliados

Esta carpeta complementa el TDR con un notebook y una vista HTML para revisar mapas, gráficos, asignaciones y simulación.

## Fuente de datos

Todo se genera a partir de `MapProbabilidad_adulto.csv`, ubicado en la raíz del repositorio.

No existe fallback a una grilla demo, sintética o suavizada.

## Flujo recomendado

```bash
python scripts/run_pipeline.py --sernanp no
python docs/tdr/generar_figuras.py
```

Los resultados numéricos quedan en `outputs/` y las figuras del informe en `docs/tdr/figures/`.

## Importante

- La superficie de probabilidad proviene directamente del CSV base.
- Las rutas y el movimiento de barcos son salidas simuladas del modelo.
- No se dibujan exclusiones regulatorias ficticias; si SERNANP no se aplica, la auditoría lo deja explícito.