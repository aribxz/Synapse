from app.rendering.markdown_renderer import MarkdownRenderer

renderer = MarkdownRenderer()

# Test case: model wraps $$...$$ in ```latex fence
test = r"""```latex
$$
\begin{array}{lccc}
\text{Function} & \text{Formula} & \text{Range} & \text{Derivative} \\ \hline
\text{ReLU} & f(x) = \max(0, x) & [0, \infty) & f'(x) = \begin{cases} 1 & x > 0 \\ 0 & x \le 0 \end{cases} \\
\text{Sigmoid} & \sigma(x) = \frac{1}{1 + e^{-x}} & (0, 1) & \sigma'(x) = \sigma(x)(1 - \sigma(x)) \\
\text{TanH} & \tanh(x) = \frac{e^x - e^{-x}}{e^x + e^{-x}} & (-1, 1) & \tanh'(x) = 1 - \tanh^2(x)
\end{array}
$$
```

Some text after."""

print("=== INPUT ===")
print(test)
print()

result = renderer.render([test])
print("=== OUTPUT ===")
print(result)