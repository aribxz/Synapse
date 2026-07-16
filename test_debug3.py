from app.rendering.markdown_renderer import MarkdownRenderer

renderer = MarkdownRenderer()

# Test the exact scenario: both ```latex and ```math fences
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

print("=== INPUT ===")
print(test)
print()

result = renderer.render([test])
print("=== OUTPUT ===")
print(result)