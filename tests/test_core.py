"""Fast, in-process tests of the library API (no subprocess)."""
import pytest
from PIL import Image

from pdf_image_extractor import (
    ExtractorError,
    extract,
    parse_pages,
    pillow_format,
    remove_letters,
    resize_image,
    sanitize_filename,
)
from pdf_image_extractor.cli import main


# --------------------------------------------------------------------------- pure helpers

@pytest.mark.parametrize("text, expected", [
    ("", ""),
    ("abc", ""),
    ("Ref 123", " 123"),
    ("12/34", "12/34"),
    ("ção 5 é", " 5 "),
    ("商品 20001 製品", " 20001 "),   # ideographs count as letters
    ("a1-b2_c3", "1-2_3"),
])
def test_remove_letters(text, expected):
    assert remove_letters(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("  123  ", "123"),
    ("12\n34", "1234"),
    ('a<b>c:d"e/f\\g|h?i*j', "abcdefghij"),
    ("1   2\t3", "1 2 3"),
    ("", ""),
    ("???", ""),
])
def test_sanitize_filename(text, expected):
    assert sanitize_filename(text) == expected


def test_sanitize_filename_caps_the_length():
    assert len(sanitize_filename("1" * 1000)) == 100
    assert sanitize_filename("1234567890", max_bytes=4) == "1234"


def test_sanitize_filename_never_splits_a_multibyte_character():
    out = sanitize_filename("é" * 100, max_bytes=5)
    assert out == "éé"  # 4 bytes; a 5th byte would cut the next é in half
    out.encode("utf-8")


@pytest.mark.parametrize("spec, total, expected", [
    (None, 3, [0, 1, 2]),
    ("", 3, [0, 1, 2]),
    ("1", 3, [0]),
    ("2-3", 3, [1, 2]),
    ("3,1", 3, [0, 2]),
    ("1-2,2-3", 3, [0, 1, 2]),
    ("2-9", 3, [1, 2]),
    ("9", 3, []),
    ("0", 3, []),
    ("3-2", 3, []),      # reversed range selects nothing
    ("1", 0, []),
])
def test_parse_pages(spec, total, expected):
    assert parse_pages(spec, total) == expected


@pytest.mark.parametrize("name, expected", [
    ("png", "PNG"), ("PNG", "PNG"), (" webp ", "WEBP"),
    ("jpeg", "JPEG"), ("jpg", "JPEG"), ("JPG", "JPEG"),
])
def test_pillow_format(name, expected):
    assert pillow_format(name) == expected


@pytest.mark.parametrize("name", ["", "docx", "notaformat", "pdfx"])
def test_pillow_format_rejects_unknown(name):
    with pytest.raises(ValueError):
        pillow_format(name)


@pytest.mark.parametrize("size", [(1000, 800), (800, 1000), (500, 500), (1200, 1200)])
def test_resize_image_scales_the_larger_side_to_70_percent(size):
    out = resize_image(Image.new("RGB", size))
    assert max(out.size) == int(max(size) * 0.7)
    assert abs(out.width / out.height - size[0] / size[1]) < 0.02


def test_resize_image_keeps_the_original_untouched():
    src = Image.new("RGB", (1000, 1000))
    resize_image(src)
    assert src.size == (1000, 1000)


# --------------------------------------------------------------------------- extract()

def test_extract_yields_text_and_files_per_page(make_pdf, tmp_path):
    pdf, case = make_pdf("multi_page_mixed")
    results = list(extract(str(pdf), str(tmp_path), "png", 90))
    assert [r.number for r in results] == [1, 2, 3, 4]
    assert [len(r.images) for r in results] == case.large_images_per_page
    assert "Cat 6003" in results[2].text
    assert all((tmp_path / p).exists() or p for r in results for p in r.images)
    assert len(list(tmp_path.iterdir())) == 3


def test_extract_names_files_reference_page_index(make_pdf, tmp_path):
    pdf, _ = make_pdf("two_images_one_page")
    [page] = extract(str(pdf), str(tmp_path), "png", 90)
    names = sorted(p.rsplit("/", 1)[-1] for p in page.images)
    assert names == ["5001_1_1.png", "5001_1_2.png"]


def test_extract_respects_pages_and_min_size(make_pdf, tmp_path):
    pdf, _ = make_pdf("multi_page_mixed")
    results = list(extract(str(pdf), str(tmp_path), "png", 90, min_size=200, pages="3-4"))
    assert [r.number for r in results] == [3, 4]
    assert [len(r.images) for r in results] == [2, 1]


def test_extract_is_lazy(make_pdf, tmp_path):
    pdf, _ = make_pdf("multi_page_mixed")
    it = extract(str(pdf), str(tmp_path), "png", 90)
    next(it)
    assert len(list(tmp_path.iterdir())) == 1  # only page 1 processed so far
    it.close()


@pytest.mark.parametrize("name", ["encrypted", "truncated", "not_a_pdf", "zero_bytes"])
def test_extract_raises_extractor_error_for_bad_files(name, make_pdf, tmp_path):
    pdf, _ = make_pdf(name)
    with pytest.raises(ExtractorError):
        list(extract(str(pdf), str(tmp_path), "png", 90))


# --------------------------------------------------------------------------- cli.main()

def test_main_returns_zero_and_prints(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("single_large_image")
    assert main([str(pdf), str(tmp_path), "png", "90"]) == 0
    out = capsys.readouterr().out
    assert "Text on Page 1:" in out and "Image Saved:" in out


def test_main_returns_one_on_error(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("encrypted")
    assert main([str(pdf), str(tmp_path), "png", "90"]) == 1
    captured = capsys.readouterr()
    assert "password protected" in captured.err
    assert "Traceback" not in captured.err


def test_main_usage_error_exits_2(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["only-one-argument"])
    assert exc.value.code == 2
