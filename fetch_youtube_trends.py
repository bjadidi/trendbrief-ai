#!/usr/bin/env python3
"""Fetch top trending YouTube videos via the YouTube Data API v3."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://www.googleapis.com/youtube/v3/videos"
MAX_RESULTS = 50


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch YouTube's most popular (trending) videos for a region.",
    )
    parser.add_argument(
        "--geo",
        default="US",
        help="Region code (ISO 3166-1 alpha-2, e.g. US, CA, GB). Default: US",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help=f"Number of videos to return (default: 20, max: {MAX_RESULTS})",
    )
    parser.add_argument(
        "--output",
        default="./youtube_trends.txt",
        help="Path to save the trends text file (default: ./youtube_trends.txt)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="YouTube Data API key (default: YOUTUBE_API_KEY env var)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print the summary to the terminal",
    )
    return parser.parse_args(argv)


def resolve_api_key(cli_key: str | None) -> str:
    key = (cli_key or os.environ.get("YOUTUBE_API_KEY") or "").strip()
    if key:
        return key
    raise SystemExit(
        "Missing YouTube API key.\n"
        "1. Create a Google Cloud project\n"
        "2. Enable YouTube Data API v3\n"
        "3. Create an API key\n"
        "4. Run: export YOUTUBE_API_KEY='your-key'\n"
        "   Or pass: --api-key your-key"
    )


def fetch_trending_videos(api_key: str, geo: str, limit: int) -> list[dict]:
    response = requests.get(
        API_URL,
        params={
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": geo,
            "maxResults": limit,
            "key": api_key,
        },
        timeout=30,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON from YouTube API (HTTP {response.status_code})") from exc

    if response.status_code != 200:
        error = payload.get("error") or {}
        message = error.get("message") or response.text
        raise RuntimeError(f"YouTube API error (HTTP {response.status_code}): {message}")

    videos: list[dict] = []
    for item in payload.get("items") or []:
        snippet = item.get("snippet") or {}
        stats = item.get("statistics") or {}
        video_id = item.get("id") or ""
        videos.append(
            {
                "id": video_id,
                "title": snippet.get("title") or "(untitled)",
                "channel": snippet.get("channelTitle") or "(unknown)",
                "views": int(stats["viewCount"]) if stats.get("viewCount") else None,
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            }
        )
    return videos


def format_views(views: int | None) -> str:
    if views is None:
        return "n/a"
    return f"{views:,}"


def format_trends_text(geo: str, videos: list[dict], fetched_at: str) -> str:
    lines = [
        f"Top {len(videos)} YouTube trending videos ({geo})",
        f"Fetched: {fetched_at}",
        "",
    ]
    for index, video in enumerate(videos, start=1):
        lines.append(f"{index}. {video['title']}")
        lines.append(
            f"   Channel: {video['channel']}  |  Views: {format_views(video['views'])}"
        )
        if video["url"]:
            lines.append(f"   {video['url']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.limit < 1 or args.limit > MAX_RESULTS:
        raise SystemExit(f"--limit must be between 1 and {MAX_RESULTS}")

    api_key = resolve_api_key(args.api_key)
    geo = args.geo.upper()

    try:
        videos = fetch_trending_videos(api_key, geo, args.limit)
    except Exception as exc:
        raise SystemExit(f"Failed to fetch YouTube trending videos: {exc}") from exc

    fetched_at = datetime.now(timezone.utc).isoformat()
    text = format_trends_text(geo, videos, fetched_at)

    if not args.quiet:
        print(text, end="")

    path = Path(args.output).expanduser().resolve()
    path.write_text(text, encoding="utf-8")
    print(f"Saved YouTube trends to {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
