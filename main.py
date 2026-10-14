"""Backwards compatible entry point: `python main.py input_file output_dir img_format img_quality`."""
import sys

from pdf_image_extractor.cli import main

if __name__ == "__main__":
    sys.exit(main())
