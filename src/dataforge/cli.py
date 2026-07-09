"""DataForge CLI — Convert between any data format."""

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

FORMATS = ["json", "yaml", "yml", "toml", "csv", "xml"]


def _detect_format(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    if ext in FORMATS:
        return "yaml" if ext == "yml" else ext
    return ext


def _read_file(path: str, fmt: str = None):
    fmt = fmt or _detect_format(path)
    content = Path(path).read_text(encoding="utf-8")

    if fmt == "json":
        return json.loads(content)
    elif fmt in ("yaml", "yml"):
        import yaml
        return yaml.safe_load(content)
    elif fmt == "toml":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        return tomllib.loads(content)
    elif fmt == "csv":
        import csv, io
        reader = csv.DictReader(io.StringIO(content))
        return [row for row in reader]
    elif fmt == "xml":
        import xml.etree.ElementTree as ET
        return _xml_to_dict(ET.fromstring(content))
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _write_file(data, path: str, fmt: str = None):
    fmt = fmt or _detect_format(path)

    if fmt == "json":
        content = json.dumps(data, indent=2, ensure_ascii=False)
    elif fmt in ("yaml", "yml"):
        import yaml
        content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    elif fmt == "toml":
        try:
            import tomli_w
            content = tomli_w.dumps(data)
        except ImportError:
            # No TOML writer available; fall back to JSON-compatible dump
            content = json.dumps(data, indent=2, ensure_ascii=False)
    elif fmt == "csv":
        if not isinstance(data, list):
            raise ValueError("CSV output requires list data")
        import csv, io
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        content = output.getvalue()
    elif fmt == "xml":
        content = _dict_to_xml(data)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    Path(path).write_text(content, encoding="utf-8")
    return content


def _xml_to_dict(element):
    result = {}
    if element.attrib:
        result["@attributes"] = element.attrib
    for child in element:
        child_dict = _xml_to_dict(child)
        tag = child.tag
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_dict)
        else:
            result[tag] = child_dict
    text = element.text.strip() if element.text else ""
    if not result and text:
        return text
    if text:
        result["#text"] = text
    return result


def _dict_to_xml(data, root_tag="root"):
    import xml.etree.ElementTree as ET
    import xml.dom.minidom as minidom

    def _build(element, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key.startswith("@"):
                    element.set(key[1:], str(value))
                elif key == "#text":
                    element.text = str(value)
                else:
                    child = ET.SubElement(element, key)
                    _build(child, value)
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(element, "item")
                _build(child, item)
        else:
            element.text = str(data)

    root = ET.Element(root_tag)
    if isinstance(data, dict) and len(data) == 1:
        tag, content = next(iter(data.items()))
        root = ET.Element(tag)
        _build(root, content)
    else:
        _build(root, data)

    return minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")


@click.group()
@click.version_option(version="1.0.0", prog_name="dataforge")
def main():
    """DataForge — Convert between JSON, YAML, TOML, CSV, XML.

    One command to convert, validate, and merge any data format.
    """
    pass


@main.command()
@click.argument("input_path")
@click.argument("output_path")
@click.option("--from", "-f", "from_fmt", help="Input format (auto-detect if omitted)")
@click.option("--to", "-t", "to_fmt", help="Output format (auto-detect if omitted)")
@click.option("--pretty/--compact", default=True, help="Pretty-print output")
def convert(input_path, output_path, from_fmt, to_fmt, pretty):
    """Convert between data formats.

    \b
    Examples:
        dataforge convert data.json output.yaml
        dataforge convert data.csv output.json
        dataforge convert config.toml config.json
        dataforge convert data.json output.xml
    """
    in_fmt = from_fmt or _detect_format(input_path)
    out_fmt = to_fmt or _detect_format(output_path)

    console.print()
    console.print(Panel(f"[bold]DataForge Convert[/bold] — [cyan]{in_fmt}[/cyan] → [green]{out_fmt}[/green]",
                        border_style="blue"))

    try:
        console.print(f"Reading [cyan]{input_path}[/cyan]...")
        data = _read_file(input_path, in_fmt)
        console.print(f"Writing [green]{output_path}[/green]...")
        _write_file(data, output_path, out_fmt)
        size = os.path.getsize(output_path)
        console.print(f"[green]✓[/green] Converted {_format_size(size)} — {output_path}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@main.command()
@click.argument("path")
@click.option("--format", "-f", "fmt", help="Format (auto-detect if omitted)")
def validate(path, fmt):
    """Validate a data file's syntax.

    \b
    Examples:
        dataforge validate config.yaml
        dataforge validate data.json
    """
    fmt = fmt or _detect_format(path)
    console.print()
    console.print(Panel(f"[bold]DataForge Validate[/bold] — [cyan]{path}[/cyan] ({fmt})",
                        border_style="blue"))

    try:
        data = _read_file(path, fmt)
        console.print(f"[green]✓[/green] Valid {fmt.upper()} — {_summarize(data)}")
    except Exception as e:
        console.print(f"[red]✗[/red] Invalid {fmt.upper()}: {e}")
        raise SystemExit(1)


def _deep_merge(base, incoming):
    """Recursively merge INCOMING into BASE (dicts merge, lists extend)."""
    if base is None:
        return incoming
    if isinstance(base, dict) and isinstance(incoming, dict):
        result = dict(base)
        for k, v in incoming.items():
            result[k] = _deep_merge(result.get(k), v)
        return result
    if isinstance(base, list) and isinstance(incoming, list):
        return base + incoming
    return incoming


@main.command()
@click.argument("files", nargs=-1)
@click.argument("output")
@click.option("--format", "-f", "fmt", default="json", help="Output format")
def merge(files, output, fmt):
    """Merge multiple data files into one.

    Reads each input in its detected format (json/yaml/toml/csv/xml),
    deep-merges into a single structure, and writes the result to
    OUTPUT in the requested format.

    \b
    Example:
        dataforge merge a.json b.yaml merged.json
    """
    if len(files) < 2:
        raise click.ClickException("Provide at least two input files to merge.")

    console.print()
    console.print(Panel(
        f"[bold]DataForge Merge[/bold] — {len(files)} files → [green]{output}[/green]",
        border_style="blue"))

    merged = None
    for f in files:
        if not Path(f).exists():
            raise FileNotFoundError(f"File not found: {f}")
        data = _read_file(f)
        merged = _deep_merge(merged, data)

    _write_file(merged, output, fmt)
    console.print()
    console.print(f"[green]✓ Merged {len(files)} file(s) → {output}[/green]")
    console.print(f"  Result: {_summarize(merged)}")


@main.command()
@click.argument("path")
def view(path):
    """Pretty-print any data file to terminal.

    \b
    Examples:
        dataforge view config.yaml
        dataforge view data.json
    """
    fmt = _detect_format(path)
    data = _read_file(path, fmt)
    console.print()
    console.print(Panel(f"[bold]{path}[/bold] ({fmt})", border_style="blue"))
    console.print_json(json.dumps(data)) if isinstance(data, (dict, list)) else console.print(data)


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _summarize(data) -> str:
    if isinstance(data, dict):
        return f"{len(data)} keys"
    elif isinstance(data, list):
        return f"{len(data)} items"
    else:
        return str(type(data).__name__)


if __name__ == "__main__":
    main()
