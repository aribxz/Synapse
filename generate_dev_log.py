import subprocess
import ollama
import datetime
import os

def get_git_changes():
    try:
        # Runs 'git diff HEAD' to see what changed compared to your last commit
        result = subprocess.run(
            ["git", "diff", "HEAD"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return "Error: Local Git tracking is not initialized or running properly."

def generate_markdown_summary(diff_text, day_num, phase_info, hours_worked):
    if not diff_text.strip():
        return "No changes detected since your last local commit point."
    
    current_date = datetime.date.today().strftime("%B %d, %Y")
    
    prompt = f"""
    You are an elite software engineering/machine learning mentor reviewing your student's daily work. 
    Analyze the provided local Git Diff changes and write a highly personalized, encouraging, 
    and deeply analytical development log in Markdown.

    Use this metadata at the very top:
    - Day: {day_num}
    - Phase: {phase_info}
    - Hours Worked: {hours_worked} hours
    - Date: {current_date}

    Follow this exact structural layout strictly:
    1. Title block matching the metadata format provided.
    2. 'What happened today, in one sentence?' (Make it punchy and impactful).
    3. 'The big problem you solved today:' (Frame the technical hurdle they overcame based on the code changes).
    4. 'The New Analogy:' (Create a clever, fitting real-world analogy like cooking, building, or assembly lines to explain the new architecture).
    5. 'What changed — file by file:' (List the specific files modified in the diff, marking new ones as [NEW] and altered ones as [Modified]. Explain what fields or logic changed).
    6. 'OOP / Code Concepts Introduced Today:' (A markdown table outlining patterns or syntax used in the diff).
    7. 'My opinion on Day {day_num}:' (Write an honest, insightful code review as a proud mentor. Include sections for 'What is going really well', 'Where to be careful now' regarding performance/edge-cases, and a 'Verdict' score).

    Make sure these are all well formatted and include good diagrams. The Architecture specifically should be well explained.
    Git Diff Data to Analyze:
    {diff_text}
    """
    
    # We use the specific Qwen model tag you just downloaded
    response = ollama.generate(model="qwen2.5-coder:7b-instruct-q4_K_M", prompt=prompt)
    return response["response"]

def main():
    print("--- End of Day Log Generator ---")
    day_num = input("What Day number is this? (e.g., 4): ")
    phase_info = input("What is the current Phase? (e.g., Part 3 — Intelligence Engine): ")
    hours_worked = input("How many hours did you work today? (e.g., ~3): ")
    
    print("\nReading local file changes...")
    changes = get_git_changes()
    
    print("Analyzing changes and generating your mentor-level markdown log...")
    markdown_log = generate_markdown_summary(changes, day_num, phase_info, hours_worked)
    
    # 1. Create the logs directory path string
    logs_folder = "logs"
    
    # 2. Automatically create the directory if it doesn't exist yet
    os.makedirs(logs_folder, exist_ok=True)
    
    # 3. Build the clean, custom filename requested
    filename = f"Day {day_num}.md"
    
    # 4. Safely join the folder path and filename together
    file_path = os.path.join(logs_folder, filename)
    
    # 5. Write the file into the logs folder
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_log)
    
    print(f"\nSuccess! '{filename}' has been saved inside the '{logs_folder}' folder.")

if __name__ == "__main__":
    main()