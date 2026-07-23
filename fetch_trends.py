#!/usr/bin/env python3
"""Fetch the current top Google Search trends via Google Trends."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trendspyg import download_google_trends_csv, download_google_trends_rss


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gather the most popular Google Search trends for a region.",
    )
    parser.add_argument(
        "--geo",
        default="US",
        help="Region code (e.g. US, GB, CA, DE, JP). Default: US",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of top trends to return (default: 20)",
    )
    parser.add_argument(
        "--output",
        default="./trends.txt",
        help="Path to save the trends text file (default: ./trends.txt)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        choices=(4, 24, 48, 168),
        help="Trending window in hours for CSV source (default: 24)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the 5-minute RSS cache (RSS fallback only)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print the summary to the terminal",
    )
    return parser.parse_args(argv)


def _normalize_and_rank(envelope: dict, geo: str, limit: int) -> dict:
    trends = list(envelope.get("trends") or [])

    # Highest search volume first (most trending on top).
    trends = sorted(
        trends,
        key=lambda t: (t.get("volume_min") or 0, -(t.get("rank") or 0)),
        reverse=True,
    )
    if limit > 0:
        trends = trends[:limit]

    for index, trend in enumerate(trends, start=1):
        trend["rank"] = index

    return {
        "schema_version": envelope.get("schema_version"),
        "source": envelope.get("source", "csv"),
        "geo": envelope.get("geo", geo),
        "fetched_at": envelope.get("fetched_at"),
        "count": len(trends),
        "trends": trends,
    }


def fetch_trends(geo: str, limit: int, hours: int = 24, cache: bool = True) -> dict:
    """Prefer CSV (hundreds of trends); fall back to RSS (~10) if Chrome fails."""
    try:
        envelope = download_google_trends_csv(
            geo=geo,
            hours=hours,
            normalize=True,
            output_format="dict",
            headless=True,
        )
        if not isinstance(envelope, dict):
            raise TypeError(f"Unexpected CSV response type: {type(envelope)!r}")
        return _normalize_and_rank(envelope, geo, limit)
    except Exception as csv_error:
        print(
            f"CSV trends unavailable ({csv_error}); falling back to RSS (~10 items)...",
            file=sys.stderr,
        )
        envelope = download_google_trends_rss(geo=geo, normalize=True, cache=cache)
        return _normalize_and_rank(envelope, geo, limit)


def format_trends_text(payload: dict) -> str:
    lines = [
        f"Top {payload['count']} Google Search trends ({payload['geo']})",
        f"Fetched: {payload.get('fetched_at') or 'unknown'}",
        "",
    ]
    for trend in payload["trends"]:
        rank = trend.get("rank", "?")
        keyword = trend.get("keyword", "?")
        volume = trend.get("volume_text") or trend.get("volume_min") or ""
        line = f"{rank}. {keyword}"
        if volume:
            line += f"  ({volume})"
        lines.append(line)

        news = trend.get("news") or []
        if news:
            headline = news[0].get("headline") or news[0].get("title")
            if headline:
                lines.append(f"   {headline}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.limit < 1:
        raise SystemExit("--limit must be >= 1")

    try:
        payload = fetch_trends(
            args.geo.upper(),
            args.limit,
            hours=args.hours,
            cache=not args.no_cache,
        )
    except Exception as exc:
        raise SystemExit(f"Failed to fetch Google Trends: {exc}") from exc

    text = format_trends_text(payload)
    if not args.quiet:
        print(text, end="")

    path = Path(args.output).expanduser().resolve()
    path.write_text(text, encoding="utf-8")
    print(f"Saved trends to {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
