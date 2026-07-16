import re

text = """```latex
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

# Test the regex
result = re.sub(r'```latex\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
print('After first sub:')
print(repr(result))
print()

result2 = re.sub(r'```math\s*\n(.*?)\n```', r'\1', result, flags=re.DOTALL)
print('After second sub:')
print(repr(result2))