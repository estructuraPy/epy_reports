---
title: Informe de diseño estructural
subtitle: Ejemplo de trabajo
author: Ing. Angel Navarro-Mora M.Sc.
date: 2026-11-09
lang: es
page-size: A4
---

# Resumen

Este ejemplo sigue un informe breve desde los valores de los materiales
hasta el plano de construcción. Edítelo, expórtelo o úselo como plantilla
para su propio proyecto.

# Materiales

Las resistencias características usadas en este informe:

:::: {.stats}
::: {.stat}
**28 MPa**

[f'c del concreto]{.stat-label}
:::
::: {.stat}
**420 MPa**

[fy del acero]{.stat-label}
:::
::::

| Elemento | Sección | Material |
| -------- | ------- | -------- |
| Viga B-1 | 300 × 600 mm | Concreto reforzado |
| Columna C-1 | 400 × 400 mm | Concreto reforzado |

# Flujo de diseño

```mermaid
flowchart LR
    A[Cargas] --> B[Análisis]
    B --> C[Diseño]
    C --> D[Planos]
```

::: {.callout-note title="Revisión"}
El revisor independiente firma el informe de cálculo antes de que los
planos se emitan para construcción.
:::

# Siguiente paso

Exporte el informe a PDF y adjúntelo al expediente de cálculo.
