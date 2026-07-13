import re


class MarkdownRenderer:
    def render(self, markdown_sections):
        text = "\n\n---\n\n".join(markdown_sections)
        text = self._cleanup_latex(text)
        text = self._collapse_blank_lines(text)
        return text

    def _cleanup_latex(self, text: str) -> str:
        # Remove stray escaped parentheses: \(  → (  and \)  → )
        text = re.sub(r"\\([()])", r"\1", text)
        # Fix double-escaped delimiters: \\(  → \(  and \\)  → \)
        text = re.sub(r"\\\\([()])", r"\\\1", text)
        return text

    def _collapse_blank_lines(self, text: str) -> str:
        # Collapse 3+ consecutive blank lines into exactly 2
        return re.sub(r"\n{3,}", "\n\n", text)
