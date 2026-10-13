"""Generates a catalogue of PDFs that exercise the extractor in many situations.

Every builder is registered in ``CASES`` under a short name and writes one PDF
to the given path. Builders return a ``Case`` describing what the PDF contains,
so tests can assert against the *expected* result instead of hard-coding it.

Run ``uv run python tests/pdf_factory.py [outdir]`` to dump every PDF to disk
(handy for trying the CLI by hand).
"""
from __future__ import annotations

import io
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import fitz
from PIL import Image

PAGE_W, PAGE_H = 595, 842  # A4 in points
PASSWORD = "secret"


@dataclass
class Case:
    """What a generated PDF contains."""
    description: str
    pages: int = 1
    # Number of embedded images >= 500x500 per page (what the tool should save).
    large_images_per_page: list[int] = field(default_factory=list)
    # Substrings expected somewhere in the extracted text.
    texts: list[str] = field(default_factory=list)


CASES: dict[str, tuple[Callable[[Path], Case], str]] = {}


def case(name: str, kind: str = "ok"):
    """Register a builder. kind: ok | encrypted | corrupt | not_pdf."""
    def deco(fn):
        CASES[name] = (fn, kind)
        return fn
    return deco


# --------------------------------------------------------------------------- helpers

def make_image(w: int, h: int, mode: str = "RGB", seed: int = 0) -> Image.Image:
    """Deterministic, non-trivial picture (gradient + noise) so codecs have work to do."""
    rnd = random.Random(seed)
    horizontal = Image.linear_gradient("L").rotate(90).resize((w, h))
    vertical = Image.linear_gradient("L").resize((w, h))
    base = Image.merge("RGB", (horizontal, vertical,
                               Image.new("L", (w, h), (seed * 40) % 256)))
    noise = Image.effect_noise((w, h), 30).convert("RGB")
    base = Image.blend(base, noise, 0.15)
    for _ in range(5):  # a few solid blocks make it visually identifiable
        x0, y0 = rnd.randrange(w), rnd.randrange(h)
        base.paste((rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)),
                   (x0, y0, min(x0 + w // 5, w), min(y0 + h // 5, h)))
    if mode == "RGB":
        return base
    if mode == "RGBA":
        alpha = Image.linear_gradient("L").resize((w, h))
        base.putalpha(alpha)
        return base
    if mode == "P":
        return base.convert("P", palette=Image.Palette.ADAPTIVE, colors=64)
    if mode == "1":
        return base.convert("L").convert("1")
    return base.convert(mode)  # L, CMYK, ...


def encode(img: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def new_doc() -> fitz.Document:
    return fitz.open()


def add_page(doc, text: str | None = None, fontname: str = "helv",
             width: int = PAGE_W, height: int = PAGE_H) -> fitz.Page:
    page = doc.new_page(width=width, height=height)
    if text is not None:
        page.insert_text((50, 50), text, fontsize=14, fontname=fontname)
    return page


def place(page, w: int, h: int, *, fmt: str = "PNG", mode: str = "RGB", seed: int = 0,
          rect: fitz.Rect | None = None, stream: bytes | None = None, **kw):
    """Embed a w x h image on the page (scaled to fit ``rect``)."""
    rect = rect or fitz.Rect(50, 80, PAGE_W - 50, 80 + (PAGE_W - 100) * h / w)
    data = stream or encode(make_image(w, h, mode, seed), fmt)
    return page.insert_image(rect, stream=data, **kw)


def stack_rects(n: int, top: int = 80, gap: int = 10):
    """n equally sized rects stacked vertically."""
    h = (PAGE_H - top - 40 - gap * (n - 1)) / n
    return [fitz.Rect(50, top + i * (h + gap), PAGE_W - 50, top + i * (h + gap) + h)
            for i in range(n)]


def save(doc: fitz.Document, path: Path, **kw):
    doc.save(str(path), **kw)
    doc.close()


# --------------------------------------------------------------------------- text / no images

@case("text_only")
def _(path):
    doc = new_doc()
    add_page(doc, "Product 1001 - just text, no pictures")
    save(doc, path)
    return Case("single page, text only", 1, [0], ["1001"])


@case("vector_only")
def _(path):
    doc = new_doc()
    page = add_page(doc, "Chart 2002")
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(100, 100, 400, 400))
    shape.draw_circle(fitz.Point(250, 250), 100)
    shape.finish(color=(1, 0, 0), fill=(0.9, 0.9, 0.2))
    shape.commit()
    save(doc, path)
    return Case("vector drawings are not embedded images", 1, [0], ["2002"])


@case("empty_page")
def _(path):
    doc = new_doc()
    add_page(doc)  # no text, no images -> extract_text() returns None
    save(doc, path)
    return Case("completely blank page", 1, [0])


@case("empty_page_among_others")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Item 3001")
    place(p, 800, 800)
    add_page(doc)  # blank in the middle
    p = add_page(doc, "Item 3003")
    place(p, 800, 800, seed=2)
    save(doc, path)
    return Case("blank page between two product pages", 3, [1, 0, 1], ["3001", "3003"])


# --------------------------------------------------------------------------- image counts

@case("single_large_image")
def _(path):
    doc = new_doc()
    p = add_page(doc, "SKU 4001")
    place(p, 1000, 800)
    save(doc, path)
    return Case("one big picture", 1, [1], ["4001"])


@case("two_images_one_page")
def _(path):
    """Issue #3: several images on the same page overwrite each other."""
    doc = new_doc()
    p = add_page(doc, "SKU 5001")
    for i, r in enumerate(stack_rects(2)):
        place(p, 700, 600, seed=i, rect=r)
    save(doc, path)
    return Case("two big pictures on the same page", 1, [2], ["5001"])


@case("five_images_one_page")
def _(path):
    doc = new_doc()
    p = add_page(doc, "SKU 5005")
    for i, r in enumerate(stack_rects(5)):
        place(p, 600, 600, seed=i, rect=r)
    save(doc, path)
    return Case("five big pictures on the same page", 1, [5], ["5005"])


@case("multi_page_mixed")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Cat 6001")
    place(p, 900, 700)
    add_page(doc, "Cat 6002 only text")
    p = add_page(doc, "Cat 6003")
    for i, r in enumerate(stack_rects(2)):
        place(p, 650, 650, seed=i + 3, rect=r)
    p = add_page(doc, "Cat 6004")
    place(p, 300, 300)  # too small, skipped
    save(doc, path)
    return Case("catalogue with images on some pages only", 4, [1, 0, 2, 0],
                ["6001", "6002", "6003", "6004"])


@case("many_pages")
def _(path):
    doc = new_doc()
    expected = []
    for n in range(1, 41):
        p = add_page(doc, f"Page ref {7000 + n}")
        if n % 3 == 0:
            place(p, 600, 600, seed=n)
            expected.append(1)
        else:
            expected.append(0)
    save(doc, path)
    return Case("40 pages, an image on every third", 40, expected, ["7001", "7040"])


@case("same_image_every_page")
def _(path):
    """One image object (single xref) shown on three different pages."""
    doc = new_doc()
    first = add_page(doc, "Logo page 8001")
    xref = place(first, 800, 800)
    for n in (2, 3):
        p = add_page(doc, f"Logo page 800{n}")
        p.insert_image(fitz.Rect(50, 80, PAGE_W - 50, 500), xref=xref)
    save(doc, path)
    return Case("image object reused on 3 pages", 3, [1, 1, 1], ["8001", "8002", "8003"])


# --------------------------------------------------------------------------- size thresholds

@case("small_images")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Icons 9001")
    for i, r in enumerate(stack_rects(3)):
        place(p, 120, 120, seed=i, rect=r)
    save(doc, path)
    return Case("only thumbnails (<500px) -> nothing to save", 1, [0], ["9001"])


@case("boundary_500x500")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Edge 9101")
    place(p, 500, 500)
    save(doc, path)
    return Case("exactly 500x500 is kept", 1, [1], ["9101"])


@case("boundary_499x500")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Edge 9102")
    place(p, 499, 500)
    save(doc, path)
    return Case("one pixel under the limit is dropped", 1, [0], ["9102"])


@case("tall_and_wide")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Shapes 9201")
    place(p, 600, 1800, rect=fitz.Rect(50, 80, 250, 680))   # portrait
    place(p, 2000, 520, seed=1, rect=fitz.Rect(50, 700, 545, 830))  # panorama
    save(doc, path)
    return Case("very tall and very wide pictures", 1, [2], ["9201"])


@case("huge_image")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Big 9301")
    place(p, 4000, 3000, fmt="JPEG")
    save(doc, path, deflate=True)
    return Case("12 megapixel photo", 1, [1], ["9301"])


# --------------------------------------------------------------------------- image encodings

@case("jpeg_image")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Photo 10001")
    place(p, 900, 700, fmt="JPEG")
    save(doc, path)
    return Case("DCT/JPEG encoded", 1, [1], ["10001"])


@case("png_with_alpha")
def _(path):
    """RGBA/soft-mask images cannot be written as JPEG by Pillow."""
    doc = new_doc()
    p = add_page(doc, "Cutout 10002")
    place(p, 800, 800, mode="RGBA")
    save(doc, path)
    return Case("transparent PNG (soft mask)", 1, [1], ["10002"])


@case("grayscale_image")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Gray 10003")
    place(p, 800, 800, mode="L")
    save(doc, path)
    return Case("8-bit grayscale", 1, [1], ["10003"])


@case("cmyk_jpeg")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Print 10004")
    place(p, 800, 800, mode="CMYK", fmt="JPEG")
    save(doc, path)
    return Case("CMYK JPEG (print-ready)", 1, [1], ["10004"])


@case("palette_image")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Indexed 10005")
    place(p, 800, 800, mode="P", fmt="PNG")
    save(doc, path)
    return Case("palette / indexed PNG", 1, [1], ["10005"])


@case("one_bit_image")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Scan 10006")
    place(p, 1000, 1000, mode="1", fmt="PNG")
    save(doc, path)
    return Case("1-bit black & white", 1, [1], ["10006"])


@case("scanned_page")
def _(path):
    """A scan: full-page image and no text layer at all."""
    doc = new_doc()
    p = add_page(doc)
    place(p, 1240, 1754, fmt="JPEG", rect=fitz.Rect(0, 0, PAGE_W, PAGE_H))
    save(doc, path)
    return Case("scan with no text layer", 1, [1])


@case("image_with_mask")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Masked 10008")
    mask = encode(make_image(800, 800, "L", seed=9), "PNG")
    p.insert_image(fitz.Rect(50, 80, 545, 575), mask=mask,
                   stream=encode(make_image(800, 800, seed=4), "PNG"))
    save(doc, path)
    return Case("image + separate stencil mask", 1, [1], ["10008"])


@case("rotated_page")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Rotated 11001")
    place(p, 800, 600)
    p.set_rotation(90)
    save(doc, path)
    return Case("page rotated 90 degrees", 1, [1], ["11001"])


@case("landscape_page")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Wide 11002", width=842, height=595)
    place(p, 1000, 600, rect=fitz.Rect(50, 80, 790, 540))
    save(doc, path)
    return Case("landscape A4", 1, [1], ["11002"])


# --------------------------------------------------------------------------- text -> filename

@case("no_digits_in_text")
def _(path):
    """The filename prefix is the text with letters removed: here nothing remains."""
    doc = new_doc()
    p = add_page(doc, "Only letters here")
    place(p, 800, 800)
    save(doc, path)
    return Case("text with no digits -> empty filename prefix", 1, [1], ["Only letters"])


@case("digits_only_reference")
def _(path):
    doc = new_doc()
    p = add_page(doc, "123456")
    place(p, 800, 800)
    save(doc, path)
    return Case("clean numeric reference", 1, [1], ["123456"])


@case("special_chars_in_text")
def _(path):
    doc = new_doc()
    p = add_page(doc, 'Ref 12/34:56 <a|b> "q" ? * \\ 78')
    place(p, 800, 800)
    save(doc, path)
    return Case("characters that are illegal in filenames", 1, [1], ["12/34"])


@case("long_text_page")
def _(path):
    """Lots of digits in the text produce a filename beyond the 255 byte limit."""
    doc = new_doc()
    p = add_page(doc)
    line = " ".join(str(1000 + i) for i in range(25))
    for i in range(12):
        p.insert_text((30, 40 + i * 18), line, fontsize=9)
    place(p, 800, 800, rect=fitz.Rect(50, 300, 545, 795))
    save(doc, path)
    return Case("numeric text longer than the OS filename limit", 1, [1], ["1000"])


@case("accents_and_unicode")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Referência ção 12345 ñ é ü")
    place(p, 800, 800)
    save(doc, path)
    return Case("accented Latin text", 1, [1], ["12345"])


@case("cjk_text")
def _(path):
    doc = new_doc()
    p = add_page(doc, "商品 20001 製品", fontname="china-s")
    place(p, 800, 800)
    save(doc, path)
    return Case("CJK text: isalpha() is True for ideographs", 1, [1], ["20001"])


@case("same_text_on_two_pages")
def _(path):
    """Two pages with identical text -> same filename stem, only the page number differs."""
    doc = new_doc()
    for s in (1, 2):
        p = add_page(doc, "Ref 30000")
        place(p, 700, 700, seed=s)
    save(doc, path)
    return Case("identical headers on two pages", 2, [1, 1], ["30000"])


# --------------------------------------------------------------------------- broken input

@case("encrypted", kind="encrypted")
def _(path):
    doc = new_doc()
    p = add_page(doc, "Secret 40001")
    place(p, 800, 800)
    save(doc, path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=PASSWORD,
         owner_pw="owner")
    return Case("password protected", 1, [1], ["40001"])


@case("truncated", kind="corrupt")
def _(path):
    good = path.with_suffix(".good")
    doc = new_doc()
    p = add_page(doc, "Cut 50001")
    place(p, 800, 800)
    save(doc, good)
    data = good.read_bytes()
    good.unlink()
    path.write_bytes(data[: len(data) // 2])
    return Case("file cut in half", 1, [1])


@case("not_a_pdf", kind="not_pdf")
def _(path):
    path.write_text("this is plain text, not a PDF\n")
    return Case("plain text with a .pdf extension")


@case("zero_bytes", kind="not_pdf")
def _(path):
    path.write_bytes(b"")
    return Case("empty file")


# --------------------------------------------------------------------------- API

def build(name: str, directory: Path) -> tuple[Path, Case]:
    fn, _ = CASES[name]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.pdf"
    return path, fn(path)


def build_all(directory: Path) -> dict[str, tuple[Path, Case]]:
    return {name: build(name, directory) for name in CASES}


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures")
    for name, (path, c) in build_all(out).items():
        print(f"{path}  -  {c.description}")
