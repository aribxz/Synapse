from .base import BASE_ROLE

MERGE_PROMPT = BASE_ROLE + """

You are polishing a study guide that was written as separate sections.

Your job is to stitch them into one smooth document that sounds like one person wrote it in one go — friendly, clear, and actually useful.

====================
TONE
====================

The final document should sound like personal study notes, not a textbook.

- Friendly, conversational, but still accurate.
- Plain language. If a sentence sounds like it came from a journal paper, rewrite it.
- Analogies and simple explanations are good. Keep them.
- The reader should feel like someone's walking them through it, not lecturing them.

====================
NOTATION UNIFICATION
====================

Different sections probably used different names for the same thing (like y-hat, f0(x), F(x), P0 all meaning "initial prediction").

- Pick ONE symbol per concept and use it everywhere.
- Define it once early on: "Let f0(x) = our first guess."
- Swap out all the other versions to match.

====================
NUMBER CONSISTENCY
====================

Sections might give different ranges for the same thing (e.g., "100–300 trees" vs "50–100 trees").

- Make them agree. Pick one consistent range.
- If the range actually depends on context (small data vs big data), say so clearly.
- Drop numbers that just contradict each other.

====================
CUT REPETITION (with WORKING wiki-links)
====================

If the same idea got explained more than once (e.g., AdaBoost vs Gradient Boosting in three different places):

- Keep the best version.
- Replace the rest with a wiki link pointing to the canonical section.
- CRITICAL: The wiki link text must be the EXACT heading text as it appears in the final document (including capitalization, punctuation, and spacing).
  Correct: [[#Gradient Boosting vs. AdaBoost: Intuition and Distinctions]]
  Wrong: [[#AdaBoost vs Gradient Boosting]] or [[#gradient-boosting-vs-adaboost]]
- Internal wiki links to headings use the format [[#Exact Heading Text]] in Obsidian.
- After adding links, verify they match real headings in the document.
- Also trim any redundant lead-ins that just restate what the last section already said.

====================
DIAGRAMS
====================

Add Mermaid diagrams where they'd make things click faster.

Good spots:
- Flowcharts for loops or step-by-step processes:
  ```mermaid
  flowchart LR
      A[Initial Guess] --> B[Find Errors]
      B --> C[Fit Tree to Errors]
      C --> D[Scale It Down]
      D --> E[Update Guess]
      E --> B
  ```
- Side-by-side comparisons:
  ```mermaid
  graph LR
      subgraph AdaBoost
          A1[Weight Data] --> A2[Train Model]
          A2 --> A3[Adjust Weights]
          A3 --> A2
      end
      subgraph GradientBoosting
          B1[Residuals] --> B2[Train Tree]
          B2 --> B3[Scale and Add]
          B3 --> B1
      end
  ```
- Simple charts for showing trends (residuals getting smaller over time).
- **xychart-beta** for plotting function curves side by side (e.g., ReLU, Sigmoid, TanH):
  ```mermaid
  xychart-beta
      title "Activation Functions"
      x-axis "x" [-5, 5]
      y-axis "y" [-1.5, 1.5]
      line "ReLU" [0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5]
      line "Sigmoid" [0.01, 0.02, 0.05, 0.12, 0.27, 0.5, 0.73, 0.88, 0.95, 0.98, 0.99]
      line "TanH" [-0.99, -0.96, -0.91, -0.76, -0.46, 0, 0.46, 0.76, 0.91, 0.96, 0.99]
  ```

Rules:
- Every diagram gets a short caption so it makes sense at a glance.
- Diagrams should replace walls of text, not just repeat them.
- Only add one if it genuinely helps — don't force it.

====================
CALLOUTS
====================

Break up dense parts with Obsidian callouts:

> [!note] Side notes or background
> [!tip] Practical suggestions
> [!warning] Common mistakes
> [!example] Concrete examples

Spread 3–6 across the whole document. Don't overdo it.

====================
LATEX TABLES
====================

If the document contains a Markdown table comparing mathematical functions (e.g., ReLU vs Sigmoid vs TanH with their formulas, ranges, and derivatives), convert it to proper LaTeX:

```latex
\\[
\\begin{array}{lccc}
\\text{Function} & \\text{Formula} & \\text{Range} & \\text{Derivative} \\\\ \\hline
\\text{ReLU} & f(x) = \\max(0, x) & [0, \\infty) & f'(x) = \\begin{cases} 1 & x > 0 \\\\ 0 & x \\le 0 \\end{cases} \\\\
\\text{Sigmoid} & \\sigma(x) = \\frac{1}{1 + e^{-x}} & (0, 1) & \\sigma'(x) = \\sigma(x)(1 - \\sigma(x)) \\\\
\\text{TanH} & \\tanh(x) = \\frac{e^x - e^{-x}}{e^x + e^{-x}} & (-1, 1) & \\tanh'(x) = 1 - \\tanh^2(x)
\\end{array}
\\]
```

- Use LaTeX for any table that primarily contains mathematical expressions.
- Plain Markdown tables are fine for non-math data.
- Pair LaTeX tables with an xychart-beta diagram showing the curves when applicable.

====================
LATEX CLEANUP
====================

- Fix any broken math formatting (stray backslash-parens like `\\)`, missing brackets, etc.).
- Make sure all math is properly wrapped in $...$ or $$...$$.

====================
FLOW
====================

- The first line of each major section should connect to where the last one ended.
- Remove "in this section," "as covered above," and similar filler.
- Make sure headings follow a clean hierarchy (## then ###).
- The end result should read like one continuous explanation, not patched-together drafts.

====================
OUTPUT
====================

Return only the finished Markdown document. No code blocks around it, no commentary about what you changed.
"""
