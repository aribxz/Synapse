import re


class MarkdownRenderer:
    def render(self, markdown_sections):
        text = "\n\n---\n\n".join(markdown_sections)
        return self._sanitize_markdown(text)

    def _sanitize_markdown(self, text: str) -> str:
        """Apply all known markdown fixes in a single deterministic pass.
        
        This consolidates all post-processing so new fixes are added in one place.
        Order matters: earlier fixes may create patterns that later fixes handle.
        """
        text = self._wrap_naked_mermaid(text)
        text = self._strip_fences(text)
        text = self._strip_math_fences(text)          # NEW: strip ```latex / ```math fences
        text = self._strip_mermaid_live_links(text)
        text = self._fix_latex_delimiters(text)       # \[...\] -> $$...$$, \(...\) -> $...$
        text = self._cleanup_latex(text)              # stray backslash fixes
        text = self._fix_math_notation(text)          # unicode math -> LaTeX
        text = self._normalize_headings(text)         # heading hierarchy
        text = self._fix_mermaid_nodes(text)          # nested brackets in mermaid
        text = self._fix_callouts(text)               # bold-wrapped callouts
        text = self._fix_heading_callouts(text)       # heading+callout combos like ## > [!example]
        text = self._fix_wiki_links(text)             # fuzzy wiki link matching
        text = self._collapse_blank_lines(text)       # 3+ blank lines -> 2
        return text

    def _fix_latex_delimiters(self, text: str) -> str:
        """Convert academic LaTeX delimiters to Obsidian-compatible ones.

        Obsidian only recognizes $$...$$ for display math and $...$ for inline.
        Academic LaTeX uses \\[...\\] and \\(...\\) which Obsidian ignores.
        """
        text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
        text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
        return text

    def _strip_math_fences(self, text: str) -> str:
        """Strip ```latex and ```math code fences that wrap $$...$$ math.
        
        Obsidian code fences take priority over math rendering, so a ```latex
        fence around $$...$$ causes the math to display as raw text instead
        of rendered equations. The model often outputs:
          ```latex
          $$
          \\begin{array}{...}
          \\end{array}
          $$
          ```
        This strips the fence, exposing the bare $$...$$ for Obsidian's renderer.
        """
        text = re.sub(r'```latex\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'```math\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
        return text

    def _wrap_naked_mermaid(self, text: str) -> str:
        """Wrap naked mermaid blocks (missing backtick fences) before they hit _strip_fences.

        Some models output a bare ``mermaid`` line instead of ```mermaid ... ```.
        This detects that pattern and wraps it with proper fences.
        """
        lines = text.split("\n")
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped == "mermaid" or stripped.startswith("mermaid "):
                nxt = i + 1
                if nxt < len(lines) and any(
                    lines[nxt].strip().startswith(kw)
                    for kw in [
                        "flowchart",
                        "graph",
                        "sequenceDiagram",
                        "classDiagram",
                        "stateDiagram",
                        "gantt",
                        "pie",
                        "erDiagram",
                        "xychart",
                        "block",
                        "timeline",
                        "mindmap",
                    ]
                ):
                    diagram = []
                    captions = []
                    j = nxt
                    while j < len(lines):
                        l = lines[j]
                        s = l.strip()
                        if s == "" or s.startswith("#") or s.startswith(">"):
                            break
                        if s.startswith("*") and not s.startswith("**"):
                            captions.append(l)
                        else:
                            diagram.append(l)
                        j += 1
                    if diagram:
                        result.append("```mermaid")
                        result.extend(diagram)
                        result.append("```")
                        result.extend(captions)
                        i = j
                        continue
            result.append(line)
            i += 1
        return "\n".join(result)

    def _strip_fences(self, text: str) -> str:
        """Strip document-level ```markdown or ``` fences that wrap the ENTIRE output.

        Does NOT strip inline ```mermaid blocks — those are valid Markdown.
        Only strips if the document has exactly one pair of outer fences (first and last non-empty lines).
        """
        lines = text.split('\n')
        first_idx = next((i for i, l in enumerate(lines) if l.strip()), None)
        last_idx = next((i for i, l in enumerate(reversed(lines)) if l.strip()), None)
        if first_idx is not None and last_idx is not None:
            last_idx = len(lines) - 1 - last_idx
            first_line = lines[first_idx].strip()
            last_line = lines[last_idx].strip()
            # Check if first and last lines form a matching fence pair
            is_fence_pair = (
                first_line.startswith('```') and first_line != '```mermaid'
                and last_line == '```'
            )
            # Also require no OTHER fence lines in between (otherwise it's inline fenced blocks)
            fence_count = sum(1 for l in lines if l.strip().startswith('```'))
            if is_fence_pair and fence_count <= 2:
                # Document is wrapped in a single pair of fences — strip them
                lines = lines[first_idx + 1:last_idx]
                text = '\n'.join(lines)
            elif first_line == '```markdown' and last_line == '```':
                # Explicit ```markdown wrapper
                fence_count = sum(1 for l in lines if l.strip().startswith('```'))
                if fence_count <= 2:
                    lines = lines[first_idx + 1:last_idx]
                    text = '\n'.join(lines)
        return text.strip()

    def _strip_mermaid_live_links(self, text: str) -> str:
        """Strip dead mermaid.live image links — native ```mermaid blocks render in Obsidian."""
        return re.sub(r"!\[.*?\]\(https://mermaid\.live/.*?\)", "", text)

    def _normalize_headings(self, text: str) -> str:
        """Normalize heading hierarchy: demote # to ## if there are multiple top-level heads."""
        lines = text.split("\n")
        has_h1 = any(re.match(r"^# [^#]", line) for line in lines)
        h1_count = sum(1 for line in lines if re.match(r"^# [^#]", line))
        if h1_count > 1:
            result = []
            for line in lines:
                if re.match(r"^# ", line):
                    result.append("##" + line[1:])
                elif re.match(r"^## ", line):
                    result.append("###" + line[2:])
                elif re.match(r"^### ", line):
                    result.append("####" + line[3:])
                elif re.match(r"^#### ", line):
                    result.append("#####" + line[4:])
                elif re.match(r"^##### ", line):
                    result.append("######" + line[5:])
                else:
                    result.append(line)
            return "\n".join(result)
        return text

    def _cleanup_latex(self, text: str) -> str:
        text = re.sub(r"\\([()])", r"\1", text)
        text = re.sub(r"\\\\([()])", r"\\\1", text)
        return text

    def _fix_math_notation(self, text: str) -> str:
        """Replace Unicode math characters with LaTeX inside math blocks."""

        def _replace_unicode_math(math_content: str) -> str:
            subs = [
                ("log\u2082", "\\log_2"),
                ("log\u2081\u2080", "\\log_{10}"),
                ("log\u2091", "\\ln"),
                ("\u03a3", "\\sum"),
                ("\u2192", "\\to"),
                ("\u2248", "\\approx"),
                ("\u00d7", "\\times"),
                ("\u2260", "\\neq"),
                ("\u2264", "\\leq"),
                ("\u2265", "\\geq"),
                ("\u221e", "\\infty"),
                ("\u03b1", "\\alpha"),
                ("\u03b2", "\\beta"),
                ("\u03b8", "\\theta"),
                ("\u03bc", "\\mu"),
                ("\u03c3", "\\sigma"),
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
        """Fix mermaid node labels with nested brackets.

        The model often outputs: Node["Label["inner"]"] which breaks Mermaid.
        Convert to: Node["Label (inner)"].
        """
        def _fix_block(block: str) -> str:
            # Fix nested brackets in labels: Node["Label["inner"]"] -> Node["Label (inner)"]
            # Also handles: Node[Label["inner"]] -> Node["Label (inner)"]
            while re.search(r'\["[^"]*\[[^\[\]]*"\]', block):
                block = re.sub(
                    r'(\w+)\["([^"]*?)\[([^\[\]]*?)"\]"\]',
                    lambda m: f'{m.group(1)}["{m.group(2)}({m.group(3)})"]',
                    block,
                )
            while re.search(r'\[[^\[\]]*\[[^\[\]]*\]', block):
                block = re.sub(
                    r'(\w+)\[([^\[\]]*?)\[([^\[\]]*?)\]',
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

    def _fix_callouts(self, text: str) -> str:
        """Fix callout formatting: > **[!type]** -> > [!type]"""
        return re.sub(r'\*\*\[!(\w+)\]\*\*', r'[!\1]', text)

    def _fix_heading_callouts(self, text: str) -> str:
        """Fix headings that have a callout embedded in them: ## > [!example] Text -> ## Text"""
        return re.sub(r'^(#{1,6})\s+> \[!\w+\]\s+', r'\1 ', text, flags=re.MULTILINE)

    def _fix_wiki_links(self, text: str) -> str:
        """Fuzzy-match [[#...]] wiki-link text to actual headings to fix typos.

        Obsidian links are case-sensitive and must match the heading exactly.
        """
        headings = []
        for line in text.split("\n"):
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                headings.append(m.group(2).strip())

        if not headings:
            return text

        def _score(a: str, b: str) -> float:
            aw = set(a.lower().split())
            bw = set(b.lower().split())
            if not aw or not bw:
                return 0.0
            return len(aw & bw) / max(len(aw), len(bw))

        def _best(link_text: str) -> str:
            if link_text in headings:
                return link_text
            best = max(headings, key=lambda h: _score(link_text, h))
            if _score(link_text, best) >= 0.4:
                return best
            return link_text

        def _fix(m):
            return f"[[#{_best(m.group(1))}]]"

        return re.sub(r"\[\[#([^\]]+)\]\]", _fix, text)

    def _collapse_blank_lines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)