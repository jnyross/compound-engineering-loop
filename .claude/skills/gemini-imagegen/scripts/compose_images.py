#!/usr/bin/env python3
"""
Compose multiple images into a new image using Gemini API.

Usage:
    python compose_images.py "instruction" output.png image1.png [image2.png ...]

Examples:
    python compose_images.py "Create a group photo of these people" group.png person1.png person2.png
    python compose_images.py "Put the cat from the first image on the couch from the second" result.png cat.png couch.png
    python compose_images.py "Apply the art style from the first image to the scene in the second" styled.png style.png photo.png

Note: Supports up to 14 reference images (Gemini 3 Pro only).

Environment:
    GEMINI_API_KEY - Required API key
"""

import argparse
import sys

from gemini_images import GeminiImageGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Compose multiple images using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("instruction", help="Composition instruction")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("images", nargs="+", help="Input images (up to 14)")
    parser.add_argument(
        "--model", "-m",
        default="gemini-3-pro-image-preview",
        choices=["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
        help="Model to use (pro recommended for composition)"
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
        output, text = gen.compose(
            instruction=args.instruction,
            images=args.images,
            output=args.output,
            aspect_ratio=args.aspect,
            image_size=args.size,
        )

        print(f"Composed image saved to: {output}")
        if text:
            print(f"Model response: {text}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
