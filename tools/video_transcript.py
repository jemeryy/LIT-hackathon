"""Fetch a cleaned, timestamped YouTube transcript as [m:ss] text lines.

Primary: youtube-transcript-api (no key). Fallback: yt-dlp auto-subs via the
tv player client (dodges the bot wall), then VTT -> deduped timestamped text.
Subs are written to a temp dir, never the repo.

Usage:
  python tools/video_transcript.py <url_or_video_id> [--out FILE] [--fallback-only]
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

TIME_RE = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,]\d{3}\s+-->")
TAG_RE = re.compile(r"<[^>]+>")


def video_id(s: str) -> str:
    s = s.strip()
    if "youtu.be/" in s:
        return s.split("youtu.be/")[1].split("?")[0].split("&")[0]
    if "watch?v=" in s:
        return urllib.parse.parse_qs(urllib.parse.urlparse(s).query).get("v", [""])[0]
    if "/embed/" in s:
        return s.split("/embed/")[1].split("?")[0].split("&")[0]
    if "/shorts/" in s:
        return s.split("/shorts/")[1].split("?")[0].split("&")[0]
    return s  # assume a bare id


def ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"[{h}:{m:02d}:{s:02d}]" if h else f"[{m}:{s:02d}]"


def via_api(vid: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    langs = ["en", "en-US", "en-GB"]
    try:  # v1.x instance API
        fetched = YouTubeTranscriptApi().fetch(vid, languages=langs)
    except AttributeError:  # v0.6.x classmethod API
        fetched = YouTubeTranscriptApi.get_transcript(vid, languages=langs)
    out, last = [], None
    for sn in fetched:
        text = (sn.get("text") if isinstance(sn, dict) else getattr(sn, "text", "")) or ""
        text = " ".join(text.split())
        start = float(sn.get("start", 0) if isinstance(sn, dict) else getattr(sn, "start", 0))
        if text and text != last:
            out.append(f"{ts(start)} {text}")
            last = text
    if not out:
        raise RuntimeError("API returned an empty transcript")
    return "\n".join(out)


def clean_vtt(raw: str) -> str:
    out, last, start = [], None, None
    for line in raw.splitlines():
        m = TIME_RE.match(line.strip())
        if m:
            start = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        if start is None:  # WEBVTT header block
            continue
        text = html.unescape(TAG_RE.sub("", line)).strip()
        if not text or text == last:  # auto-subs repeat lines heavily
            continue
        out.append(f"{ts(start)} {text}")
        last = text
    if not out:
        raise RuntimeError("VTT parsed to no text lines")
    return "\n".join(out)


def via_ytdlp(vid: str) -> str:
    tmp = Path(tempfile.mkdtemp(prefix="vt_"))
    cmd = [
        "yt-dlp", "--skip-download", "--write-auto-sub", "--sub-lang", "en",
        "--extractor-args", "youtube:player_client=tv", "--ignore-no-formats-error",
        "-o", "sub_%(id)s", f"https://www.youtube.com/watch?v={vid}",
    ]
    r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    vtt = next(tmp.glob("*.vtt"), None)
    if vtt is None:
        raise RuntimeError(f"yt-dlp wrote no .vtt (no English auto-subs?): {r.stderr.strip()[-200:]}")
    return clean_vtt(vtt.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch a cleaned [m:ss]-timestamped YouTube transcript.")
    ap.add_argument("video", help="YouTube URL or bare video id")
    ap.add_argument("--out", help="write transcript to this file (default: stdout)")
    ap.add_argument("--fallback-only", action="store_true", help="skip the API path, force the yt-dlp VTT fallback")
    args = ap.parse_args()

    vid = video_id(args.video)
    text, api_err = None, None
    if not args.fallback_only:
        try:
            text = via_api(vid)
        except Exception as e:
            api_err = e
    if text is None:
        try:
            text = via_ytdlp(vid)
        except Exception as e:
            detail = f"api: {api_err}; yt-dlp: {e}" if api_err else f"yt-dlp: {e}"
            print(f"ERROR: transcript fetch failed for {vid} ({detail})", file=sys.stderr)
            return 1

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out} ({text.count(chr(10)) + 1} lines)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
