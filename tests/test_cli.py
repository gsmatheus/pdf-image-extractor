"""CLI contract: bad input, bad arguments and output formats."""
import pytest
from PIL import Image

import pdf_factory
from conftest import run_main, saved_lines

BROKEN = [n for n, (_, kind) in pdf_factory.CASES.items() if kind != "ok"]


def bug(reason):
    """Known bug: strict xfail, so fixing it forces removing the marker."""
    return pytest.mark.xfail(strict=True, reason=reason)


NO_ERROR_HANDLING = bug("no error handling: fitz/pdfplumber exceptions escape as a traceback")


@pytest.mark.parametrize("name", [pytest.param(n, marks=NO_ERROR_HANDLING) for n in BROKEN])
def test_broken_pdf_fails_without_traceback(name, make_pdf, run_cli):
    """Encrypted / truncated / non-PDF input must give a clean non-zero exit."""
    pdf, _ = make_pdf(name)
    proc, out = run_cli(pdf)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr
    assert not list(out.iterdir())


@bug("missing input is not validated (fixed by PR #6)")
def test_missing_input_file(run_cli, tmp_path):
    proc, _ = run_cli(tmp_path / "nope.pdf")
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr


@bug("output dir is not created when missing (fixed by PR #6)")
def test_output_dir_is_created_when_missing(make_pdf, tmp_path):
    pdf, _ = make_pdf("single_large_image")
    target = tmp_path / "a" / "b" / "c"
    proc = run_main(pdf, target, "png", 90)
    assert proc.returncode == 0, proc.stderr[-500:]
    assert len(list(target.iterdir())) == 1


def test_missing_arguments_shows_usage():
    proc = run_main()
    assert proc.returncode == 2
    assert "usage" in proc.stderr.lower()


@bug("int(args.img_quality) raises ValueError; argparse type=int would give a usage error")
@pytest.mark.parametrize("quality", ["abc", "", "1.5"])
def test_non_numeric_quality_is_rejected_cleanly(quality, make_pdf, run_cli):
    pdf, _ = make_pdf("single_large_image")
    proc, _ = run_cli(pdf, "png", quality)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize("fmt, expected", [
    ("png", "PNG"), ("jpeg", "JPEG"), ("webp", "WEBP"),
    ("PNG", "PNG"),   # upper-case should work too
    pytest.param("jpg", "JPEG", marks=bug("Pillow has no 'JPG' writer; needs mapping to JPEG")),
])
def test_output_formats(fmt, expected, make_pdf, run_cli):
    pdf, _ = make_pdf("single_large_image")
    proc, out = run_cli(pdf, fmt, 80)
    assert proc.returncode == 0, proc.stderr[-500:]
    [file] = [p for p in out.iterdir()]
    with Image.open(file) as img:
        assert img.format == expected


@bug("unknown format escapes as KeyError traceback")
def test_unknown_format_fails_cleanly(make_pdf, run_cli):
    pdf, _ = make_pdf("single_large_image")
    proc, _ = run_cli(pdf, "notaformat", 80)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize("fmt", ["png", "jpeg", "webp"])
@pytest.mark.parametrize("name", ["png_with_alpha", "grayscale_image", "cmyk_jpeg",
                                  "palette_image", "one_bit_image"])
def test_colour_modes_survive_every_format(name, fmt, make_pdf, run_cli):
    pdf, _ = make_pdf(name)
    proc, out = run_cli(pdf, fmt, 85)
    assert proc.returncode == 0, proc.stderr[-500:]
    assert len(saved_lines(proc)) == 1
    assert len(list(out.iterdir())) == 1


def test_saved_image_is_downscaled_not_enlarged(make_pdf, run_cli):
    pdf, _ = make_pdf("single_large_image")  # 1000x800 embedded
    proc, out = run_cli(pdf)
    [file] = list(out.iterdir())
    with Image.open(file) as img:
        assert max(img.size) <= 1000
        assert img.width >= 500 or img.height >= 500
        assert abs(img.width / img.height - 1000 / 800) < 0.02  # aspect ratio kept
