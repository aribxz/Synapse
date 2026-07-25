import re
import subprocess
import tempfile
import os
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
    print(msg, flush=True)


class QualityGate:
    def __init__(self, ai_service: "AIService | None" = None, linter=None):
        self.ai = ai_service
        self.linter = linter or MarkdownLinter()
        self._mmdc_available = self._check_mmdc()

    def _check_mmdc(self) -> bool:
        """Check if mmdc (Mermaid CLI) is available via npx."""
        try:
            result = subprocess.run(
                ["npx", "@mermaid-js/mermaid-cli", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _validate_mermaid(self, text: str, fast_model="gemini") -> str:
        """Validate Mermaid blocks by attempting to render them with mmdc.
        If mmdc is unavailable, fall back to heuristic validation.
        Broken diagrams are sent to AI repair, then stripped if still broken.
        """
        mermaid_blocks = list(re.finditer(r"```mermaid\n.*?```", text, flags=re.DOTALL))

        if not mermaid_blocks:
            return text

        for match in mermaid_blocks:
            block = match.group(0)
            content = block.replace("```mermaid", "").replace("```", "").strip()
            if not content:
                text = text[:match.start()] + "" + text[match.end():]
                continue

            is_valid = False
            if self._mmdc_available:
                is_valid = self._validate_via_mmdc(content)
            else:
                # Fallback: bracket balance check
                opens = content.count("[")
                closes = content.count("]")
                if opens != closes:
                    _safe_print(f"  Unbalanced brackets ({opens}[ vs {closes}]) - will attempt repair")
                else:
                    is_valid = True

            if not is_valid:
                _safe_print("  Mermaid validation failed - attempting AI repair")
                repaired = self._repair_mermaid(content, fast_model=fast_model)
                if repaired and self._verify_repaired_mermaid(repaired):
                    _safe_print("  AI repair succeeded")
                    text = text[:match.start()] + "```mermaid\n" + repaired + "\n```" + text[match.end():]
                else:
                    _safe_print("  AI repair failed or unavailable - stripping diagram")
                    text = text[:match.start()] + "" + text[match.end():]

        return text

    def _validate_via_mmdc(self, content: str) -> bool:
        """Use mmdc to attempt rendering the Mermaid diagram. Returns True if valid."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
                f.write(content)
                temp_input = f.name
            temp_output = temp_input.replace(".mmd", ".png")

            result = subprocess.run(
                ["npx", "@mermaid-js/mermaid-cli", "-i", temp_input, "-o", temp_output, "--quiet"],
                capture_output=True,
                timeout=15,
            )

            # Cleanup
            for path in (temp_input, temp_output):
                if os.path.exists(path):
                    os.remove(path)

            if result.returncode != 0:
                stderr = result.stderr.decode() if result.stderr else ""
                _safe_print(f"  mmdc error: {stderr[:200]}")
                return False
            return True
        except subprocess.TimeoutExpired:
            _safe_print("  mmdc timeout - treating as invalid")
            return False
        except Exception as e:
            _safe_print(f"  mmdc validation error: {e}")
            return False

    def _verify_repaired_mermaid(self, content: str) -> bool:
        """Verify a repaired mermaid block is valid."""
        if not content or not content.strip():
            return False
        if self._mmdc_available:
            return self._validate_via_mmdc(content)
        # Fallback: basic bracket balance
        return content.count("[") == content.count("]")

    def _repair_mermaid(self, broken_content: str, fast_model="gemini") -> str | None:
        """Attempt to repair a broken mermaid block via AI."""
        if self.ai is None:
            return None
        try:
            fixed = self.ai.repair_block(
                "```mermaid\n" + broken_content + "\n```",
                "mermaid_syntax",
                "Mermaid diagram has invalid syntax that prevents rendering. Fix node IDs and labels to be plain alphanumeric. No parentheses, math symbols, special chars, or nested brackets inside labels.",
                fast_model=fast_model,
            )
            # Extract the mermaid content from the response
            fixed = fixed.strip()
            if fixed.startswith("```mermaid"):
                fixed = fixed.replace("```mermaid", "").replace("```", "").strip()
            return fixed
        except Exception as e:
            _safe_print(f"  Mermaid AI repair error: {e}")
            return None

    def run(self, markdown: str, fast_model="gemini") -> str:
        markdown = self._validate_mermaid(markdown, fast_model=fast_model)

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
                markdown = self._repair(markdown, errors, fast_model=fast_model)

        return markdown

    def _repair(self, markdown: str, issues, fast_model="gemini") -> str:
        ai = self.ai
        if ai is None:
            return markdown

        doc_len = len(markdown)
        sorted_issues = sorted(issues, key=lambda i: i.start, reverse=True)

        fixed_ranges = []
        for issue in sorted_issues:
            if any(
                issue.start < f_end and issue.end > f_start
                for f_start, f_end in fixed_ranges
            ):
                continue

            # Skip repairs that cover most of the document — they'll nuke the output
            if doc_len > 0 and (issue.end - issue.start) / doc_len > 0.5:
                _safe_print(f"  Skipping repair for [{issue.category}] L{issue.line}: issue covers {(issue.end - issue.start) / doc_len:.0%} of document (too large)")
                continue

            # Skip repairs with no block content — nothing to fix
            if not issue.block.strip():
                _safe_print(f"  Skipping repair for [{issue.category}] L{issue.line}: no block content to repair")
                continue

            try:
                fixed = ai.repair_block(
                    issue.block, issue.category, issue.message, fast_model=fast_model
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