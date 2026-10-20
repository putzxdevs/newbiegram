"""Tests for the TL schema compiler and the packaging metadata around it.

The compiler regenerates newbiegram/raw and newbiegram/errors/exceptions from the
`.tl` sources on every build (see hatch_build.py), so it must be deterministic
and idempotent: running it twice must not produce a second, different tree.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pyproject():
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_project_metadata(pyproject):
    project = pyproject["project"]

    assert project["name"] == "newbiegram"
    assert project["requires-python"] == "<4.0, >=3.12"


def test_declared_python_matches_classifiers(pyproject):
    """`requires-python` and the classifiers must not disagree."""
    project = pyproject["project"]
    declared = project["requires-python"]

    classifiers = [c for c in project["classifiers"] if c.startswith("Programming Language :: Python :: 3.")]
    versions = {c.rsplit("::", 1)[-1].strip() for c in classifiers}

    # 3.11 was dropped because the code uses PEP 695 `type` aliases.
    assert "3.11" not in versions
    assert {"3.12", "3.13"} <= versions
    assert ">=3.12" in declared


def test_runtime_dependencies_are_declared(pyproject):
    """pyaes and aiosqlite are imported unconditionally, so they must be required."""
    names = {
        re.split(r"[<>=!\[ ]", dep, maxsplit=1)[0].strip()
        for dep in pyproject["project"]["dependencies"]
    }

    assert "pyaes" in names
    assert "aiosqlite" in names


def test_optional_fast_extra(pyproject):
    extras = pyproject["project"]["optional-dependencies"]

    assert "fast" in extras
    assert any(dep.startswith("tgcrypto") for dep in extras["fast"])


def test_ruff_target_matches_requires_python(pyproject):
    """Ruff parses with the configured target; a lower value hides 3.12 syntax errors."""
    ruff = pyproject["tool"]["ruff"]

    assert ruff["target-version"] == "py312"


def test_generated_code_is_not_linted(pyproject):
    """The compiler output is regenerated on build, so it must not gate CI."""
    ignores = pyproject["tool"]["ruff"]["lint"]["per-file-ignores"]

    for path in ("newbiegram/raw/functions/*", "newbiegram/raw/types/*"):
        assert ignores.get(path) == ["ALL"]


def test_tl_sources_are_present():
    sources = list((ROOT / "compiler" / "api" / "source").glob("*.tl"))

    assert len(sources) >= 3
    assert any(s.name == "main_api.tl" for s in sources)


def test_compiler_output_is_committed():
    """A clean checkout must be usable without running the compiler first."""
    assert (ROOT / "newbiegram" / "raw" / "functions" / "ping.py").is_file()
    assert (ROOT / "newbiegram" / "raw" / "all.py").is_file()
    assert (ROOT / "newbiegram" / "errors" / "exceptions").is_dir()


def test_no_stale_build_artifacts_are_tracked():
    """PKG-INFO at the repo root shadows the hatchling version and produced a
    wheel named 0.2.8 while the source said 0.3.0a0."""
    assert not (ROOT / "PKG-INFO").exists(), "PKG-INFO must not be committed"


@pytest.mark.timeout(600)
def test_compiler_is_idempotent():
    """Regenerating the raw API must be a no-op on an already-built tree."""
    def snapshot():
        generated = [
            ROOT / "newbiegram" / "raw" / "all.py",
            ROOT / "newbiegram" / "raw" / "functions" / "ping.py",
            ROOT / "newbiegram" / "errors" / "exceptions" / "__init__.py",
        ]
        return {path: path.read_bytes() for path in generated if path.is_file()}

    before = snapshot()
    assert before, "no generated files found to compare"

    result = subprocess.run(
        [sys.executable, "-c", "from compiler.api.compiler import start; start()"],
        cwd=ROOT, capture_output=True, timeout=600, check=False,
    )
    assert result.returncode == 0, result.stderr.decode()[-2000:]

    assert snapshot() == before, "compiler output changed on a second run"


def test_build_hook_is_wired_for_wheel_and_install():
    """hatch_build.py must compile on wheel builds, not just editable installs."""
    hook = (ROOT / "hatch_build.py").read_text()

    assert '"wheel"' in hook
    assert '"install"' in hook
    assert "compile_api()" in hook
    assert "compile_errors()" in hook


def test_community_files_referenced_by_readme_exist():
    """README links to files that were missing from the repository."""
    for name in ("CONTRIBUTING.md", "SECURITY.md", ".github/CODE_OF_CONDUCT.md"):
        assert (ROOT / name).is_file(), f"{name} is linked from README.md but missing"


def test_readme_local_links_resolve():
    """Every relative link in README.md must point at a file that exists."""
    readme = (ROOT / "README.md").read_text()
    missing = []

    for target in re.findall(r"\]\(([^)]+)\)", readme):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue

        path = (ROOT / target.lstrip("./")).resolve()
        if not path.exists():
            missing.append(target)

    assert not missing, f"README links to missing files: {missing}"


def test_no_committed_backup_files():
    """`main_api.tl.layer184.bak` was a 200 KB stale schema, unreferenced by the
    compiler and excluded from the sdist."""
    stale = [p.name for p in (ROOT / "compiler").rglob("*.bak")]

    assert not stale, f"stale backup files in the schema directory: {stale}"


def test_license_files_are_present():
    """MANIFEST.in and the license declaration assume these exist."""
    for name in ("COPYING", "COPYING.lesser", "NOTICE"):
        assert (ROOT / name).is_file()
