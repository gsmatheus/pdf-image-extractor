"""Fast, in-process tests of the library API (no subprocess)."""
import pytest
from PIL import Image

import pdf_factory

from pdf_image_extractor import (
    ExtractorError,
    extract,
    parse_pages,
    pillow_format,
    remove_letters,
    resize_image,
    sanitize_filename,
)
from pdf_image_extractor.cli import format_summary, main


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
    ("\x00\x1f12", "12"),            # control characters
    ("\u200b7\u200b", "7"),          # zero-width characters
    ("..12..", "12"),                # edge dots are invalid on Windows
    ("- 5 -", "5"),
    ("_7_", "7"),
    ("12.50", "12.50"),              # inner punctuation is kept
    ("$12.50 - 5%", "$12.50 - 5%"),
    ("...", ""),
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


@pytest.mark.parametrize("name, expected", [
    ("no_digits_in_text", "page_1_1.png"),   # nothing usable in the text
    ("scanned_page", "page_1_1.png"),        # no text layer at all
    ("digits_only_reference", "123456_1_1.png"),
    ("special_chars_in_text", "123456 78_1_1.png"),
    ("cjk_text", "20001_1_1.png"),
])
def test_filename_prefix_comes_from_the_digits_of_the_page_text(name, expected, make_pdf, tmp_path):
    pdf, _ = make_pdf(name)
    [page] = extract(str(pdf), str(tmp_path), "png", 90)
    assert [p.rsplit("/", 1)[-1] for p in page.images] == [expected]


def test_same_reference_on_two_pages_stays_distinct(make_pdf, tmp_path):
    pdf, _ = make_pdf("same_text_on_two_pages")
    names = [p.rsplit("/", 1)[-1] for page in extract(str(pdf), str(tmp_path), "png", 90)
             for p in page.images]
    assert names == ["30000_1_1.png", "30000_2_1.png"]


def test_pages_option_keeps_original_page_numbers_in_filenames(make_pdf, tmp_path):
    pdf, _ = make_pdf("multi_page_mixed")
    [page] = extract(str(pdf), str(tmp_path), "png", 90, pages="3")
    assert sorted(p.rsplit("/", 1)[-1] for p in page.images) == ["6003_3_1.png", "6003_3_2.png"]


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


# --------------------------------------------------------------------------- bad images / passwords

def test_one_undecodable_image_does_not_abort_the_run(make_pdf, tmp_path):
    pdf, case = make_pdf("corrupt_image_among_good")
    [page] = extract(str(pdf), str(tmp_path), "png", 90)
    assert len(page.images) == sum(case.large_images_per_page) == 2
    assert [p.rsplit("/", 1)[-1] for p in page.images] == ["60001_1_1.png", "60001_1_3.png"]
    [warning] = page.warnings
    assert "page 1, image 2" in warning
    assert sorted(p.name for p in tmp_path.iterdir()) == ["60001_1_1.png", "60001_1_3.png"]


def test_failed_image_never_removes_a_file_from_a_previous_run(make_pdf, tmp_path):
    pdf, _ = make_pdf("corrupt_image_among_good")
    keep = tmp_path / "60001_1_2.png"
    keep.write_bytes(b"from an earlier run")
    list(extract(str(pdf), str(tmp_path), "png", 90))
    assert keep.read_bytes() == b"from an earlier run"


def test_cli_warns_on_stderr_and_still_succeeds(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("corrupt_image_among_good")
    assert main([str(pdf), str(tmp_path), "png", "90"]) == 0
    captured = capsys.readouterr()
    assert captured.out.count("Image Saved:") == 2
    assert "Warning: page 1, image 2" in captured.err


def test_password_opens_an_encrypted_pdf(make_pdf, tmp_path):
    pdf, case = make_pdf("encrypted")
    [page] = extract(str(pdf), str(tmp_path), "png", 90, password=pdf_factory.PASSWORD)
    assert "40001" in page.text
    assert len(page.images) == 1


def test_wrong_password_is_an_error(make_pdf, tmp_path):
    pdf, _ = make_pdf("encrypted")
    with pytest.raises(ExtractorError, match="wrong password"):
        list(extract(str(pdf), str(tmp_path), "png", 90, password="nope"))


def test_missing_password_hints_at_the_option(make_pdf, tmp_path):
    pdf, _ = make_pdf("encrypted")
    with pytest.raises(ExtractorError, match="--password"):
        list(extract(str(pdf), str(tmp_path), "png", 90))


def test_cli_password_option(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("encrypted")
    assert main([str(pdf), str(tmp_path), "png", "90", "--password", pdf_factory.PASSWORD]) == 0
    assert "Image Saved:" in capsys.readouterr().out
    assert main([str(pdf), str(tmp_path), "png", "90", "--password", "wrong"]) == 1


# --------------------------------------------------------------------------- run summary

@pytest.mark.parametrize("args, expected", [
    ((4, 3, [2, 4], 0), "Done: 3 images from 4 pages. No images on pages 2, 4."),
    ((1, 1, [], 0), "Done: 1 image from 1 page."),
    ((1, 0, [1], 0), "Done: 0 images from 1 page. No images on page 1."),
    ((0, 0, [], 0), "Done: 0 images from 0 pages."),
    ((3, 2, [], 1), "Done: 2 images from 3 pages. 1 image skipped (see warnings)."),
    ((40, 0, list(range(1, 41)), 0),
     "Done: 0 images from 40 pages. No images on pages 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ... (40 in total)."),
])
def test_format_summary(args, expected):
    assert format_summary(*args) == expected


def test_cli_prints_the_summary_on_stderr_not_stdout(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("multi_page_mixed")  # images on pages 1 and 3 only
    assert main([str(pdf), str(tmp_path), "png", "90"]) == 0
    captured = capsys.readouterr()
    assert "Done: 3 images from 4 pages. No images on pages 2, 4." in captured.err
    assert "Done:" not in captured.out  # stdout format is unchanged for anything parsing it


def test_cli_summary_counts_skipped_images(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("corrupt_image_among_good")
    main([str(pdf), str(tmp_path), "png", "90"])
    assert "Done: 2 images from 1 page. 1 image skipped (see warnings)." in capsys.readouterr().err


def test_cli_prints_no_summary_on_error(make_pdf, tmp_path, capsys):
    pdf, _ = make_pdf("encrypted")
    assert main([str(pdf), str(tmp_path), "png", "90"]) == 1
    assert "Done:" not in capsys.readouterr().err
