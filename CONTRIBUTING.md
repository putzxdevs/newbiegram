# Contributing to NewbieGram

Thanks for your interest in improving NewbieGram. This document covers how to
get set up and what we look for in a pull request.

## Getting started

NewbieGram requires **Python 3.12 or newer**. Anything older will fail to import,
because the SOCKS layer uses PEP 695 `type` aliases.

```bash
git clone https://github.com/putzxdevs/newbiegram.git
cd newbiegram

python3.12 -m venv .venv
source .venv/bin/activate

pip install -e ".[fast]"
pip install pytest pytest-asyncio pytest-timeout
```

Run the test suite and the linter before opening a pull request:

```bash
pytest tests/ -v
ruff check .
```

CI runs the tests on Python 3.12 and 3.13 across Linux, macOS and Windows, so a
change that only works on one platform will be caught.

## Project layout

| Path | Contents |
|---|---|
| `newbiegram/` | The library. Hand-written code lives here. |
| `newbiegram/raw/` | **Generated.** Do not edit. |
| `newbiegram/errors/exceptions/` | **Generated.** Do not edit. |
| `compiler/` | Reads the `.tl` schema in `compiler/api/source/` and generates the two directories above. |
| `tests/` | pytest suite. |

### Never edit generated files

`newbiegram/raw/functions/`, `newbiegram/raw/types/`, `newbiegram/raw/base/`,
`newbiegram/raw/all.py` and `newbiegram/errors/exceptions/` are regenerated from
`compiler/api/source/*.tl` on every build (see `hatch_build.py`). Any edit there
is lost on the next build. To change the API surface, edit the `.tl` sources and
rebuild:

```bash
python -c "from compiler.api.compiler import start; start()"
python -c "from compiler.errors.compiler import start; start()"
```

Ruff is configured to ignore the generated tree, so lint failures there are not
something you need to fix.

## Reporting bugs

Open an issue with:

- the NewbieGram version (`python -c "import newbiegram; print(newbiegram.__version__)"`)
- your Python version and OS
- a minimal snippet that reproduces the problem
- the full traceback, with `logging` output if it helps

If the failure involves a specific Telegram RPC error, include the error code
and the raw payload — many of these are layer-specific.

## Pull requests

- Keep the change focused; unrelated cleanups belong in a separate PR.
- Add or update tests for behaviour you change.
- Make sure `pytest` and `ruff check` both pass.
- Describe what changed and why in the PR body.

## Adding a new method

Methods mirror the Telegram API, so adding one usually means:

1. Add the signature to `compiler/api/source/main_api.tl`.
2. Run the compiler to regenerate `newbiegram/raw/`.
3. Add the high-level wrapper in `newbiegram/methods/`.
4. Expose it on `Client` in `newbiegram/methods/`.
5. Add a test.

## Code style

Ruff handles formatting and linting; `ruff format` is available but not enforced,
since the existing codebase predates it. Match the surrounding code rather than
reformatting files you are only lightly touching.

## Code of Conduct

Participation in this project is governed by the
[Code of Conduct](.github/CODE_OF_CONDUCT.md). Please read it before
contributing.