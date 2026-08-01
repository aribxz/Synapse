from pathlib import Path

class ExportService:
    def export(self, markdown, filename):
        base_dir = Path(__file__).resolve().parent.parent # Gets the file name, gets the absolute path, removes one directory.

        output_dir = base_dir / "outputs" # Store.
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"{filename}.md" 

        output_file.write_text(markdown, encoding="utf-8") # This is the save

        return output_file