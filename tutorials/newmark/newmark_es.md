---
abstract: |
  Nathan Mortimore Newmark fue el ingeniero estructural que
  le dio forma matemática a la respuesta dinámica de las
  estructuras frente a sismos. Formó cuatro décadas de
  doctorandos en la Universidad de Illinois en
  Urbana-Champaign, diseñó la Torre Latinoamericana de la
  Ciudad de México que sobrevivió el terremoto de 1957 sin
  daño estructural, formuló el método de integración temporal
  que lleva su nombre y, junto a Emilio Rosenblueth, escribió
  el libro que fundó la ingeniería sísmica como disciplina
  académica. Este documento reconstruye su trayectoria como
  persona, profesional y profesor, y delinea el alcance de
  su legado.
bibliography: newmark.bib
cover: true
csl: ieee
logo: epy_reports.png
watermark: epy_reports.png
date: 2026-06-15
author: Ing. Angel Navarro-Mora M.Sc.
footer: "Nathan M. Newmark (1910–1981) — ANM Ingeniería"
lang: es
page-numbers: true
page-size: letter
subtitle: Vida, obra y legado del fundador de la ingeniería sísmica moderna
title: Nathan M. Newmark (1910–1981)
---

[[section-roman]]

[[toc]]

[[lof]]

[[lot]]

[[loe]]

[[section-arabic]]

::: {.disclosure}
Este documento es un ejemplo ilustrativo preparado con asistencia de IA; revise su contenido antes de utilizarlo.
:::

::: {.callout-note title="Sobre este ejemplo"}
Este informe es un ejemplo de **epy_reports**, parte de la suite de documentos
ePy (código abierto). Su fuente —y los ejemplos hermanos de epy_slides y
epy_papers— están en GitHub:

- Informe Newmark (epy_reports):
  <https://github.com/estructuraPy/epy_reports/tree/main/tutorials/newmark>
- Presentación Empire State (epy_slides):
  <https://github.com/estructuraPy/epy_slides/tree/main/examples/empire_state_building>
- Artículo Puente de Brooklyn (epy_papers):
  <https://github.com/estructuraPy/epy_papers/tree/main/examples/brooklyn_bridge>
:::

# Introducción {#sec-intro}


A principios del siglo XX, las ciudades enfrentaban los sismos casi sin defensa técnica. Los terremotos se interpretaban como catástrofes caprichosas; las estructuras buscaban resistir por rigidez bruta, una estrategia que el suelo desmentía con cada evento. Nathan Mortimore Newmark (1910–1981) lideró el cambio de paradigma: del muro rígido a la **estructura dinámica resiliente**, capaz de **gestionar la energía** del movimiento en lugar de oponerse a él. Como *Padre de la Ingeniería Sísmica* [@vargas2021newmark], su obra no solo evitó colapsos: devolvió a la humanidad la confianza para habitar verticalmente un planeta en vibración constante.[^fn-1]

Antes de Newmark, *diseño sísmico* significaba aplicar un coeficiente lateral estático del 8 al 10 % del peso a la estructura y verificar resistencia elástica. Después de Newmark, el diseño sísmico pasó a apoyarse en el espectro de respuesta, en integración temporal de la ecuación dinámica del movimiento, en la ductilidad como recurso de diseño y en la verificación de derivas. Esa transición no fue gradual ni anónima: está sostenida por cuarenta años de publicaciones de una sola persona y de su escuela en Urbana [@hall1991memoir].


El recorrido continúa por su formación y vida personal en @sec-formacion, su práctica profesional en @sec-profesional, su labor docente en @sec-profesor, el método β en @sec-metodo, otros aportes en @sec-otros, los reconocimientos en @sec-reconocimientos y el legado vivo en @sec-legado.


::: {.callout-important title="Por qué importa"}
La integración temporal del método β y el espectro de respuesta de @newmarkHall1982 son la base computacional de prácticamente todo software de análisis estructural moderno (SAP2000, ETABS, OpenSees, ANSYS, ABAQUS). Cuando un ingeniero corre un *time-history* hoy, está ejecutando un algoritmo escrito por Newmark en 1959.
:::


[^fn-1]: La denominación "Padre de la Ingeniería Sísmica" es de uso extendido en la comunidad académica hispanohablante; en la literatura técnica anglosajona se prefiere "founder of earthquake engineering as an academic discipline" [@hall1991memoir].


[[pagebreak]]

# Vida y formación {#sec-formacion}


