from app.rendering.markdown_renderer import MarkdownRenderer

renderer = MarkdownRenderer()

# Test step by step
test = """```latex
$$
a = b
$$
```

Some text.

```math
$$
c = d
$$
```"""

print("=== ORIGINAL ===")
print(repr(test))
print()

t1 = renderer._wrap_naked_mermaid(test)
print("=== AFTER _wrap_naked_mermaid ===")
print(repr(t1))
print()

t2 = renderer._strip_fences(t1)
print("=== AFTER _strip_fences ===")
print(repr(t2))
print()

t3 = renderer._strip_math_fences(t2)
print("=== AFTER _strip_math_fences ===")
print(repr(t3))
print()