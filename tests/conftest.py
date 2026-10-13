import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import pdf_factory  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def pdf_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("pdfs")


@pytest.fixture(scope="session")
def make_pdf(pdf_dir):
    """Build (and cache) a fixture PDF by name -> (path, Case)."""
    cache = {}

    def _make(name):
        if name not in cache:
            cache[name] = pdf_factory.build(name, pdf_dir)
        return cache[name]

    return _make


def run_main(*args):
    return subprocess.run([sys.executable, str(ROOT / "main.py"), *map(str, args)],
                          capture_output=True, text=True, timeout=120)


@pytest.fixture
def run_cli(tmp_path):
    """Run `main.py` as a user would. Returns (CompletedProcess, output_dir)."""
    def _run(pdf, fmt="png", quality=90, *extra, out=None):
        out = out if out is not None else tmp_path / "out"
        out.mkdir(parents=True, exist_ok=True)
        return run_main(pdf, out, fmt, quality, *extra), out

    return _run


def saved_lines(proc):
    return [l for l in proc.stdout.splitlines() if l.startswith("Image Saved:")]


@pytest.fixture(scope="session")
def extraction(make_pdf, tmp_path_factory):
    """Run the CLI once per PDF (default png/90) and cache the result."""
    cache = {}

    def _get(name):
        if name not in cache:
            pdf, case = make_pdf(name)
            out = tmp_path_factory.mktemp(f"out_{name}")
            cache[name] = (run_main(pdf, out, "png", 90), out, case)
        return cache[name]

    return _get
