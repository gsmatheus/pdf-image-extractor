# PDF Image Extractor

## Overview

The PDF Image Extractor is a Python script designed to process PDF files, specifically extracting and saving images embedded within the pages of the document. Besides the image extraction, it also prints out the textual content of the pages. This tool can be particularly useful when handling digital catalogs or any PDFs with important embedded images.

## Features

- **Image Extraction**: Efficiently extracts images from any page within a provided PDF.
- **Image Resizing**: Automatically resizes the extracted images to 60% of their original size, ensuring consistent output and potentially reducing file size.
- **Text Extraction**: For each processed page, the script also extracts and prints the textual content.
- **Flexibility**: Designed with modularity in mind, making it easy to integrate, expand, or modify for various use cases.

## Requirements

To run this script, you will need:

- Python 3.x
- pdfplumber
- fitz (PyMuPDF)
- PIL (Pillow)

These can be installed using `pip`:

```
pip install pdfplumber pymupdf pillow
```

or if using [uv](https://docs.astral.sh/uv/)

```
uv synv
uv run main.py
```

## Usage

1. Clone the repository or download the script.
2. Run the script:

  ```bash
  python main.py input_file output_dir img_format img_quality [--min_size MIN] [--pages PAGES]
  ```

  - `--min_size`: (Optional) Minimum width/height for images to extract (default: 500).
  - `--pages`: (Optional) Comma-separated list or range of page numbers to process (e.g., `1,3,5` or `2-4`).

  If the output directory does not exist, it will be created automatically.

  **Example:**
  
  ```bash
  python main.py ./file.pdf ./ png 100 --min_size 600 --pages 1,3,5
  ```

## Customization

- **Changing Output Image Format**: By default, images are saved in the `.webp` format due to its efficiency. However, you can modify the `save_page_images` function to save in a different format, such as PNG or JPEG.
- **Adjusting Resizing Ratio**: The `resize_image` function currently reduces the image size to 60% of the original. Adjust the resizing ratio as per your requirements by modifying the multiplier value.
