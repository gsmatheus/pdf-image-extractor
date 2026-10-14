# PDF Image Extractor

## Overview

The PDF Image Extractor is a Python script designed to process PDF files, specifically extracting and saving images embedded within the pages of the document. Besides the image extraction, it also prints out the textual content of the pages. This tool can be particularly useful when handling digital catalogs or any PDFs with important embedded images.

## Features

- **Image Extraction**: Efficiently extracts images from any page within a provided PDF.
- **Image Resizing**: Automatically resizes the extracted images to 70% of their original size, ensuring consistent output and potentially reducing file size.
- **Text Extraction**: For each processed page, the script also extracts and prints the textual content.
- **Flexibility**: Designed with modularity in mind, making it easy to integrate, expand, or modify for various use cases.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip`

```bash
uv sync
```

## Usage

```bash
uv run pdf-image-extractor input_file output_dir img_format img_quality [--min_size MIN] [--pages PAGES] [--password PASSWORD]
```

`python main.py ...` and `python -m pdf_image_extractor ...` work too.

- `img_format`: `png`, `jpeg` (or `jpg`), `webp`, ... Anything Pillow can write.
- `img_quality`: integer passed to Pillow (used by JPEG/WebP, ignored by PNG).
- `--min_size`: (Optional) Minimum width/height for images to extract (default: 500).
- `--pages`: (Optional) Comma-separated list or range of page numbers to process (e.g., `1,3,5` or `2-4`).
- `--password`: (Optional) Password for encrypted PDFs.

If the output directory does not exist, it is created. Images are saved as `<digits of the page text>_<page>_<image>.<format>` (page and image numbers start at 1; `<image>` is the position of the image on the page, so it can skip numbers when small images are filtered out). When the page text has no digits, as in scans, the prefix is `page`, e.g. `page_3_1.png`.

**Example:**

```bash
uv run pdf-image-extractor ./file.pdf ./images png 100 --min_size 600 --pages 1,3,5
```

Errors (missing file, password-protected or corrupted PDF, wrong password, bad options) exit with a non-zero status and a message on stderr.

When the run finishes, a one-line summary goes to stderr (stdout is unchanged), e.g. `Done: 12 images from 40 pages. No images on pages 2, 5, 9.` It also counts skipped images.

An image that cannot be decoded is skipped with a `Warning:` on stderr and the run carries on with the rest of the document (exit status stays 0).

### As a library

```python
from pdf_image_extractor import extract

for page in extract("catalog.pdf", "images", "webp", 85, min_size=500, pages="1-3"):
    print(page.number, page.text[:40], page.images, page.warnings)
```

## Customization

- **Resizing ratio**: `RESIZE_RATIO` in `pdf_image_extractor/core.py` (default `0.7`, i.e. the larger side is scaled to 70%).
- **Filename prefix length**: `MAX_REFERENCE_BYTES` in the same file.

## Tests

The test PDFs are generated on the fly by `tests/pdf_factory.py` (text-only, scans, several images per page, JPEG/CMYK/alpha/1-bit images, rotated pages, odd filenames, encrypted and corrupted files, ...), so no binaries are committed.

```
uv sync
uv run pytest
```

To write all the sample PDFs to disk and try the CLI by hand:

```
uv run python tests/pdf_factory.py tests/fixtures
```

Tests marked `xfail` document known bugs; fixing one makes it fail until the marker is removed.
