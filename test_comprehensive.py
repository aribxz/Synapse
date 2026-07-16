from app.rendering.markdown_renderer import MarkdownRenderer

renderer = MarkdownRenderer()

# Test 1: Multiple math fences
test1 = """```latex
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

# Test 2: With mermaid (should not be stripped)
test2 = """```latex
$$
E = mc^2
$$
```

```mermaid
flowchart LR
    A[Start] --> B[End]
```"""

# Test 3: Document-level fence (should be stripped)
test3 = """```markdown
# Title

Content here.
```"""

# Test 4: Mixed - document fence with math fence inside
test4 = """```markdown
# Title

```latex
$$
a = b
$$
```
```"""

# Test 5: Full document with sections
test5 = """# Section 1

```latex
$$
x = y
$$
```

---

# Section 2

```math
$$
z = w
$$
```"""

for i, test in enumerate([test1, test2, test3, test4, test5], 1):
    print(f"\n=== TEST {i} ===")
    print(f"Input:\n{test}\n")
    result = renderer.render([test])
    print(f"Output:\n{result}\n")
    print("-" * 50)