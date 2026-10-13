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
2. Ensure you have a folder named `images` (or another name of your choice, but remember to update the `OUTPUT_DIR` constant in the script accordingly) in the same directory as the script. This is where the extracted images will be saved.
3. Update the `PDF_PATH` constant in the script to point to your target PDF file.
4. Run the script:
```
python main.py input_file output_dir img_format img_quality
```

After execution, check the `images` folder for the extracted images.

For example, you can extract to png in the current folder via:

```
python main.py ./file.pdf ./ png 100
```


## Customization

- **Changing Output Image Format**: By default, images are saved in the `.webp` format due to its efficiency. However, you can modify the `save_page_images` function to save in a different format, such as PNG or JPEG.
- **Adjusting Resizing Ratio**: The `resize_image` function currently reduces the image size to 60% of the original. Adjust the resizing ratio as per your requirements by modifying the multiplier value.

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
