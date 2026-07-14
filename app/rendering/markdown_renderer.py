import re


class MarkdownRenderer:
    def render(self, markdown_sections):
        text = "\n\n---\n\n".join(markdown_sections)
        text = self._strip_fences(text)
        text = self._cleanup_latex(text)
        text = self._fix_math_notation(text)
        text = self._fix_mermaid_nodes(text)
        text = self._collapse_blank_lines(text)
        return text

    def _strip_fences(self, text: str) -> str:
        """Strip leading/trailing ```markdown or ``` fences that models sometimes add."""
        text = re.sub(r"^```(markdown)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    def _cleanup_latex(self, text: str) -> str:
        text = re.sub(r"\\([()])", r"\1", text)
        text = re.sub(r"\\\\([()])", r"\\\1", text)
        return text

    def _fix_math_notation(self, text: str) -> str:
        """Replace Unicode math characters with LaTeX inside math blocks."""

        def _replace_unicode_math(math_content: str) -> str:
            subs = [
                ("log\u2082", "\\\\log_2"),
                ("log\u2081\u2080", "\\\\log_{10}"),
                ("log\u2091", "\\\\ln"),
                ("\u03a3", "\\\\sum"),
                ("\u2192", "\\\\to"),
                ("\u2248", "\\\\approx"),
                ("\u00d7", "\\\\times"),
                ("\u2260", "\\\\neq"),
                ("\u2264", "\\\\leq"),
                ("\u2265", "\\\\geq"),
                ("\u221e", "\\\\infty"),
                ("\u03b1", "\\\\alpha"),
                ("\u03b2", "\\\\beta"),
                ("\u03b8", "\\\\theta"),
                ("\u03bc", "\\\\mu"),
                ("\u03c3", "\\\\sigma"),
            ]
            for unicode_char, latex in subs:
                math_content = math_content.replace(unicode_char, latex)
            return math_content

        def _fix_inline(match):
            return "$" + _replace_unicode_math(match.group(1)) + "$"

        def _fix_display(match):
            return "$$" + _replace_unicode_math(match.group(1)) + "$$"

        text = re.sub(r"\$(.+?)\$", _fix_inline, text)
        text = re.sub(r"\$\$(.+?)\$\$", _fix_display, text)
        return text

    def _fix_mermaid_nodes(self, text: str) -> str:
        """Fix mermaid node IDs that contain parentheses or nested brackets.

        Probability(p)       -> Probability["Probability (p)"]
        Surprise(-log(p))    -> Surprise["Surprise (-log(p))"]
        A["text["inner"]"]   -> A["text (inner)"]
        """
        def _fix_block(block: str) -> str:
            def _wrap_paren_node(match):
                node_name = match.group(1)
                inner = match.group(2)
                return f'{node_name}["{node_name} ({inner})"]'

            block = re.sub(
                r"\b(\w+)\(((?:[^()]+|\([^()]*\))*)\)",
                _wrap_paren_node,
                block,
            )
            while re.search(r'\["[^"]*\[[^\[\]]*"\]', block):
                block = re.sub(
                    r'(\w+)\["([^"]*?)\[([^\[\]]*?)"\]"\]',
                    lambda m: f'{m.group(1)}["{m.group(2)}({m.group(3)})"]',
                    block,
                )
            return block

        text = re.sub(
            r"```mermaid\n.*?```",
            lambda m: _fix_block(m.group(0)),
            text,
            flags=re.DOTALL,
        )
        return text

    def _collapse_blank_lines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)
