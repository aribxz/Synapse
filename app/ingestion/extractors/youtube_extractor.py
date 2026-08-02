import os
import re
from urllib.parse import parse_qs, urlparse

import requests

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    IpBlocked,
    RequestBlocked,
    PoTokenRequired,
    TranscriptsDisabled,
    NoTranscriptFound,
    InvalidVideoId,
)
from youtube_transcript_api.formatters import TextFormatter

from app.ingestion.base_extractor import BaseExtractor
from app.llm.gemini_client import GeminiClient
from app.models.knowledge_source import KnowledgeSource


HOSTED_SERVICE_URL = os.getenv(
    "YOUTUBE_TRANSCRIPT_SERVICE_URL", "https://youtube-transcript.ai"
)

_TRANSCRIPT_CACHE = {}


class YouTubeExtractionError(Exception):
    def __init__(self, reason: str, detail: str):
        self.reason = reason
        self.detail = detail
        super().__init__(detail)

    def __str__(self):
        return self.reason


def extract_video_id_from_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.lstrip("/")

    if parsed.netloc and "youtube.com" in parsed.netloc:
        query_params = parse_qs(parsed.query)
        if "v" in query_params and query_params["v"]:
            return query_params["v"][0]

    return url


def _friendly_reason(exc: Exception) -> str:
    if isinstance(exc, (IpBlocked, RequestBlocked)):
        return "YouTube blocked this server's IP"
    if isinstance(exc, PoTokenRequired):
        return "YouTube requires bot verification for this video"
    if isinstance(exc, (TranscriptsDisabled, NoTranscriptFound)):
        return "This video has no captions"
    if isinstance(exc, InvalidVideoId):
        return "Invalid YouTube link"
    return None


def _fetch_via_gemini(video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    client = GeminiClient()
    text = client.transcribe_youtube(url)
    if len(text.split()) < 50:
        raise ValueError("Gemini transcript too short to be usable")
    return text


def _fetch_direct(video_id: str) -> str:
    yt_api = YouTubeTranscriptApi()
    transcript_data = yt_api.fetch(video_id)
    formatter = TextFormatter()
    return formatter.format_transcript(transcript_data)


def _parse_hosted_transcript(raw_text: str) -> str:
    idx = raw_text.find("## Transcript")
    if idx == -1:
        ts = re.search(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", raw_text)
        idx = ts.start() if ts else 0

    body = raw_text[idx:]
    body = re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", " ", body)
    body = body.replace("[", " ").replace("]", " ")
    body = body.replace("\r", " ")
    return re.sub(r"\s+", " ", body).strip()


def _fetch_hosted(video_id: str) -> str:
    url = f"{HOSTED_SERVICE_URL}/transcript/{video_id}.txt"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    text = _parse_hosted_transcript(response.text)
    if len(text.split()) < 50:
        raise ValueError("Hosted service returned no usable transcript")

    return text


def _fetch_home_helper(video_id: str) -> str:
    helper_url = os.getenv("HOME_HELPER_URL", "").strip().rstrip("/")
    if not helper_url:
        raise RuntimeError("HOME_HELPER_URL not set")

    response = requests.get(f"{helper_url}/transcript/{video_id}", timeout=15)
    response.raise_for_status()

    text = response.text.strip()
    if len(text.split()) < 50:
        raise ValueError("Home helper returned no usable transcript")

    return text


def _fetch_transcript(video_id: str) -> str:
    steps = [
        ("gemini", _fetch_via_gemini),
        ("direct", _fetch_direct),
        ("free hosted service", _fetch_hosted),
        ("home helper", _fetch_home_helper),
    ]

    failures = []
    direct_reason = None

    for name, step in steps:
        try:
            return step(video_id)
        except Exception as exc:
            reason = _friendly_reason(exc)
            if name == "direct" and reason:
                direct_reason = reason
            failures.append(f"{name}: {reason or exc}")

    raise YouTubeExtractionError(
        direct_reason or "Could not retrieve the video transcript",
        " | ".join(failures),
    )


class YouTubeExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        video_id = extract_video_id_from_url(source.metadata["url"])

        cached = _TRANSCRIPT_CACHE.get(video_id)
        if cached:
            source.raw_content = cached
            return source

        text = _fetch_transcript(video_id)

        _TRANSCRIPT_CACHE[video_id] = text
        source.raw_content = text.replace("\n", " ")

        return source
