#!/usr/bin/env python3
"""
Generate images from text prompts using Gemini API.

Usage:
    python generate_image.py "prompt" output.png [--model MODEL] [--aspect RATIO] [--size SIZE]

Examples:
    python generate_image.py "A cat in space" cat.png
    python generate_image.py "A logo for Acme Corp" logo.png --model gemini-3-pro-image-preview --aspect 1:1
    python generate_image.py "Epic landscape" landscape.png --aspect 16:9 --size 2K

Environment:
    GEMINI_API_KEY - Required API key
"""

import argparse
import sys

from gemini_images import GeminiImageGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate images from text prompts using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("prompt", help="Text prompt describing the image")
    parser.add_argument("output", help="Output file path (e.g., output.png)")
    parser.add_argument(
        "--model", "-m",
        default="gemini-2.5-flash-image",
        choices=["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
        help="Model to use (default: gemini-2.5-flash-image)"
    )
    parser.add_argument(
        "--aspect", "-a",
        choices=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        help="Aspect ratio"
    )
    parser.add_argument(
        "--size", "-s",
        choices=["1K", "2K", "4K"],
        help="Image resolution (4K only available with pro model)"
    )

    args = parser.parse_args()

    try:
        gen = GeminiImageGenerator(model=args.model)
        output, text = gen.generate(
            prompt=args.prompt,
            output=args.output,
            aspect_ratio=args.aspect,
            image_size=args.size,
        )

        print(f"Image saved to: {output}")
        if text:
            print(f"Model response: {text}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
