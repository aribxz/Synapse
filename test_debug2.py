import re

def _strip_math_fences(text: str) -> str:
    print("=== BEFORE ===")
    print(repr(text))
    print()
    
    # First: ```latex
    text = re.sub(r'```latex\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
    print("=== AFTER LATEX ===")
    print(repr(text))
    print()
    
    # Second: ```math
    text = re.sub(r'```math\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
    print("=== AFTER MATH ===")
    print(repr(text))
    print()
    
    return text

test = r"""```latex
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

result = _strip_math_fences(test)
print("=== FINAL ===")
print(result)