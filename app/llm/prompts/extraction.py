from .base import BASE_ROLE

EXTRACTION_PROMPT = f"""
{BASE_ROLE}

Your job is to preserve knowledge, not write notes.

Extract structured knowledge that will help another AI teach this material.

For every field below, you MUST extract something. Never leave an array empty.
If the source does not explicitly cover something, infer what you can or write "Not explicitly covered in source."

====================
FIELD GUIDANCE
====================

- **concepts**: The core ideas introduced. One short phrase per entry.
  ["overfitting", "bias-variance tradeoff", "regularization"]

- **definitions**: Precise definitions of key terms. 1-2 sentences each.
  ["Overfitting: when a model fits training data perfectly but fails on new data because it learned noise instead of signal."]

- **mechanisms**: How something works step-by-step. Can include multiple sentences.
  ["Gradient descent iteratively adjusts parameters: compute the gradient of the loss, move parameters in the opposite direction by the learning rate, repeat until convergence."]

- **algorithms**: Named procedures with steps. Include the steps.
  ["Decision tree building: 1. Start with all data at root. 2. Find the feature and threshold that best splits the data (lowest Gini/SSR). 3. Split into two child nodes. 4. Repeat recursively until a stopping rule is met."]

- **reasoning**: Why a method works or why it is designed a certain way.
  ["Squaring residuals does two things: makes errors positive (so +10 and -10 don't cancel), and punishes large errors disproportionately."]

- **intuition**: Mental models, analogies, or high-level ways to think about the concept. Write in plain language as if explaining to a friend.
  ["Think of Gini Impurity like a drawer of socks: if it is all socks, perfectly organised (Gini=0). If half socks and half shirts, maximally messy (Gini=0.5)."]

- **why_it_matters**: Why the reader should care about this concept. Practical importance.
  ["Understanding bias vs variance tells you whether to collect more data (fixes variance) or add better features (fixes bias) — saving weeks of wasted effort."]

- **examples**: Concrete worked examples with actual numbers, if the source provides any.
  ["Entropy example: if 2 out of 5 people love a movie, p=0.4, entropy = -0.4log2(0.4) - 0.6log2(0.6) = 0.97."]

- **important_details**: Technical specifics the source emphasised: parameter values, edge cases, or nuances.
  ["Default lambda in XGBoost is 1. Larger lambda = simpler trees."]

- **common_misconceptions**: Mistakes or misunderstandings the source warns about.
  ["A coefficient of 1.825 does NOT mean probability increases by 1.825 per unit — it means log-odds increases by 1.825."]

- **prerequisites**: Concepts the reader should already know before this one.
  ["Gradient descent", "Loss functions"]

- **connections**: How this concept relates to other topics in the material. Use the format: "Topic Name — relationship".
  ["Bias-Variance Tradeoff — High bias leads to underfitting, high variance leads to overfitting."]

- **formulas**: Mathematical formulas exactly as presented. Use LaTeX notation within the string.
  ["$$G = 1 - \\\\sum p_i^2$$"]

- **pitfalls**: Warnings, gotchas, or things that can silently go wrong.
  ["Using the test set to pick a model invalidates it as an unbiased evaluation."]

- **summary**: A 2-3 sentence summary of the entire topic. This can be paragraphs.
  ["Decision trees split data recursively using yes/no questions. For classification, Gini impurity measures split quality; for regression, SSR does. Pruning via cost-complexity prevents overfitting."]

- **coverage**: How much the source said about this topic. Choose exactly one.
  - "thin": Barely mentioned; most fields will be sparse.
  - "adequate": Covered the basics; most fields have content.
  - "rich": Went deep with explanations, examples, and nuance.

====================
CRITICAL RULES
====================

- Every array field must contain at least one entry. If the source genuinely does not cover something, put: "Not covered in source."
- Formulas must use LaTeX delimiters ($...$ or $$...$$).
- Keep individual entries concise (1-3 sentences max per entry).
- Do NOT merge concepts — each array entry should be one discrete item.
- Return ONLY valid JSON. No explanation, no markdown formatting, no code fences.

====================
OUTPUT SCHEMA
====================

{{
    "concepts": [],
    "definitions": [],
    "mechanisms": [],
    "algorithms": [],
    "reasoning": [],
    "intuition": [],
    "why_it_matters": [],
    "examples": [],
    "important_details": [],
    "common_misconceptions": [],
    "prerequisites": [],
    "connections": [],
    "formulas": [],
    "pitfalls": [],
    "summary": "",
    "coverage": "adequate"
}}
"""