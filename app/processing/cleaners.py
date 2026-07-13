import re # -> Regex (Regular Expressions)

class TextCleaner: # We do this because large amounts of whitespaces can consume tokens.
    def clean(self, text: str):
        text = text.replace("\r", "\n") # standardizes everything to \n
        text = re.sub(r"\n{3,}", "\n\n", text) # If you find 3 or more consecutive newlines in a row, shrink them down to a maximum of 2 newlines
        text = re.sub(r"[ \t]+", " ", text) # looks for any sequence of multiple spaces or tabs (\t) and collapses them down into a single, clean space
        text = text.strip() # Trims off any accidental trailing spaces or blank lines sitting at the very beginning or the very end of the entire document.

        return text
