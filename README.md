# dataforge

> Convert, validate, and merge between JSON, YAML, TOML, CSV, and XML.

[![PyPI](https://img.shields.io/pypi/v/kryptorious-dataforge)](https://pypi.org/project/kryptorious-dataforge/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Part of the [Kryptorious developer toolkit](https://kryptorious.gumroad.com/l/jbvet) — 31 open-source tools, one $9 lifetime license.

## Install

```bash
pip install kryptorious-dataforge
```

## Quickstart

```bash
printf '{"a":1}\n' > 1.json
printf "b: 2\n" > 2.yaml
dataforge merge 1.json 2.yaml merged.json
# -> {"a":1,"b":2}
```

## Commands

| Command | Description |
|---------|-------------|
| `dataforge convert a.json b.yaml` | Convert between any two formats. |
| `dataforge merge a.json b.yaml merged.json` | Deep-merge multiple files into one. |
| `dataforge validate data.toml` | Validate a file's syntax. |
| `dataforge view config.yaml` | Pretty-print any data file. |



## License

MIT — free for personal and commercial use. The $9 lifetime license adds DevFlow Premium (multi-environment CI/CD, approval gates, infrastructure-as-code). Get it at [kryptorious.gumroad.com/l/jbvet](https://kryptorious.gumroad.com/l/jbvet).
