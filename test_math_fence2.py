from app.rendering.markdown_renderer import MarkdownRenderer

renderer = MarkdownRenderer()

# Test ```math fence
test = r"""```math
$$
E = mc^2
$$
```"""

print("=== INPUT (```math fence) ===")
print(test)
print()

result = renderer.render([test])
print("=== OUTPUT ===")
print(result)
print()

# Test both in one document
test2 = r"""```latex
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

print("=== INPUT (both fences) ===")
print(test2)
print()

result2 = renderer.render([test2])
print("=== OUTPUT ===")
print(result2)