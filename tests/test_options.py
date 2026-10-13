"""--min_size and --pages (added by PR #6)."""
import re

import pytest

from conftest import saved_lines


def pages_printed(proc):
    return [int(n) for n in re.findall(r"^Text on Page (\d+):", proc.stdout, re.M)]


# multi_page_mixed: p1 = 1 big image, p2 = text, p3 = 2 big images, p4 = one 300px image
@pytest.mark.parametrize("pages, expected_pages", [
    ("1", [1]),
    ("1,3", [1, 3]),
    ("2-4", [2, 3, 4]),
    ("3,1", [1, 3]),            # order does not matter, output is sorted
    ("1,1,1", [1]),             # duplicates collapse
    ("1-2,4", [1, 2, 4]),       # ranges and lists mix
    ("3-9", [3, 4]),            # out-of-range pages are ignored
    ("9", []),                  # nothing selected
])
def test_pages_selection(pages, expected_pages, make_pdf, run_cli):
    pdf, _ = make_pdf("multi_page_mixed")
    proc, _ = run_cli(pdf, "png", 90, "--pages", pages)
    assert proc.returncode == 0, proc.stderr[-300:]
    assert pages_printed(proc) == expected_pages


def test_pages_only_saves_images_of_selected_pages(make_pdf, run_cli):
    pdf, _ = make_pdf("multi_page_mixed")
    proc, out = run_cli(pdf, "png", 90, "--pages", "3")
    assert len(saved_lines(proc)) == 2
    assert len(list(out.iterdir())) == 2


@pytest.mark.parametrize("pages", ["abc", "1-", "-3", "1,,2", "x-y"])
def test_pages_garbage_is_a_clean_error(pages, make_pdf, run_cli):
    pdf, _ = make_pdf("multi_page_mixed")
    proc, out = run_cli(pdf, "png", 90, "--pages", pages)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr
    assert not list(out.iterdir())


@pytest.mark.parametrize("pages", ["0", "0-2", "-1"])
def test_pages_are_one_based(pages, make_pdf, run_cli):
    """Page 0 does not exist; it must not silently wrap to the last page."""
    pdf, _ = make_pdf("multi_page_mixed")
    proc, _ = run_cli(pdf, "png", 90, "--pages", pages)
    assert 4 not in pages_printed(proc) or pages == "0-2"
    assert 0 not in pages_printed(proc)


@pytest.mark.parametrize("min_size, expected", [
    (100, 4),    # the 300px picture on page 4 now counts too
    (300, 4),
    (301, 3),
    (500, 3),
    (801, 0),
])
def test_min_size(min_size, expected, make_pdf, run_cli):
    pdf, _ = make_pdf("multi_page_mixed")  # 900x700, 650x650 x2, 300x300
    proc, out = run_cli(pdf, "png", 90, "--min_size", min_size)
    assert proc.returncode == 0, proc.stderr[-300:]
    assert len(saved_lines(proc)) == expected
    assert len(list(out.iterdir())) == expected


def test_min_size_default_matches_documented_500(make_pdf, run_cli):
    pdf, _ = make_pdf("boundary_499x500")
    proc, _ = run_cli(pdf)
    assert saved_lines(proc) == []
    proc, _ = run_cli(pdf, "png", 90, "--min_size", 499)
    assert len(saved_lines(proc)) == 1


@pytest.mark.parametrize("value", ["abc", "1.5", ""])
def test_min_size_must_be_an_integer(value, make_pdf, run_cli):
    pdf, _ = make_pdf("single_large_image")
    proc, _ = run_cli(pdf, "png", 90, "--min_size", value)
    assert proc.returncode == 2  # argparse usage error
    assert "Traceback" not in proc.stderr


def test_errors_go_to_stderr(make_pdf, run_cli, tmp_path):
    proc, _ = run_cli(tmp_path / "nope.pdf")
    assert proc.returncode != 0
    assert proc.stderr.strip(), "error message should be on stderr, not stdout"
