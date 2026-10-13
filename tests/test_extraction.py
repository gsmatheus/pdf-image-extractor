"""End-to-end behaviour of the CLI against every kind of PDF in pdf_factory."""
import pytest

import pdf_factory
from conftest import saved_lines

OK_CASES = [n for n, (_, kind) in pdf_factory.CASES.items() if kind == "ok"]

ISSUE_3 = "issue #3: images on the same page overwrite each other (filename has no image index)"
LONG_NAME = "filename built from the page text exceeds the OS limit -> OSError"

# test name -> {case: reason}. xfail(strict): fixing a bug turns the test red until
# its entry is removed, which keeps this list honest.
KNOWN_BUGS = {
    "test_every_image_ends_up_as_its_own_file": {
        "two_images_one_page": ISSUE_3,
        "five_images_one_page": ISSUE_3,
        "multi_page_mixed": ISSUE_3,
        "tall_and_wide": ISSUE_3,
        "long_text_page": LONG_NAME,
    },
    "test_exits_cleanly": {"long_text_page": LONG_NAME},
    "test_prints_text_of_every_page": {"long_text_page": LONG_NAME},
    "test_reports_one_saved_image_per_large_embedded_image": {"long_text_page": LONG_NAME},
}


def cases_for(test_name):
    bugs = KNOWN_BUGS.get(test_name, {})
    return [pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=bugs[n]))
            if n in bugs else n for n in OK_CASES]


@pytest.mark.parametrize("name", cases_for("test_exits_cleanly"))
def test_exits_cleanly(name, extraction):
    proc, _, _ = extraction(name)
    assert proc.returncode == 0, proc.stderr[-300:]


@pytest.mark.parametrize("name", cases_for("test_prints_text_of_every_page"))
def test_prints_text_of_every_page(name, extraction):
    proc, _, case = extraction(name)
    assert proc.returncode == 0, proc.stderr[-300:]
    for page in range(1, case.pages + 1):
        assert f"Text on Page {page}:" in proc.stdout
    for text in case.texts:
        assert text in proc.stdout


@pytest.mark.parametrize("name", cases_for("test_reports_one_saved_image_per_large_embedded_image"))
def test_reports_one_saved_image_per_large_embedded_image(name, extraction):
    proc, _, case = extraction(name)
    assert proc.returncode == 0, proc.stderr[-300:]
    assert len(saved_lines(proc)) == sum(case.large_images_per_page)


@pytest.mark.parametrize("name", cases_for("test_every_image_ends_up_as_its_own_file"))
def test_every_image_ends_up_as_its_own_file(name, extraction):
    """'Image Saved' lines must match distinct non-empty files on disk."""
    proc, out, case = extraction(name)
    assert proc.returncode == 0, proc.stderr[-300:]
    files = [p for p in out.iterdir() if p.is_file()]
    assert len(files) == sum(case.large_images_per_page)
    assert all(p.stat().st_size > 0 for p in files)
