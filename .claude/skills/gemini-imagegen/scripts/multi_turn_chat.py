#!/usr/bin/env python3
"""
Interactive multi-turn image generation and refinement using Gemini API.

Usage:
    python multi_turn_chat.py [--model MODEL] [--output-dir DIR]

This starts an interactive session where you can:
- Generate images from prompts
- Iteratively refine images through conversation
- Load existing images for editing
- Save images at any point

Commands:
    /save [filename]  - Save current image
    /load <path>      - Load an image into the conversation
    /clear            - Start fresh conversation
    /quit             - Exit

Environment:
    GEMINI_API_KEY - Required API key
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from gemini_images import GeminiImageGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Interactive multi-turn image generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--model", "-m",
        default="gemini-2.5-flash-image",
        choices=["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
        help="Model to use"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Directory to save images"
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        gen = GeminiImageGenerator(model=args.model)
        chat = gen.chat()
    except Exception as e:
        print(f"Error initializing: {e}", file=sys.stderr)
        sys.exit(1)

    image_count = 0
    print(f"Gemini Image Chat ({args.model})")
    print("Commands: /save [name], /load <path>, /clear, /quit")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            if cmd == "/quit":
                print("Goodbye!")
                break

            elif cmd == "/clear":
                chat = gen.chat()
                print("Conversation cleared.")
                continue

            elif cmd == "/save":
                if chat.current_image is None:
                    print("No image to save.")
                    continue
                filename = arg
                if filename is None:
                    image_count += 1
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"image_{timestamp}_{image_count}.png"
                filepath = output_dir / filename
                chat.current_image.save(filepath)
                print(f"Image saved to: {filepath}")
                continue

            elif cmd == "/load":
                if not arg:
                    print("Usage: /load <path>")
                    continue
                try:
                    img = Image.open(arg)
                    chat.current_image = img
                    print(f"Loaded: {arg}")
                    print("You can now describe edits to make.")
                except Exception as e:
                    print(f"Error loading image: {e}")
                continue

            else:
                print(f"Unknown command: {cmd}")
                continue

        # Send message to model
        try:
            image_to_send = None
            if chat.current_image and not chat._chat.history:
                image_to_send = chat.current_image

            img, text = chat.send(user_input, image_to_send)

            if text:
                print(f"\nGemini: {text}")

            if img:
                image_count += 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_{timestamp}_{image_count}.png"
                filepath = output_dir / filename
                img.save(filepath)
                print(f"\n[Image generated: {filepath}]")

        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
