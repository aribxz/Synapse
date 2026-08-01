import json, os
from flask import Blueprint, render_template, request, Response, stream_with_context, send_file

from app.controllers.input_controller import InputController

main_bp = Blueprint("main", __name__) # Name is just storing where the blueprint came from.
controller = InputController()

@main_bp.route("/")
def home():
    return render_template("index.html")

@main_bp.route("/about")
def about():
    return render_template("about.html")

@main_bp.route("/process", methods=["POST"])
def process():
    fast_model = request.form.get("fast_model", "gemini")
    print(f"--- Starting Processing Pipeline (fast model: {fast_model}) ---", flush=True)

    gen = controller.process_request(request, fast_model=fast_model)

    is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest" # Checks for JavaScript.

    if not is_xhr:
        try:
            while True:  # This generates the chunk and for each chunk the generate function retrives some information about it to be displayed at the frontend.
                pct, msg, title = next(gen)
        except StopIteration as e:
            output_file = e.value

        return send_file(output_file, as_attachment=True, download_name="notes.md", mimetype="text/markdown")

    def generate():
        nonlocal gen
        try:
            while True:
                pct, msg, title = next(gen)
                yield json.dumps({"pct": pct, "msg": msg, "title": title}) + "\n"  # Streaming.
        except StopIteration as e:
            output_file = e.value

        with open(output_file, "r", encoding="utf-8") as f: # Actual markdown.
            content = f.read()

        yield json.dumps({"type": "file", "content": content, "filename": "notes.md"}) + "\n" # See the content (important because the frontend receives it and sees that it is done. Notice that the frontend can only receive plain json that is why we do this).

    return Response(stream_with_context(generate()), mimetype="text/plain") # Offer it for download.

'''
Flow:
    First the generate() gets called
    it calls next(gen) -> that gets information about pct, msg, title
    back to generate() where it steams this response and gives the message to the frontend.
'''