import argparse
import os
import re
import sys
from typing import Optional, Sequence

from .core import DEFAULT_MIN_SIZE, ExtractorError, extract, pillow_format

DESCRIPTION = (
    "The PDF Image Extractor is a Python script designed to process PDF files, specifically "
    "extracting and saving images embedded within the pages of the document. Besides the image "
    "extraction, it also prints out the textual content of the pages."
)


def page_spec(value: str) -> str:
    """argparse type: bad --pages input is a usage error, not a traceback."""
    if not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", value):
        raise argparse.ArgumentTypeError(
            f"invalid page selection '{value}' (expected e.g. 1,3,5 or 2-4)")
    return value


def image_format(value: str) -> str:
    """argparse type: validates the format but keeps the spelling (it becomes the file extension)."""
    try:
        pillow_format(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdf-image-extractor", description=DESCRIPTION)
    parser.add_argument("input_file")
    parser.add_argument("output_dir")
    parser.add_argument("img_format", type=image_format)
    parser.add_argument("img_quality", type=int)
    parser.add_argument("--min_size", type=int, default=DEFAULT_MIN_SIZE,
                        help=f"Minimum width/height for images to extract (default: {DEFAULT_MIN_SIZE})")
    parser.add_argument("--pages", type=page_spec, default=None,
                        help="Comma-separated list or range of page numbers to process, "
                             "e.g. 1,3,5 or 2-4 (default: all)")
    return parser


def error(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if not os.path.isfile(args.input_file):
        return error(f"Input PDF file '{args.input_file}' does not exist.")

    if not os.path.exists(args.output_dir):
        try:
            os.makedirs(args.output_dir)
            print(f"Created output directory: {args.output_dir}")
        except OSError as e:
            return error(f"Failed to create output directory '{args.output_dir}': {e}")

    try:
        for page in extract(args.input_file, args.output_dir, args.img_format,
                            args.img_quality, args.min_size, args.pages):
            print(f"Text on Page {page.number}:")
            print(page.text)
            print("-" * 50)
            for image in page.images:
                print(f"Image Saved: {image}")
            print("=" * 50)
    except ExtractorError as e:
        return error(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
