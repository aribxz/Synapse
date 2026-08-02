"""Home-PC transcript helper for Synapse.

Run this on a computer with a normal home internet connection (where YouTube
doesn't block transcript requests). A deployed Synapse instance can fall back to
this machine when YouTube blocks the cloud server's IP.

Setup:
  cd C:\\Users\\ASUS\\Documents\\Python\\Synapse
  .venv\\Scripts\\activate
  python home_helper.py

Expose it to your deployed app (pick one):
  Option A (easiest, free): install Tailscale on this PC (https://tailscale.com).
      The PC gets a stable address like 100.x.y.z. No router/port-forwarding needed.
  Option B: forward a port on your home router to this PC (port 5055).

Then set the environment variable on Render:
  HOME_HELPER_URL=http://100.x.y.z:5055
"""

from urllib.parse import parse_qs, urlparse

from flask import Flask

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

app = Flask(__name__)


def extract_video_id_from_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.lstrip("/")

    if parsed.netloc and "youtube.com" in parsed.netloc:
        query_params = parse_qs(parsed.query)
        if "v" in query_params and query_params["v"]:
            return query_params["v"][0]

    return url


@app.route("/health")
def health():
    return "ok"


@app.route("/transcript/<video_id>")
def transcript(video_id):
    try:
        yt_api = YouTubeTranscriptApi()
        transcript_data = yt_api.fetch(video_id)
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript_data)

        if len(text.strip()) < 200:
            return "No usable transcript found for this video.", 404

        return text.replace("\n", " ")

    except Exception as exc:
        return str(exc), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055)