![Nathan M. Newmark (1910–1981). Retrato del archivo de la Universidad de Illinois Urbana-Champaign. Fuente: Wikimedia Commons.](newmark_portrait.jpg){#fig-portrait width=40%}

El hombre del retrato de @fig-portrait nació el 22 de septiembre de 1910 en Plainfield, Nueva Jersey, hijo de Abraham S. Newmark y Mollie Nathanson [@hall1991memoir]. Su talento matemático se manifestó temprano: a los 19 años ya había terminado su licenciatura en ingeniería civil en la Universidad de Rutgers (1930), con múltiples honores y premios especiales que lo ubicaron como el mejor de su promoción.

Su madurez técnica se consolidó en la Universidad de Illinois en Urbana-Champaign (UIUC), bajo la tutela de tres figuras legendarias: **Hardy Cross** (autor del método de distribución de momentos), **Harold M. Westergaard** y **Frank E. Richart** [@hall1991memoir]. Obtuvo su maestría en 1932 y el doctorado en 1934, ambos en Urbana. Su ascenso fue meteórico: en 1943, a los 33 años, fue nombrado *Research Professor* **saltándose el rango intermedio de profesor asociado** — un hito administrativo casi inaudito en la academia estadounidense.

En el ámbito personal, su vida estuvo anclada por su esposa **Anne May Cohen** (matrimonio en 1931) y sus tres hijos, Richard, Linda y Susan. Permaneció en Urbana toda su carrera profesional: cuarenta y tres años en la facultad de ingeniería civil, hasta su retiro formal en 1976. Murió el 25 de enero de 1981, a los 70 años, poco después de haber comenzado a escribir, junto con William J. Hall, el libro póstumo *Earthquake Spectra and Design* [@newmarkHall1982].


::: {.callout-note}
Es inusual que un ingeniero de su estatura haya pasado toda su carrera en una sola institución. Recibió ofertas constantes de Berkeley, Stanford, MIT y Caltech; las declinó todas. Urbana era, en sus palabras, *el lugar donde puedo trabajar sin distracciones*.
:::


[[pagebreak]]

# Trayectoria profesional {#sec-profesional}


Aunque académico de carrera, Newmark mantuvo una práctica consultora intensa que alimentó su investigación con casos reales — desde el conflicto bélico hasta la infraestructura civil más crítica del hemisferio occidental.


## Servicio bélico y defensa {#sec-guerra}


Durante la Segunda Guerra Mundial, Newmark sirvió como consultor del *National Defense Research Committee* (NDRC) y de la *Office of Scientific Research and Development* (OSRD), parte de su servicio en la Zona de Guerra del Pacífico [@hall1991memoir]. Más adelante contribuyó al desarrollo de los sistemas balísticos **Minute Man** y **MX**, diseñando los silos enterrados resistentes a explosión nuclear cercana. Por estas contribuciones estratégicas, el presidente Truman le entregó en 1948 el *President's Certificate of Merit*.


## La Torre Latinoamericana {#sec-torre}


El proyecto de consultoría más célebre de Newmark fue la Torre Latinoamericana en la Ciudad de México (1956). Junto con Adolfo Zeevaert y Leonardo Zeevaert, diseñó la primera estructura alta del mundo concebida explícitamente para resistir un sismo de magnitud 7.5 sobre un suelo lacustre de baja capacidad portante. La estrategia combinó:

1. Fundación tipo cajón flotante con 361 pilotes de fricción.
2. Marco rígido de acero estructural con columnas de doble cajón.
3. Periodo fundamental sintonizado para evitar la región amplificada del espectro del suelo blando.

El 28 de julio de 1957 un terremoto de magnitud 7.7 con epicentro en Guerrero golpeó la Ciudad de México. Varios edificios se colapsaron. La Torre Latinoamericana, ocupada y operativa, no sufrió **ni un solo daño estructural**. El sismo de magnitud 8.0 de 1985, que devastó decenas de edificios, tampoco la afectó.


## Infraestructura crítica {#sec-encargos}


- **Sistema BART** (Bay Area Rapid Transit), San Francisco — criterios sísmicos de diseño del sistema de tránsito rápido que conecta el norte de California sobre la zona de fallas más activa de Estados Unidos [@hall1991memoir].
- **Oleoducto Trans-Alaska** — diseño sísmico del que en su momento fue el mayor proyecto privado de infraestructura del mundo, atravesando 1\,287 km y tres sistemas de fallas activas [@hall1991memoir].
- **Fundación de la Torre Sears** (hoy Willis Tower), Chicago, 1970 — consultoría sobre interacción suelo-estructura.
- **~70 plantas de energía nuclear** (Atomic Energy Commission) más múltiples instalaciones de **gas natural licuado (GNL)** durante sus últimos diecisiete años de carrera [@hall1991memoir]. Su criterio de diseño *Safe Shutdown Earthquake* todavía sobrevive en la regulación nuclear.


[[pagebreak]]

# El profesor {#sec-profesor}


Lo que distinguió a Newmark del resto de los académicos de su generación fue su intensidad como mentor doctoral. Entre 1934 y 1976 supervisó a más de cincuenta doctorandos. Buena parte de la ingeniería estructural moderna se entiende como una rama del árbol genealógico académico de Newmark:


| Estudiante / colaborador | Aporte principal |
| --- | --- |
| Anestis S. Veletsos | Comportamiento inelástico [@veletsosNewmark1960] |
| Mete Sözen | Diseño sismo-resistente de hormigón armado |
| William J. Hall | Espectros de diseño [@newmarkHall1982] |
| William C. Schnobrich | Análisis de placas y cáscaras |
| Anil K. Chopra | Dinámica estructural moderna [@chopra2017dynamics] |
| Emilio Rosenblueth | Coautor del primer texto sísmico [@newmarkRosenblueth1971] |

: Algunos discípulos de Newmark y su aporte principal. {#tbl-discipulos}


@tbl-discipulos lista apenas una fracción de su descendencia académica. El curso *CE 472 — Structural Dynamics*, que Newmark dictó durante más de tres décadas en Urbana, formó a generaciones enteras de ingenieros sísmicos en cuatro continentes.

Newmark fue también pionero de la **computación científica** aplicada a la ingeniería estructural. Entre 1947 y 1957 presidió el *Digital Computer Laboratory* de la UIUC, donde tuvo un papel decisivo en el desarrollo de la **ILLIAC-II**, una de las primeras computadoras digitales a gran escala del mundo [@hall1991memoir]. Ese esfuerzo posicionó a la universidad como líder mundial en la aplicación de la computación al análisis dinámico de estructuras — la base instrumental que diez años después haría posible el método β. Como jefe del Departamento de Ingeniería Civil entre 1956 y 1973, elevó la institución a un prestigio internacional sin precedentes.


::: {.callout-tip title="Su estilo de enseñanza"}
Hall lo recuerda así: *Nathan no enseñaba fórmulas; enseñaba a derivarlas. Si un estudiante llegaba a su oficina con una pregunta sobre el método β, se iba dos horas después con seis páginas de álgebra a mano y la convicción de que él mismo lo había deducido.*
:::


[[pagebreak]]

# El método β {#sec-metodo}


En 1959 Newmark publicó en el *Journal of the Engineering Mechanics Division* de la ASCE un artículo de 28 páginas que cambió el análisis dinámico para siempre: *A Method of Computation for Structural Dynamics* [@newmark1959method]. Propuso una familia de algoritmos de integración temporal de un solo paso, controlados por dos parámetros $\beta$ y $\gamma$, capaces de pasar de explícitos a implícitos cambiando un solo número.


## Formulación {#sec-formulacion}


Considere el sistema con un grado de libertad de la @fig-sdof, con masa $m$, rigidez $k$, amortiguamiento $c$ y excitación por aceleración del suelo $\ddot u_{g}(t)$.


![Sistema masa-resorte-amortiguador (SDOF) sometido a una aceleración del suelo $\ddot u_{g}(t)$.](sdof.svg){#fig-sdof width=55%}

La ecuación de movimiento de la @fig-sdof es


$$
m\,\ddot u(t) + c\,\dot u(t) + k\,u(t) = -\,m\,\ddot u_{g}(t)
$$ {#eq-eom}

Newmark planteó la solución temporal mediante aproximaciones truncadas en serie de Taylor para la velocidad y el desplazamiento en el paso $n+1$:[^fn-2]


$$
\dot u_{n+1} \;=\; \dot u_{n} + \Delta t\,\bigl[ (1-\gamma)\,\ddot u_{n} + \gamma\,\ddot u_{n+1} \bigr]
$$ {#eq-vel}

$$
u_{n+1} \;=\; u_{n} + \Delta t\,\dot u_{n} + \frac{\Delta t^{2}}{2}\,\bigl[ (1-2\beta)\,\ddot u_{n} + 2\beta\,\ddot u_{n+1} \bigr]
$$ {#eq-disp}

@eq-vel y @eq-disp definen la familia β. La aceleración en $n+1$ se obtiene sustituyendo en @eq-eom y resolviendo un sistema lineal en $\ddot u_{n+1}$.


[^fn-2]: La derivación completa, con prueba de consistencia y estimación de error de truncamiento, se encuentra en el artículo original [@newmark1959method, pp. 67–94].


## Variantes clásicas {#sec-variantes}


Tres elecciones de $(\beta, \gamma)$ son universalmente conocidas:


| Variante | β | γ | Tipo | Estabilidad |
| --- | --- | --- | --- | --- |
| Aceleración promedio | 1/4 | 1/2 | Implícito | Incondicionalmente estable |
| Aceleración lineal | 1/6 | 1/2 | Implícito | Estable si $\Delta t / T \leq 0.551$ |
| Diferencia central | 0 | 1/2 | Explícito | Estable si $\Delta t / T \leq 1/\pi$ |
| Backward difference | 1/2 | 1 | Implícito | Estable, alta disipación numérica |

: Variantes clásicas del método β. {#tbl-variantes}


@tbl-variantes resume el compromiso esencial: la aceleración promedio preserva exactamente la energía pero distorsiona la fase; la aceleración lineal tiene mejor precisión en fase pero exige pasos finos; la diferencia central es explícita —no requiere resolver ningún sistema lineal— pero su límite de estabilidad la vuelve costosa para sistemas con altas frecuencias.


![Hipótesis de variación de la aceleración $\ddot u(t)$ entre $t_{n}$ y $t_{n+1} = t_{n} + \Delta t$. El parámetro $\beta$ codifica la forma asumida del integrando: $\beta = 1/6$ corresponde a variación lineal, $\beta = 1/4$ a un promedio constante y $\beta = 1/8$ a una aproximación escalonada.](beta_assumptions.svg){#fig-beta width=75%}

@fig-beta expone el significado físico de $\beta$: no es un número cualquiera, sino la elección de la forma asumida para la aceleración entre dos pasos consecutivos. Distintos $\beta$ corresponden a distintas reglas de integración numérica de $\ddot u(t)$ en $[t_{n},\, t_{n+1}]$. La estabilidad incondicional se obtiene cuando $2\beta \geq \gamma \geq 1/2$.


## Implementación de referencia {#sec-codigo}


La estructura algorítmica de un paso del método β para un SDOF lineal es compacta:


```python
"""Newmark-beta step for a linear SDOF system."""

def newmark_step(m, c, k, u, v, a, p_next, dt, beta=0.25, gamma=0.5):
    """Advance (u, v, a) by one step under load p_next."""
    k_eff = k + gamma / (beta * dt) * c + m / (beta * dt ** 2)
    A = m / (beta * dt ** 2) + gamma / (beta * dt) * c
    B = m / (beta * dt) + (gamma / beta - 1.0) * c
    C = m * (0.5 / beta - 1.0) + dt * c * (0.5 * gamma / beta - 1.0)
    u_next = (p_next + A * u + B * v + C * a) / k_eff
    v_next = (
        gamma / (beta * dt) * (u_next - u)
        + (1.0 - gamma / beta) * v
        + dt * (1.0 - 0.5 * gamma / beta) * a
    )
    a_next = (
        (u_next - u) / (beta * dt ** 2)
        - v / (beta * dt)
        - (0.5 / beta - 1.0) * a
    )
    return u_next, v_next, a_next
```


Este patrón —reescribir el sistema dinámico como una ecuación pseudo-estática con rigidez efectiva $k^{*}$ y carga efectiva $p^{*}$— es la forma canónica que aparece en todos los textos modernos [@chopra2017dynamics; @bathe2014fem].


[[pagebreak]]

# Otros aportes {#sec-otros}


::: {.callout-warning title="Más que el método β"}
Reducir la obra de Newmark al método β es injusto. Sus contribuciones posteriores en sismología aplicada y mecánica de suelos fueron igualmente decisivas.
:::


## Método del bloque deslizante (1965) {#sec-bloque}


En la *Fifth Rankine Lecture* [@newmark1965sliding] Newmark introdujo un modelo simple para estimar el desplazamiento permanente inducido por un sismo sobre una masa de suelo o estructura potencialmente deslizante. La idea: integrar dos veces, durante los intervalos en que la aceleración del registro excede el valor crítico $a_{c}$, la ecuación


$$
\ddot d(t) = \ddot u_{g}(t) - a_{c}\,\operatorname{sgn}\!\bigl( \dot d(t) \bigr)
$$ {#eq-bloque}

@eq-bloque sigue siendo, sesenta años después, la base normativa para la verificación sísmica de presas, taludes y muros de contención en prácticamente todos los códigos del mundo. Su vigencia se manifiesta en estudios recientes sobre los deslizamientos de **Bullas (2002)** y **La Paca (2005)** en Murcia, España [@rodriguezPeces2011newmark]. El mismo trabajo señala una lección operativa: las evaluaciones a escala regional (píxeles de 25 m) producen estimaciones incorrectas o nulas, mientras que los análisis a 2.5 m por píxel identifican con exactitud las áreas de ruptura — argumento decisivo a favor de los **mapas de desplazamiento de alta resolución** como producto normativo.


## Espectro Newmark-Hall {#sec-espectro}


Con William J. Hall, Newmark consolidó el concepto de **espectro suavizado de diseño**: dada una aceleración pico del terreno (PGA), una velocidad pico (PGV) y un desplazamiento pico (PGD), se obtienen tres regiones del espectro (aceleración, velocidad y desplazamiento constante) ajustadas por factores empíricos que dependen del amortiguamiento. El espectro Newmark-Hall apareció en su forma canónica en [@newmarkHall1982] y dominó la práctica del diseño sísmico durante tres décadas.


## Diseño basado en ductilidad {#sec-ductilidad}


Newmark formalizó las dos hipótesis fundamentales del diseño dúctil:

- **Igual desplazamiento** (períodos largos $T > T_{c}$): el desplazamiento máximo del sistema inelástico es igual al del sistema elástico de la misma rigidez inicial.
- **Igual energía** (períodos intermedios): la energía absorbida por el sistema inelástico iguala a la del sistema elástico.

Ambas, derivadas de simulaciones con @veletsosNewmark1960, son el fundamento del concepto moderno de **factor de reducción de respuesta R** que aparece en el ASCE 7, el Eurocódigo 8 y la mayoría de los códigos sísmicos.


[[pagebreak]]

# Reconocimientos {#sec-reconocimientos}


- ***President's Certificate of Merit*** (1948), entregado por Harry S. Truman, por su servicio a la NDRC y la OSRD durante la Segunda Guerra Mundial [@hall1991memoir].
- Miembro **fundador** de la **National Academy of Engineering** (1964), en el primer grupo de elegidos al constituirse la academia [@hall1991memoir].
- **National Medal of Science** (1968), entregada por Lyndon B. Johnson, *por su liderazgo en la creación de la ingeniería estructural moderna basada en mecánica racional*.
- *John von Neumann Lecture* (1969), American Society of Mechanical Engineers.
- *Foreign Member of the Royal Society* (1975).
- **Gold Medal de la Institution of Structural Engineers** del Reino Unido (1980): apenas **el segundo ingeniero estadounidense en los 57 años de historia de la institución** en recibirla [@hall1991memoir].
- **Norman Medal** de la ASCE en cinco ocasiones (un récord absoluto histórico).
- Doctorados *honoris causa* de Princeton, Lehigh, Notre Dame, Liège y ocho universidades adicionales.


# Legado {#sec-legado}


::: {.callout-caution title="Disciplina, no caja de herramientas"}
La ingeniería sísmica como disciplina académica con currículum propio, doctorandos propios y revistas propias no existía antes de Newmark. Cuando murió en 1981, ya era impensable diseñar una estructura crítica sin la maquinaria conceptual que él había construido.
:::


**Tres semanas después** de su muerte en 1981, la UIUC renombró su edificio de ingeniería civil como **Newmark Civil Engineering Laboratory** [@hall1991memoir]. Es el edificio donde se forman cada año cerca de cien doctorandos de ingeniería estructural.

La *EERI Distinguished Lecture* lleva su nombre desde 1985 y se otorga anualmente al ingeniero o investigador con la contribución más significativa a la ingeniería sísmica del año anterior.

Sus dos libros, *Fundamentals of Earthquake Engineering* [@newmarkRosenblueth1971] y *Earthquake Spectra and Design* [@newmarkHall1982], se siguen citando, vendiendo y prescribiendo como bibliografía obligatoria en cursos de maestría y doctorado a lo largo del mundo. El segundo, publicado un año después de su muerte, fue completado por William J. Hall a partir de manuscritos y notas de clase que el propio Newmark había dejado preparadas.

Como resume @hall1991memoir en su *Biographical Memoir* para la National Academy of Sciences, Newmark fue *"una universidad en sí mismo"* — un hombre cuya intuición técnica se equilibraba con un interés genuino por las personas. Hall sintetiza así su legado:

> *"Casi todo ingeniero estructural en ejercicio en algún lugar del mundo usa diariamente, sin saberlo, una idea de Nathan Newmark. Esa es, probablemente, la forma más honesta de medir su legado."*


[[pagebreak]]

# Referencias {.unnumbered}


::: {#refs}
:::
