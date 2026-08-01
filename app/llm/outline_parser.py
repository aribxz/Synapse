# The parser gains a global map, allowing it to intelligently jump to the exact sections of the documents it needs
from dataclasses import dataclass

@dataclass
class OutlineTopic:
    title: str
    description: str
    role: str
    source_chunks: list[int]

class OutlineParser: # Processes the AI's response. When it sees Source Chunks: 1, 5, it converts that string into a Python list of integers inside an OutlineTopic object.
    def parse(self, outline: str) -> list[OutlineTopic]: # It takes a raw string (outline) and returns a list of OutlineTopic objects.
        topics = []
        current = {}

        for line in outline.splitlines(): # Splits the large input string by newline characters
            line = line.strip() # Removes whitespace from the start and end of the line

            if not line: 
                continue

            if line.startswith("Title:"):
                current["title"] = line.removeprefix("Title:").strip()  # removeprefix() crops away that header tag, .strip() scrubs any remaining dead space before the actual textual data
            
            elif line.startswith("Description:"):
                current["description"] = line.removeprefix("Description:").strip()

            elif line.startswith("Role:"):
                current["role"] = line.removeprefix("Role:").strip()

            elif line.startswith("Source Chunks:"):
                raw = line.removeprefix("Source Chunks:").strip()
                chunks = []

                for part in raw.split(","): # splits it wherever there is a comma.
                    part = part.strip() # breaks the text into individual pieces

                    if "-" in part:
                        start, end = map(int, part.split("-")) # Splits to find the starting point and the ending point.
                        chunks.extend(range(start, end + 1)) # Adds numbers in between (+1 cause python).

                    else:
                        chunks.append(int(part))
                
                current["source_chunks"] = chunks
                topics.append(OutlineTopic(**current))
                current = {}

        return topics


