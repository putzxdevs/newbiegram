<p align="center">
    <a href="https://github.com/putzxdevs/newbiegram">
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/putzxdevs/newbiegram/main/docs/source/_static/newbiegram-dark.png">
            <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/putzxdevs/newbiegram/main/docs/source/_static/newbiegram-light.png">
            <img alt="NewbieGram" width="128" src="https://raw.githubusercontent.com/putzxdevs/newbiegram/main/docs/source/_static/newbiegram-light.png">
        </picture>
    </a>
    <br>
    <b>Python Framework for the Telegram MTProto API</b>
    <br>
    <a href="https://github.com/putzxdevs/newbiegram">
        Homepage
    </a>
    •
    <a href="https://github.com/putzxdevs/newbiegram/blob/main/README.md">
        Documentation
    </a>
    •
    <a href="https://github.com/putzxdevs/newbiegram/releases">
        Releases
    </a>
    •
    <a href="https://t.me/putzxdevs">
        News
    </a>
</p>

# NewbieGram

[![We use Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI package version](https://img.shields.io/pypi/v/newbiegram.svg)](https://pypi.python.org/pypi/newbiegram)
[![PyPI license](https://img.shields.io/pypi/l/newbiegram.svg)](https://pypi.python.org/pypi/newbiegram)
[![PyPI python versions](https://img.shields.io/pypi/pyversions/newbiegram.svg)](https://pypi.python.org/pypi/newbiegram)
[![PyPI download month](https://img.shields.io/pypi/dm/newbiegram.svg)](https://pypi.python.org/pypi/newbiegram/)
[![GitHub Actions status](https://github.com/putzxdevs/newbiegram/actions/workflows/python.yml/badge.svg)](https://github.com/putzxdevs/newbiegram/actions)

## Description

NewbieGram is a Python library for interacting with the Telegram MTProto API. It provides a simple and intuitive interface for developers to leverage the power of Telegram's API in their Python applications. It is a fork of [Hydrogram](https://github.com/hydrogram/hydrogram) tracking the latest Telegram API layer.

## Installation

NewbieGram requires **Python 3.12 or newer**.

```bash
pip install newbiegram -U
```

For the optional AES accelerator (recommended in production):

```bash
pip install "newbiegram[fast] -U"
```

## Usage

```python
from newbiegram import Client, filters

app = Client("my_account")


@app.on_message(filters.private)
async def hello(client, message):
    await message.reply("Hello from NewbieGram!")


app.run()
```

## Features

- **Easy to use:** a clean, intuitive interface for the Telegram MTProto API, while still allowing advanced usages.
- **Elegant:** low-level details are abstracted and re-presented in a more convenient way, making the Telegram API more accessible.
- **Fast:** boosted by [TgCrypto](https://github.com/pyrogram/tgcrypto), a high-performance cryptography library written in C, which makes it faster than other Python Telegram libraries.
- **Type-hinted:** types and methods are all type-hinted, enabling excellent editor support and making it easier to write and maintain code.
- **Async:** fully asynchronous, which means it can handle multiple requests at the same time, making it faster and more efficient.
- **Powerful:** full access to Telegram's API to execute any official client action and more, giving developers the flexibility to build powerful applications.

## Resources

- The [project README](https://github.com/putzxdevs/newbiegram/blob/main/README.md) is the entry point for installation, quickstart, and contribution guidelines.
- The [API reference](https://github.com/putzxdevs/newbiegram/blob/main/newbiegram) is generated from the in-tree `newbiegram/` package — open the module in your editor or browse it on GitHub.
- The [release notes](https://github.com/putzxdevs/newbiegram/releases) and the `news/` directory cover what changed in each version.
- The [issue tracker](https://github.com/putzxdevs/newbiegram/issues) is where bugs and feature requests should go.
- The [Telegram channel](https://t.me/putzxdevs) is where news and updates get posted.

## Contributing

NewbieGram is an open source project and we welcome contributions from the community. We appreciate all types of contributions, including bug reports, feature requests, documentation improvements, and code contributions.

To get started, please review our [Contribution Guidelines](https://github.com/putzxdevs/newbiegram/blob/main/CONTRIBUTING.md) for more information.

All contributors are expected to adhere to the [Code of Conduct](https://github.com/putzxdevs/newbiegram/blob/main/.github/CODE_OF_CONDUCT.md). Please read it before contributing.

We appreciate your help in making NewbieGram better!

## Support

NewbieGram is an open source project maintained by its contributors. If you want to support ongoing development, open an issue or send a pull request — that's what keeps the project alive.

## Thanks

- [Pyrogram](https://github.com/pyrogram/pyrogram) and its contributors for the inspiration and base code.
- [Hydrogram](https://github.com/hydrogram/hydrogram) and its contributors — NewbieGram is a direct fork of that project.

## License

You may copy, distribute and modify the software provided that modifications are described and licensed for free under [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html). Derivatives works (including modifications or anything statically linked to the library) can only be redistributed under LGPL-3, but applications that use the library don't have to be.
