import io
import os
from dataclasses import dataclass, field
from typing import Iterator, Optional

import fitz
import pdfplumber
from PIL import Image

# Longest filename prefix (in bytes) built from the page text; filesystems cap names at 255 bytes.
MAX_REFERENCE_BYTES = 100
DEFAULT_MIN_SIZE = 500
# Extracted images are scaled so that their larger side is this fraction of the original.
RESIZE_RATIO = 0.7


class ExtractorError(Exception):
    """A problem with the input that the user can act on (bad file, bad option)."""


@dataclass
class PageResult:
    number: int  # 1-based
    text: str
    images: list[str] = field(default_factory=list)
    # Images of this page that could not be processed (corrupt data, unsupported encoding...).
    warnings: list[str] = field(default_factory=list)


def remove_letters(text: str) -> str:
    """Removes all letters from a string."""
    return ''.join([c for c in text if not c.isalpha()])


def sanitize_filename(text: str, max_bytes: int = MAX_REFERENCE_BYTES) -> str:
    """Sanitizes a string to be used as (part of) a filename."""
    # Remove newlines and trim whitespace
    text = text.replace('\n', '').strip()
    # Remove invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '')
    # Collapse runs of whitespace
    text = ' '.join(text.split())
    # Keep the result well below the filesystem's filename length limit
    text = text.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
    return text.strip()


def pillow_format(name: str) -> str:
    """Maps a user supplied format ('png', 'jpg', ...) to Pillow's save format.

    Raises ValueError if Pillow cannot write it.
    """
    Image.init()
    fmt = name.strip().upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt not in Image.SAVE:
        raise ValueError(f"unsupported image format '{name}' (try png, jpeg, webp)")
    return fmt


def parse_pages(spec: Optional[str], total_pages: int) -> list[int]:
    """Turns '1,3,5' / '2-4' (1-based) into sorted 0-based indices inside the document."""
    if not spec:
        return list(range(total_pages))
    pages = set()
    for part in spec.split(","):
        if "-" in part:
            start, end = part.split("-")
            pages.update(range(int(start) - 1, int(end)))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total_pages)


def resize_image(image: Image.Image) -> Image.Image:
    """Scales the image so that its larger side is RESIZE_RATIO of the original."""
    max_size = int(max(image.width, image.height) * RESIZE_RATIO)
    if image.width > max_size or image.height > max_size:
        if image.width > image.height:
            aspect_ratio = image.height / image.width
            new_width = max_size
            new_height = int(max_size * aspect_ratio)
        else:
            aspect_ratio = image.width / image.height
            new_height = max_size
            new_width = int(max_size * aspect_ratio)
        image = image.resize((new_width, new_height), Image.Resampling.BICUBIC)
    return image


def save_images_from_page(document: fitz.Document, page_number: int, reference: str,
                          output_dir: str, image_format: str, quality: int,
                          min_size: int = DEFAULT_MIN_SIZE,
                          warnings: Optional[list[str]] = None) -> list[str]:
    """Saves every image of a page that is at least ``min_size`` on both sides.

    Files are named ``<reference>_<page>_<image>.<image_format>`` (1-based numbers).
    An image that cannot be decoded or written is skipped and described in
    ``warnings`` (when given) so that one bad image does not abort the whole run.
    Returns the list of saved filenames.
    """
    saved_images = []
    page = document.load_page(page_number)
    safe_reference = sanitize_filename(reference)
    save_as = pillow_format(image_format)

    for img_index, img in enumerate(page.get_images(full=True)):
        filename = os.path.join(
            output_dir, f"{safe_reference}_{page_number + 1}_{img_index + 1}.{image_format}")
        try:
            image_bytes = document.extract_image(img[0])["image"]
            image = Image.open(io.BytesIO(image_bytes))
            if image.width < min_size or image.height < min_size:
                continue
            image = resize_image(image)  # decodes the pixels, so corrupt data fails here
            try:
                image.save(filename, save_as, quality=quality)
            except Exception:
                if os.path.exists(filename):
                    os.remove(filename)  # drop the half-written file
                raise
        except Exception as e:
            if warnings is not None:
                warnings.append(f"page {page_number + 1}, image {img_index + 1}: "
                                f"skipped ({type(e).__name__}: {e})")
            continue
        saved_images.append(filename)

    return saved_images


def extract(pdf_path: str, output_dir: str, image_format: str, quality: int,
            min_size: int = DEFAULT_MIN_SIZE, pages: Optional[str] = None,
            password: Optional[str] = None) -> Iterator[PageResult]:
    """Yields the text and saved images of each selected page, in order.

    Raises ExtractorError if the PDF cannot be opened, or is password protected and
    ``password`` is missing or wrong.
    """
    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        raise ExtractorError(f"could not open '{pdf_path}' as a PDF: {e}") from e
    try:
        if document.needs_pass:
            if password is None:
                raise ExtractorError(
                    f"'{pdf_path}' is password protected (use --password)")
            if not document.authenticate(password):
                raise ExtractorError(f"wrong password for '{pdf_path}'")
        try:
            pdf = pdfplumber.open(pdf_path, password=password)
        except Exception as e:
            raise ExtractorError(f"could not read '{pdf_path}': {e}") from e
        with pdf:
            for index in parse_pages(pages, len(pdf.pages)):
                text = (pdf.pages[index].extract_text() or "").strip()
                warnings: list[str] = []
                images = save_images_from_page(
                    document, index, remove_letters(text), output_dir,
                    image_format, quality, min_size, warnings)
                yield PageResult(index + 1, text, images, warnings)
    finally:
        document.close()
