from app.rendering.markdown_renderer import MarkdownRenderer

renderer = MarkdownRenderer()

# Test both fences in one document
test2 = """```latex
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
print(test2)
print()

result2 = renderer.render([test2])
print("=== OUTPUT ===")
print(result2)