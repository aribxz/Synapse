import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class LintIssue:
    severity: Literal["error", "warning"]
    category: Literal["mermaid", "math", "wikilink"]
    message: str
    line: int
    start: int
    end: int
    block: str


class MarkdownLinter:
    def lint(self, markdown: str) -> list[LintIssue]:
        issues = []
        issues.extend(self._lint_mermaid(markdown))
        issues.extend(self._lint_math(markdown))
        issues.extend(self._lint_wikilinks(markdown))
        return issues

    def _strip_all_code(self, text: str) -> str:
        text = re.sub(r"(?s)```.*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)
        return text

    def _strip_fenced_only(self, text: str) -> str:
        return re.sub(r"(?s)```.*?```", "", text)

    def _lint_mermaid(self, markdown: str) -> list[LintIssue]:
        issues = []

        for match in re.finditer(r"(?s)```mermaid\n(.*?)```", markdown):
            block = match.group(0)
            content = match.group(1)
            block_start = match.start()
            block_end = match.end()
            start_line = markdown[:block_start].count("\n") + 1

            if not content.strip():
                issues.append(LintIssue(
                    severity="warning",
                    category="mermaid",
                    message="Empty mermaid block",
                    line=start_line,
                    start=block_start,
                    end=block_end,
                    block=block,
                ))
                continue

            no_comments = re.sub(r"(?m)^\s*%%.*$", "", content)

            bracket_balance = no_comments.count("[") == no_comments.count("]")
            brace_balance = no_comments.count("{") == no_comments.count("}")
            paren_balance = no_comments.count("(") == no_comments.count(")")
            quote_balance = no_comments.count('"') % 2 == 0

            if not bracket_balance:
                issues.append(LintIssue(
                    severity="error",
                    category="mermaid",
                    message="Unbalanced square brackets [] in mermaid block",
                    line=start_line,
                    start=block_start,
                    end=block_end,
                    block=block,
                ))
            if not brace_balance:
                issues.append(LintIssue(
                    severity="error",
                    category="mermaid",
                    message="Unbalanced curly braces {} in mermaid block",
                    line=start_line,
                    start=block_start,
                    end=block_end,
                    block=block,
                ))
            if not paren_balance:
                issues.append(LintIssue(
                    severity="error",
                    category="mermaid",
                    message="Unbalanced parentheses () in mermaid block",
                    line=start_line,
                    start=block_start,
                    end=block_end,
                    block=block,
                ))
            if not quote_balance:
                issues.append(LintIssue(
                    severity="error",
                    category="mermaid",
                    message="Unbalanced double quotes in mermaid block",
                    line=start_line,
                    start=block_start,
                    end=block_end,
                    block=block,
                ))

            if "xychart-beta" in content:
                missing = []
                for key in ["title", "x-axis", "y-axis"]:
                    if key not in content:
                        missing.append(key)
                if "line" not in content:
                    missing.append("line")
                if missing:
                    issues.append(LintIssue(
                        severity="error",
                        category="mermaid",
                        message=f"xychart-beta missing: {', '.join(missing)}",
                        line=start_line,
                        start=block_start,
                        end=block_end,
                        block=block,
                    ))

        return issues

    def _lint_math(self, markdown: str) -> list[LintIssue]:
        issues = []

        no_code = self._strip_all_code(markdown)

        i = 0
        dollar_count = 0
        while i < len(no_code):
            if no_code[i] == "$":
                if i + 1 < len(no_code) and no_code[i + 1] == "$":
                    dollar_count += 2
                    i += 2
                else:
                    dollar_count += 1
                    i += 1
            else:
                i += 1

        if dollar_count % 2 != 0:
            issues.append(LintIssue(
                severity="warning",
                category="math",
                message=f"Unbalanced $ delimiters ({dollar_count} total, odd count)",
                line=1,
                start=0,
                end=1,
                block="",
            ))

        unicode_map = {
            "\u2082": "log\u2082 (Unicode subscript, use \\\\log_2)",
            "\u03a3": "\u03a3 (use \\\\sum)",
            "\u2192": "\u2192 (use \\\\to)",
            "\u2248": "\u2248 (use \\\\approx)",
            "\u00d7": "\u00d7 (use \\\\times)",
            "\u2260": "\u2260 (use \\\\neq)",
            "\u2264": "\u2264 (use \\\\leq)",
            "\u2265": "\u2265 (use \\\\geq)",
            "\u221e": "\u221e (use \\\\infty)",
        }

        for dm_match in re.finditer(r"\$\$(.+?)\$\$", markdown, re.DOTALL):
            inner = dm_match.group(1)
            found = [desc for char, desc in unicode_map.items() if char in inner]
            if found:
                issues.append(LintIssue(
                    severity="warning",
                    category="math",
                    message=f"Unicode math in $$ block: {', '.join(found)}",
                    line=markdown[:dm_match.start()].count("\n") + 1,
                    start=dm_match.start(),
                    end=dm_match.end(),
                    block=dm_match.group(0),
                ))

        for im_match in re.finditer(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", markdown):
            inner = im_match.group(1)
            found = [desc for char, desc in unicode_map.items() if char in inner]
            if found:
                issues.append(LintIssue(
                    severity="warning",
                    category="math",
                    message=f"Unicode math in $ block: {', '.join(found)}",
                    line=markdown[:im_match.start()].count("\n") + 1,
                    start=im_match.start(),
                    end=im_match.end(),
                    block=im_match.group(0),
                ))

        seen = set()
        no_fenced = self._strip_fenced_only(markdown)
        for code_match in re.finditer(r"`([^`]+)`", no_fenced):
            inner = code_match.group(1).strip()
            if inner in seen:
                continue
            seen.add(inner)
            has_math_chars = any(g in inner for g in ["\u03a3", "\u03c0", "\u03b8", "\u03b1", "\u03b2", "\u03bc", "\u03c3"])
            has_latex_cmd = bool(re.search(r"\\(?:log|sum|int|frac|hat|bar|sqrt|lim|cong|approx|to|times|cdot|nabla|partial|infty|alpha|beta|gamma|delta|theta|mu|sigma|pi)", inner))
            has_unicode_math = any(c in inner for c in ["\u2082", "\u2083", "\u00b2", "\u00b3"])
            if "=" in inner and (has_math_chars or has_latex_cmd or has_unicode_math):
                match_text = code_match.group(0)
                pos = markdown.find(match_text)
                if pos == -1:
                    continue
                line_num = markdown[:pos].count("\n") + 1
                issues.append(LintIssue(
                    severity="warning",
                    category="math",
                    message=f"Formula in code block instead of $...$: {inner[:60]}",
                    line=line_num,
                    start=pos,
                    end=pos + len(match_text),
                    block=match_text,
                ))

        return issues

    def _lint_wikilinks(self, markdown: str) -> list[LintIssue]:
        issues = []

        headings = set()
        for match in re.finditer(r"^(#{1,6})\s+(.+)$", markdown, re.MULTILINE):
            heading = match.group(2).strip().lower()
            headings.add(heading)

        no_code = self._strip_all_code(markdown)

        for match in re.finditer(r"\[\[#([^\]]+)\]\]", no_code):
            link_target = match.group(1).strip().lower()
            if link_target not in headings:
                line_num = markdown[:match.start()].count("\n") + 1
                issues.append(LintIssue(
                    severity="error",
                    category="wikilink",
                    message=f'Wiki link target "#{match.group(1).strip()}" not found in headings',
                    line=line_num,
                    start=match.start(),
                    end=match.end(),
                    block=match.group(0),
                ))

        return issues