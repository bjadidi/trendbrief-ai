#!/usr/bin/env python3
"""Generate a NotebookLM Video Overview from a URL, file, or text source."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

from notebooklm import AuthError, NotebookLMClient, VideoFormat, VideoStyle

VIDEO_FORMATS = {
    "explainer": VideoFormat.EXPLAINER,
    "brief": VideoFormat.BRIEF,
    "cinematic": VideoFormat.CINEMATIC,
}

VIDEO_STYLES = {
    "auto": VideoStyle.AUTO_SELECT,
    "custom": VideoStyle.CUSTOM,
    "classic": VideoStyle.CLASSIC,
    "whiteboard": VideoStyle.WHITEBOARD,
    "kawaii": VideoStyle.KAWAII,
    "anime": VideoStyle.ANIME,
    "watercolor": VideoStyle.WATERCOLOR,
    "retro-print": VideoStyle.RETRO_PRINT,
    "heritage": VideoStyle.HERITAGE,
    "paper-craft": VideoStyle.PAPER_CRAFT,
}

STYLE_IGNORED_FORMATS = {"cinematic"}
DEFAULT_TIMEOUT_VIDEO = 1800
DEFAULT_TIMEOUT_CINEMATIC = 3600


def default_title_from_args(args: argparse.Namespace) -> str:
    if args.url:
        host = urlparse(args.url).netloc or "url"
        return f"Video from {host}"
    if args.file:
        return f"Video from {Path(args.file).name}"
    snippet = (args.text or "").strip().splitlines()[0][:60]
    return snippet or "Generated video"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a NotebookLM notebook, add a source, generate a video, and download the MP4.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Web or YouTube URL to use as the source")
    source.add_argument("--file", help="Local file path (PDF, text, etc.) to upload as the source")
    source.add_argument("--text", help="Pasted text content to use as the source")

    parser.add_argument("--title", help="Notebook title (default: derived from the source)")
    parser.add_argument("--instructions", default="", help="Optional instructions for the video")
    parser.add_argument(
        "--format",
        choices=sorted(VIDEO_FORMATS),
        default="explainer",
        help="Video format (default: explainer)",
    )
    parser.add_argument(
        "--style",
        choices=sorted(VIDEO_STYLES),
        default="whiteboard",
        help="Visual style (default: whiteboard; ignored for cinematic)",
    )
    parser.add_argument(
        "--style-prompt",
        default=None,
        help="Custom style prompt (required when --style custom)",
    )
    parser.add_argument("--language", default="en", help="Output language code (default: en)")
    parser.add_argument(
        "--output",
        default="./output.mp4",
        help="Output MP4 path (default: ./output.mp4)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "Seconds to wait for generation "
            f"(default: {DEFAULT_TIMEOUT_VIDEO}, or {DEFAULT_TIMEOUT_CINEMATIC} for cinematic)"
        ),
    )
    args = parser.parse_args(argv)

    cli_args = argv if argv is not None else sys.argv[1:]
    style_explicit = any(a == "--style" or a.startswith("--style=") for a in cli_args)

    if args.format in STYLE_IGNORED_FORMATS and style_explicit:
        parser.error(f"--style is not supported with --format {args.format}")

    if args.style == "custom" and not args.style_prompt:
        parser.error("--style-prompt is required when --style custom")

    if args.style_prompt and args.style != "custom":
        parser.error("--style-prompt can only be used with --style custom")

    if args.format in STYLE_IGNORED_FORMATS and args.style_prompt:
        parser.error(f"--style-prompt is not supported with --format {args.format}")

    if args.file and not Path(args.file).is_file():
        parser.error(f"File not found: {args.file}")

    if args.title is None:
        args.title = default_title_from_args(args)

    if args.timeout is None:
        args.timeout = (
            DEFAULT_TIMEOUT_CINEMATIC if args.format == "cinematic" else DEFAULT_TIMEOUT_VIDEO
        )

    return args


async def add_source(client: NotebookLMClient, notebook_id: str, args: argparse.Namespace) -> None:
    if args.url:
        print(f"Adding URL source: {args.url}")
        await client.sources.add_url(notebook_id, args.url, wait=True)
        return
    if args.file:
        path = Path(args.file)
        print(f"Uploading file source: {path}")
        await client.sources.add_file(notebook_id, path, wait=True)
        return
    print("Adding text source")
    await client.sources.add_text(notebook_id, args.title, args.text, wait=True)


async def generate(args: argparse.Namespace) -> str:
    video_format = VIDEO_FORMATS[args.format]
    kwargs: dict = {
        "instructions": args.instructions or None,
        "video_format": video_format,
        "language": args.language,
    }

    if args.format not in STYLE_IGNORED_FORMATS:
        kwargs["video_style"] = VIDEO_STYLES[args.style]
        if args.style == "custom":
            kwargs["style_prompt"] = args.style_prompt

    try:
        async with NotebookLMClient.from_storage() as client:
            print(f"Creating notebook: {args.title}")
            nb = await client.notebooks.create(args.title)
            print(f"Notebook ID: {nb.id}")

            await add_source(client, nb.id, args)

            print(
                f"Generating video (format={args.format}"
                + (f", style={args.style}" if args.format not in STYLE_IGNORED_FORMATS else "")
                + ")..."
            )
            status = await client.artifacts.generate_video(nb.id, **kwargs)

            print(f"Waiting for completion (timeout={args.timeout:.0f}s)...")
            final = await client.artifacts.wait_for_completion(
                nb.id,
                status.task_id,
                timeout=args.timeout,
            )
            if not final.is_complete:
                detail = final.error or final.status
                raise RuntimeError(f"Video generation did not complete: {detail}")

            output = str(Path(args.output).expanduser().resolve())
            print(f"Downloading video to {output}...")
            path = await client.artifacts.download_video(nb.id, output)
            return path
    except FileNotFoundError as exc:
        raise SystemExit(
            "NotebookLM auth storage not found.\n"
            "Run: notebooklm login\n"
            "Then: notebooklm auth check --test"
        ) from exc
    except AuthError as exc:
        raise SystemExit(
            f"Authentication error: {exc}\n"
            "Try: notebooklm login && notebooklm auth check --test"
        ) from exc


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path = asyncio.run(generate(args))
    print(f"Done: {path}")


if __name__ == "__main__":
    main()
