class MarkdownRenderer:
    def render(self, markdown_sections):
        return "\n\n---\n\n".join(markdown_sections)