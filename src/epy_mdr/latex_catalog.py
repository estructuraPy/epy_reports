"""Catalog of LaTeX math snippets, grouped by category.

Each entry exposes:

- ``label``   — the short text shown on the palette button (Unicode
  symbol or a 1-3 character mnemonic).
- ``latex``   — the LaTeX source inserted at the editor caret when
  the user clicks the button. The caret is left at the end of the
  insertion; placeholders are deliberately bare so the user types
  the actual content.
- ``tooltip`` — the description shown on hover, in Spanish.

The catalog is split into eight categories that together cover the
mathematical needs of structural / civil engineering and most
applied-math writing: Greek letters, operators and relations,
calculus, structure, matrices and vectors, sets and logic, common
functions, and engineering decorations (tensors, hats, dots).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LatexEntry:
    """One palette entry: button label, LaTeX source, tooltip."""

    label: str
    latex: str
    tooltip: str


CATALOG: dict[str, list[LatexEntry]] = {
    "Letras griegas (minúsculas)": [
        LatexEntry("α", r"\alpha",   "alfa"),
        LatexEntry("β", r"\beta",    "beta"),
        LatexEntry("γ", r"\gamma",   "gamma"),
        LatexEntry("δ", r"\delta",   "delta"),
        LatexEntry("ε", r"\epsilon", "epsilon"),
        LatexEntry("ϵ", r"\varepsilon", "varepsilon"),
        LatexEntry("ζ", r"\zeta",    "zeta"),
        LatexEntry("η", r"\eta",     "eta"),
        LatexEntry("θ", r"\theta",   "theta"),
        LatexEntry("ϑ", r"\vartheta", "vartheta"),
        LatexEntry("ι", r"\iota",    "iota"),
        LatexEntry("κ", r"\kappa",   "kappa"),
        LatexEntry("λ", r"\lambda",  "lambda"),
        LatexEntry("μ", r"\mu",      "mu"),
        LatexEntry("ν", r"\nu",      "nu"),
        LatexEntry("ξ", r"\xi",      "xi"),
        LatexEntry("π", r"\pi",      "pi"),
        LatexEntry("ϖ", r"\varpi",   "varpi"),
        LatexEntry("ρ", r"\rho",     "rho"),
        LatexEntry("ϱ", r"\varrho",  "varrho"),
        LatexEntry("σ", r"\sigma",   "sigma"),
        LatexEntry("ς", r"\varsigma", "varsigma"),
        LatexEntry("τ", r"\tau",     "tau"),
        LatexEntry("υ", r"\upsilon", "upsilon"),
        LatexEntry("φ", r"\phi",     "phi"),
        LatexEntry("ϕ", r"\varphi",  "varphi"),
        LatexEntry("χ", r"\chi",     "chi"),
        LatexEntry("ψ", r"\psi",     "psi"),
        LatexEntry("ω", r"\omega",   "omega"),
    ],
    "Letras griegas (mayúsculas)": [
        LatexEntry("Γ", r"\Gamma",   "Gamma"),
        LatexEntry("Δ", r"\Delta",   "Delta"),
        LatexEntry("Θ", r"\Theta",   "Theta"),
        LatexEntry("Λ", r"\Lambda",  "Lambda"),
        LatexEntry("Ξ", r"\Xi",      "Xi"),
        LatexEntry("Π", r"\Pi",      "Pi"),
        LatexEntry("Σ", r"\Sigma",   "Sigma"),
        LatexEntry("Υ", r"\Upsilon", "Upsilon"),
        LatexEntry("Φ", r"\Phi",     "Phi"),
        LatexEntry("Ψ", r"\Psi",     "Psi"),
        LatexEntry("Ω", r"\Omega",   "Omega"),
    ],
    "Operadores y relaciones": [
        LatexEntry("±", r"\pm",      "más-menos"),
        LatexEntry("∓", r"\mp",      "menos-más"),
        LatexEntry("×", r"\times",   "producto cruz"),
        LatexEntry("·", r"\cdot",    "punto centrado"),
        LatexEntry("÷", r"\div",     "dividir"),
        LatexEntry("∗", r"\ast",     "asterisco"),
        LatexEntry("⊕", r"\oplus",   "suma directa"),
        LatexEntry("⊗", r"\otimes",  "producto tensorial"),
        LatexEntry("=", "=",         "igual"),
        LatexEntry("≠", r"\neq",     "distinto"),
        LatexEntry("≈", r"\approx",  "aproximadamente"),
        LatexEntry("≡", r"\equiv",   "idéntico"),
        LatexEntry("∼", r"\sim",     "tilde"),
        LatexEntry("≅", r"\cong",    "congruente"),
        LatexEntry("∝", r"\propto",  "proporcional a"),
        LatexEntry("≤", r"\leq",     "menor o igual"),
        LatexEntry("≥", r"\geq",     "mayor o igual"),
        LatexEntry("≪", r"\ll",      "mucho menor"),
        LatexEntry("≫", r"\gg",      "mucho mayor"),
        LatexEntry("→", r"\to",      "flecha derecha"),
        LatexEntry("←", r"\leftarrow", "flecha izquierda"),
        LatexEntry("⇒", r"\Rightarrow", "implica"),
        LatexEntry("⇐", r"\Leftarrow", "implicado por"),
        LatexEntry("⇔", r"\Leftrightarrow", "si y solo si"),
        LatexEntry("↦", r"\mapsto",  "mapea a"),
    ],
    "Cálculo": [
        LatexEntry("∑", r"\sum_{i=1}^{n} ",     "sumatoria"),
        LatexEntry("∏", r"\prod_{i=1}^{n} ",    "productoria"),
        LatexEntry("∫", r"\int_{a}^{b} \, dx",  "integral definida"),
        LatexEntry("∬", r"\iint ",              "integral doble"),
        LatexEntry("∭", r"\iiint ",             "integral triple"),
        LatexEntry("∮", r"\oint ",              "integral cerrada"),
        LatexEntry("lim", r"\lim_{x \to 0} ",    "límite"),
        LatexEntry("∞", r"\infty",              "infinito"),
        LatexEntry("d/dx", r"\frac{d}{dx}",       "derivada total"),
        LatexEntry("∂", r"\partial ",            "símbolo de parcial"),
        LatexEntry("∂/∂x", r"\frac{\partial}{\partial x} ", "derivada parcial"),
        LatexEntry("∂²/∂x²", r"\frac{\partial^{2}}{\partial x^{2}} ", "segunda parcial"),
        LatexEntry("∇", r"\nabla ",              "gradiente"),
        LatexEntry("∇²", r"\nabla^{2} ",         "laplaciano"),
        LatexEntry("∇·", r"\nabla \cdot ",       "divergencia"),
        LatexEntry("∇×", r"\nabla \times ",      "rotacional"),
    ],
    "Estructura": [
        LatexEntry("a/b",    r"\frac{a}{b}",                 "fracción"),
        LatexEntry("√x",     r"\sqrt{x}",                    "raíz cuadrada"),
        LatexEntry("ⁿ√x",    r"\sqrt[n]{x}",                 "raíz n-ésima"),
        LatexEntry("aⁿ",     r"a^{n}",                       "potencia"),
        LatexEntry("aᵢ",     r"a_{i}",                       "subíndice"),
        LatexEntry("aᵢʲ",    r"a_{i}^{j}",                   "sub y super"),
        LatexEntry("(a)",    r"\left( a \right)",            "paréntesis ajustables"),
        LatexEntry("[a]",    r"\left[ a \right]",            "corchetes ajustables"),
        LatexEntry("{a}",    r"\left\{ a \right\}",          "llaves ajustables"),
        LatexEntry("|a|",    r"\left| a \right|",            "valor absoluto"),
        LatexEntry("‖a‖",    r"\left\| a \right\|",          "norma"),
        LatexEntry("⌊a⌋",    r"\left\lfloor a \right\rfloor", "función piso"),
        LatexEntry("⌈a⌉",    r"\left\lceil a \right\rceil",  "función techo"),
        LatexEntry("⟨a⟩",    r"\left\langle a \right\rangle", "Macaulay (paréntesis angulares)"),
        LatexEntry("cases", r"\begin{cases} a & \text{si } x>0 \\ b & \text{si } x \leq 0 \end{cases}", "definición por casos"),
        LatexEntry("align", r"\begin{aligned} a &= b \\ c &= d \end{aligned}", "ecuaciones alineadas"),
        LatexEntry("over", r"\overline{a}",                  "barra superior"),
        LatexEntry("under", r"\underline{a}",                "barra inferior"),
        LatexEntry("over←", r"\overrightarrow{AB}",          "flecha sobre"),
    ],
    "Matrices y vectores": [
        LatexEntry("(A)",    r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}", "matriz con paréntesis"),
        LatexEntry("[A]",    r"\begin{bmatrix} a & b \\ c & d \end{bmatrix}", "matriz con corchetes"),
        LatexEntry("|A|",    r"\begin{vmatrix} a & b \\ c & d \end{vmatrix}", "determinante"),
        LatexEntry("‖A‖",    r"\begin{Vmatrix} a & b \\ c & d \end{Vmatrix}", "norma matricial"),
        LatexEntry("{A}",    r"\begin{Bmatrix} a & b \\ c & d \end{Bmatrix}", "matriz con llaves"),
        LatexEntry("matrix", r"\begin{matrix} a & b \\ c & d \end{matrix}",  "matriz sin delimitadores"),
        LatexEntry("→a",     r"\vec{a}",                                     "vector"),
        LatexEntry("Aᵀ",     r"A^{T}",                                       "transpuesta"),
        LatexEntry("A⁻¹",    r"A^{-1}",                                      "inversa"),
        LatexEntry("A*",     r"A^{*}",                                       "adjunta"),
        LatexEntry("â",      r"\hat{a}",                                     "circunflejo"),
        LatexEntry("ā",      r"\bar{a}",                                     "barra"),
        LatexEntry("ã",      r"\tilde{a}",                                   "tilde"),
        LatexEntry("ȧ",      r"\dot{a}",                                     "punto (1ra derivada temporal)"),
        LatexEntry("ä",      r"\ddot{a}",                                    "doble punto (2da derivada temporal)"),
        LatexEntry("⃛a",     r"\dddot{a}",                                   "triple punto (3ra derivada)"),
        LatexEntry("dim",    r"\dim ",                                        "dimensión"),
        LatexEntry("rank",   r"\operatorname{rank} ",                         "rango"),
        LatexEntry("tr",     r"\operatorname{tr} ",                           "traza"),
        LatexEntry("det",    r"\det ",                                        "determinante (operador)"),
    ],
    "Conjuntos y lógica": [
        LatexEntry("∈",  r"\in",        "pertenece"),
        LatexEntry("∉",  r"\notin",     "no pertenece"),
        LatexEntry("∋",  r"\ni",        "contiene"),
        LatexEntry("⊂",  r"\subset",    "subconjunto estricto"),
        LatexEntry("⊆",  r"\subseteq",  "subconjunto o igual"),
        LatexEntry("⊃",  r"\supset",    "superconjunto"),
        LatexEntry("⊇",  r"\supseteq",  "superconjunto o igual"),
        LatexEntry("∪",  r"\cup",       "unión"),
        LatexEntry("∩",  r"\cap",       "intersección"),
        LatexEntry("∖",  r"\setminus",  "diferencia"),
        LatexEntry("∅",  r"\emptyset",  "conjunto vacío"),
        LatexEntry("ℝ", r"\mathbb{R}",  "reales"),
        LatexEntry("ℕ", r"\mathbb{N}",  "naturales"),
        LatexEntry("ℤ", r"\mathbb{Z}",  "enteros"),
        LatexEntry("ℚ", r"\mathbb{Q}",  "racionales"),
        LatexEntry("ℂ", r"\mathbb{C}",  "complejos"),
        LatexEntry("∀", r"\forall",     "para todo"),
        LatexEntry("∃", r"\exists",     "existe"),
        LatexEntry("∄", r"\nexists",    "no existe"),
        LatexEntry("∧", r"\wedge",      "y lógico"),
        LatexEntry("∨", r"\vee",        "o lógico"),
        LatexEntry("¬", r"\neg",        "negación"),
        LatexEntry("∴", r"\therefore",  "por lo tanto"),
        LatexEntry("∵", r"\because",    "porque"),
    ],
    "Funciones comunes": [
        LatexEntry("sin",   r"\sin ",     "seno"),
        LatexEntry("cos",   r"\cos ",     "coseno"),
        LatexEntry("tan",   r"\tan ",     "tangente"),
        LatexEntry("cot",   r"\cot ",     "cotangente"),
        LatexEntry("sec",   r"\sec ",     "secante"),
        LatexEntry("csc",   r"\csc ",     "cosecante"),
        LatexEntry("arcsin", r"\arcsin ", "arcoseno"),
        LatexEntry("arccos", r"\arccos ", "arcocoseno"),
        LatexEntry("arctan", r"\arctan ", "arcotangente"),
        LatexEntry("sinh",  r"\sinh ",    "seno hiperbólico"),
        LatexEntry("cosh",  r"\cosh ",    "coseno hiperbólico"),
        LatexEntry("tanh",  r"\tanh ",    "tangente hiperbólica"),
        LatexEntry("log",   r"\log ",     "logaritmo"),
        LatexEntry("ln",    r"\ln ",      "logaritmo natural"),
        LatexEntry("logₐ",  r"\log_{a} ", "logaritmo en base a"),
        LatexEntry("exp",   r"\exp ",     "exponencial"),
        LatexEntry("eˣ",    r"e^{x}",     "e a la x"),
        LatexEntry("max",   r"\max ",     "máximo"),
        LatexEntry("min",   r"\min ",     "mínimo"),
        LatexEntry("sup",   r"\sup ",     "supremo"),
        LatexEntry("inf",   r"\inf ",     "ínfimo"),
        LatexEntry("arg",   r"\arg ",     "argumento"),
        LatexEntry("Re",    r"\Re ",      "parte real"),
        LatexEntry("Im",    r"\Im ",      "parte imaginaria"),
        LatexEntry("gcd",   r"\gcd ",     "máximo común divisor"),
        LatexEntry("mod",   r"\bmod ",    "módulo"),
        LatexEntry("text",  r"\text{texto}", "texto dentro de math"),
    ],
    "Ingeniería estructural": [
        LatexEntry("σᵢⱼ", r"\sigma_{ij}",                  "tensor de tensiones"),
        LatexEntry("εᵢⱼ", r"\varepsilon_{ij}",             "tensor de deformaciones"),
        LatexEntry("τ",  r"\tau",                          "tensión cortante"),
        LatexEntry("M·y/I", r"\frac{M \cdot y}{I}",        "flexión: σ = M y / I"),
        LatexEntry("V·Q/I·b", r"\frac{V \cdot Q}{I \cdot b}", "cortante: τ = V Q / (I b)"),
        LatexEntry("EI",  r"E I",                          "rigidez a flexión"),
        LatexEntry("EA",  r"E A",                          "rigidez axial"),
        LatexEntry("GJ",  r"G J",                          "rigidez torsional"),
        LatexEntry("üg",  r"\ddot u_{g}(t)",               "aceleración del suelo"),
        LatexEntry("F=ma", r"F = m \, a",                  "segunda ley de Newton"),
        LatexEntry("mü+cu̇+ku", r"m \, \ddot u + c \, \dot u + k \, u", "ecuación SDOF"),
        LatexEntry("ω=√(k/m)", r"\omega = \sqrt{\frac{k}{m}}", "frecuencia natural"),
        LatexEntry("T=2π/ω", r"T = \frac{2\pi}{\omega}",   "período"),
        LatexEntry("ζ", r"\zeta",                          "razón de amortiguamiento"),
        LatexEntry("ξ", r"\xi",                            "razón de amortiguamiento (notación alterna)"),
        LatexEntry("φ", r"\phi",                           "factor de minoración de resistencia"),
        LatexEntry("ρ", r"\rho",                           "densidad / cuantía"),
        LatexEntry("Δ", r"\Delta",                         "incremento / deriva"),
        LatexEntry("f'c", r"f'_{c}",                       "resistencia del concreto"),
        LatexEntry("fy",  r"f_{y}",                        "fluencia del acero"),
        LatexEntry("Mn",  r"M_{n}",                        "momento nominal"),
        LatexEntry("Vn",  r"V_{n}",                        "cortante nominal"),
        LatexEntry("Pn",  r"P_{n}",                        "carga nominal"),
    ],
}


def total_entries() -> int:
    """Return the total number of entries across all categories."""
    return sum(len(entries) for entries in CATALOG.values())


def find(needle: str) -> list[tuple[str, LatexEntry]]:
    """Return ``(category, entry)`` pairs whose label, latex source or
    tooltip contains *needle* (case-insensitive).

    Useful for a search box on top of the palette.
    """
    needle_l = needle.lower()
    out: list[tuple[str, LatexEntry]] = []
    for category, entries in CATALOG.items():
        for entry in entries:
            haystack = (
                entry.label.lower()
                + " "
                + entry.latex.lower()
                + " "
                + entry.tooltip.lower()
            )
            if needle_l in haystack:
                out.append((category, entry))
    return out
