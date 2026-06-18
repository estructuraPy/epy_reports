---
title: Sample Report — Steel Beam Check
subtitle: A starting point you can adapt
author: Your Name
date: 2026-06-18
lang: en
page-size: letter
cover: true
footer: "Sample document — epy_mdr"
page-numbers: true
---

# Introduction {#sec-intro}

This is a **sample document**. Open it, edit it, and export it with
`Ctrl+P` to see how epy_mdr lays out a real report. It exercises the most
common elements; the full reference lives in the *Welcome* tab.

The demand check is summarized in @tbl-loads and computed with @eq-moment.

# Loads {#sec-loads}

| Case | Description | Value (kN/m) |
| --- | --- | ---: |
| D | Dead load | 12.0 |
| L | Live load | 18.0 |
| w | Factored `1.2D + 1.6L` | 43.2 |

: Service and factored loads. {#tbl-loads}

# Demand {#sec-demand}

For a simply supported span $L = 6.0\ \text{m}$, the maximum moment is

$$
M_u = \frac{w_u L^2}{8}
$$ {#eq-moment}

::: {.callout-note title="Assumption"}
The beam is laterally braced, so lateral-torsional buckling does not
govern. Use $\phi_b = 0.90$ for flexure (AISC 360).
:::

A quick check in Python:

```python
wu, L = 43.2, 6.0          # kN/m, m
Mu = wu * L**2 / 8         # kN·m
print(f"Mu = {Mu:.1f} kN·m")   # 194.4 kN·m
```

The result governs the section selection.[^fn-phi]

[^fn-phi]: The resistance factor $\phi_b = 0.90$ already accounts for
    flexural strength uncertainty, so no extra factor is applied here.

# Checklist {#sec-check}

- [x] Loads defined
- [x] Demand computed
- [ ] Section selected
- [ ] Deflection verified
