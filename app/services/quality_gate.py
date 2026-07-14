from typing import TYPE_CHECKING

from app.rendering.linter import MarkdownLinter

if TYPE_CHECKING:
    from app.services.ai_service import AIService


_UNICODE_REPLACEMENTS = {
    "\u03a3": "Sigma",
    "\u2192": "->",
    "\u2248": "~=",
    "\u00d7": "x",
    "\u2082": "_2",
    "\u2260": "!=",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u221e": "inf",
    "\u03b1": "alpha",
    "\u03b2": "beta",
    "\u03b8": "theta",
    "\u03bc": "mu",
    "\u03c3": "sigma",
    "\u03c0": "pi",
}


def _safe_print(msg: str):
    for old, new in _UNICODE_REPLACEMENTS.items():
        msg = msg.replace(old, new)
    print(msg)


class QualityGate:
    def __init__(self, ai_service: "AIService | None" = None, linter=None):
        self.ai = ai_service
        self.linter = linter or MarkdownLinter()

    def run(self, markdown: str) -> str:
        issues = self.linter.lint(markdown)

        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        if errors or warnings:
            _safe_print(f"\n--- QualityGate: {len(errors)} error(s), {len(warnings)} warning(s) ---")
            for issue in errors:
                _safe_print(f"  Error [{issue.category}] L{issue.line}: {issue.message[:100]}")
            for issue in warnings:
                _safe_print(f"  Warning [{issue.category}] L{issue.line}: {issue.message[:100]}")
            if errors and self.ai:
                markdown = self._repair(markdown, errors)

        return markdown

    def _repair(self, markdown: str, issues) -> str:
        ai = self.ai
        if ai is None:
            return markdown

        sorted_issues = sorted(issues, key=lambda i: i.start, reverse=True)

        fixed_ranges = []
        for issue in sorted_issues:
            if any(
                issue.start < f_end and issue.end > f_start
                for f_start, f_end in fixed_ranges
            ):
                continue

            try:
                fixed = ai.repair_block(
                    issue.block, issue.category, issue.message
                )
                markdown = markdown[:issue.start] + fixed + markdown[issue.end:]
                fixed_ranges.append((issue.start, issue.start + len(fixed)))
                _safe_print(f"  Repaired [{issue.category}] L{issue.line}")
            except Exception as e:
                _safe_print(f"  Repair failed [{issue.category}] L{issue.line}: {e}")

        remaining = self.linter.lint(markdown)
        remaining_errors = [i for i in remaining if i.severity == "error"]
        if remaining_errors:
            _safe_print(f"  {len(remaining_errors)} error(s) remain after repair")

        return markdown
