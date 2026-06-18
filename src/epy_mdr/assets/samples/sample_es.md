---
title: Informe de ejemplo — Revisión de viga
subtitle: Un punto de partida que podés adaptar
author: Tu Nombre
date: 2026-06-18
lang: es
page-size: letter
cover: true
footer: "Documento de ejemplo — epy_mdr"
page-numbers: true
---

# Introducción {#sec-intro}

Este es un **documento de ejemplo**. Abrilo, editalo y exportalo con
`Ctrl+P` para ver cómo epy_mdr arma un informe real. Ejercita los
elementos más comunes; la referencia completa está en la pestaña
*Welcome*.

La verificación de demanda se resume en @tbl-loads y se calcula con
@eq-moment.

# Cargas {#sec-cargas}

| Caso | Descripción | Valor (kN/m) |
| --- | --- | ---: |
| D | Carga muerta | 12.0 |
| L | Carga viva | 18.0 |
| w | Mayorada `1.2D + 1.6L` | 43.2 |

: Cargas de servicio y mayoradas. {#tbl-loads}

# Demanda {#sec-demanda}

Para un tramo simplemente apoyado de $L = 6.0\ \text{m}$, el momento
máximo es

$$
M_u = \frac{w_u L^2}{8}
$$ {#eq-moment}

::: {.callout-note title="Hipótesis"}
La viga está arriostrada lateralmente, por lo que el pandeo lateral-
torsional no gobierna. Use $\phi_b = 0.90$ para flexión (AISC 360).
:::

Una verificación rápida en Python:

```python
wu, L = 43.2, 6.0          # kN/m, m
Mu = wu * L**2 / 8         # kN·m
print(f"Mu = {Mu:.1f} kN·m")   # 194.4 kN·m
```

El resultado gobierna la selección de la sección.[^fn-phi]

[^fn-phi]: El factor de resistencia $\phi_b = 0.90$ ya considera la
    incertidumbre de la resistencia a flexión, así que no se aplica un
    factor adicional aquí.

# Lista de verificación {#sec-check}

- [x] Cargas definidas
- [x] Demanda calculada
- [ ] Sección seleccionada
- [ ] Deflexión verificada
