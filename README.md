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

## Usage

1. Clone the repository or download the script.
2. Ensure you have a folder named `images` (or another name of your choice, but remember to update the `OUTPUT_DIR` constant in the script accordingly) in the same directory as the script. This is where the extracted images will be saved.
3. Update the `PDF_PATH` constant in the script to point to your target PDF file.
4. Run the script:
```
python pdf_image_extractor.py
```

After execution, check the `images` folder for the extracted images.

## Customization

- **Changing Output Image Format**: By default, images are saved in the `.webp` format due to its efficiency. However, you can modify the `save_page_images` function to save in a different format, such as PNG or JPEG.
- **Adjusting Resizing Ratio**: The `resize_image` function currently reduces the image size to 60% of the original. Adjust the resizing ratio as per your requirements by modifying the multiplier value.
