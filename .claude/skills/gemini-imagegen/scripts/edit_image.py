#!/usr/bin/env python3
"""
Edit existing images using Gemini API.

Usage:
    python edit_image.py input.png "edit instruction" output.png [options]

Examples:
    python edit_image.py photo.png "Add a rainbow in the sky" edited.png
    python edit_image.py room.jpg "Change the sofa to red leather" room_edited.jpg
    python edit_image.py portrait.png "Make it look like a Van Gogh painting" artistic.png --model gemini-3-pro-image-preview

Environment:
    GEMINI_API_KEY - Required API key
"""

import argparse
import sys

from gemini_images import GeminiImageGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Edit images using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("input", help="Input image path")
    parser.add_argument("instruction", help="Edit instruction")
    parser.add_argument("output", help="Output file path")
    parser.add_argument(
        "--model", "-m",
        default="gemini-2.5-flash-image",
        choices=["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
        help="Model to use (default: gemini-2.5-flash-image)"
    )
    parser.add_argument(
        "--aspect", "-a",
        choices=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        help="Output aspect ratio"
    )
    parser.add_argument(
        "--size", "-s",
        choices=["1K", "2K", "4K"],
        help="Output resolution"
    )

    args = parser.parse_args()

    try:
        gen = GeminiImageGenerator(model=args.model)
        output, text = gen.edit(
            input_image=args.input,
            instruction=args.instruction,
            output=args.output,
            aspect_ratio=args.aspect,
            image_size=args.size,
        )

        print(f"Edited image saved to: {output}")
        if text:
            print(f"Model response: {text}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
