#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Generate a plain-markdown API reference for the public ``abr_sdk`` surface.

Upstream publishes an autodoc2 reference, but its output is MyST directives and
list-tables that read poorly outside Sphinx. This walks the source with ``ast``
instead, so no import and no compiled library are needed, and emits signatures
plus docstrings as markdown.

Only the modules a hackathon participant should touch are included; ``cabi``,
``keygen``, and the private helpers are skipped.

Usage:
    ./scripts/gen_api_docs.py [--source PATH] [--dest PATH]
"""

from __future__ import annotations

import argparse
import ast
import textwrap
from pathlib import Path

MODULES = {
    "asr": ["AsrMode", "Asr", "AsrChunk", "AsrTranscript", "Processor"],
    "tts": ["Tts", "Processor"],
    "core": [
        "Library",
        "Application",
        "Buffer",
        "BufferDirection",
        "EventSet",
        "EventFlags",
        "Event",
    ],
    "exceptions": None,
}

SKIP_METHODS = frozenset(["__enter__", "__exit__", "__repr__", "__str__", "__del__"])


def unparse_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Render a function signature, wrapping it if it is long."""
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    flat = f"{node.name}({args}){returns}"
    if len(flat) <= 100:
        return flat
    wrapped = ",\n    ".join(split_args(args))
    return f"{node.name}(\n    {wrapped},\n){returns}"


def split_args(args: str) -> list[str]:
    """Split an argument list on its top-level commas."""
    out: list[str] = []
    depth = 0
    start = 0
    for i, char in enumerate(args):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            out.append(args[start:i].strip())
            start = i + 1
    out.append(args[start:].strip())
    return [arg for arg in out if len(arg) > 0]


def clean_docstring(doc: str | None, heading: str = "###") -> str:
    """Normalize a docstring and soften the RST that upstream uses."""
    if doc is None:
        return ""
    doc = doc.split("\n\nAuthor:")[0]
    softened = [soften_rst(line) for line in unsetext(doc.split("\n"), heading)]
    return "\n".join(wrap(fence(bullets(softened)))).strip()


def unsetext(lines: list[str], heading: str) -> list[str]:
    """Turn numpydoc section underlines into real headings."""
    out: list[str] = []
    for line in lines:
        underline = line.strip()
        if len(underline) > 0 and set(underline) <= {"-"} and len(out) > 0:
            title = out[-1].strip()
            if len(title) > 0 and len(underline) >= len(title):
                out[-1] = f"{heading}# {title}"
                out.append("")
                continue
        out.append(line)
    return out


def bullets(lines: list[str]) -> list[str]:
    """Render numpydoc parameter blocks as bullets instead of indented text."""
    out: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("#"):
            in_section = line.lstrip("#").strip() in (
                "Parameters",
                "Returns",
                "Raises",
                "Yields",
            )
            out.append(line)
            continue
        if not in_section:
            out.append(line)
            continue
        if line.startswith("    ") and len(line.strip()) > 0:
            if len(out) > 0 and out[-1].startswith("- "):
                out[-1] = f"{out[-1]} {line.strip()}"
            else:
                out.append(line.strip())
        elif len(line.strip()) > 0:
            out.append(f"- `{line.strip()}`:")
        else:
            out.append(line)
    return out


def fence(lines: list[str]) -> list[str]:
    """
    Convert indented RST literal blocks into fenced code blocks.

    NB: must run after ``bullets``, which consumes the indented continuation
    lines inside numpydoc sections. Run first, it would fence them instead.
    """
    out: list[str] = []
    in_block = False
    for line in lines:
        indented = line.startswith("    ") and len(line.strip()) > 0
        if indented and not in_block and follows_colon(out):
            in_block = True
            out.append("```python")
        elif in_block and len(line.strip()) > 0 and not indented:
            in_block = False
            close(out)
        out.append(line[4:] if in_block else line)
    if in_block:
        close(out)
    return out


def wrap(lines: list[str], width: int = 100) -> list[str]:
    """Reflow over-long bullet lines, leaving code and tables alone."""
    out: list[str] = []
    for line in lines:
        if len(line) <= width or not line.startswith("- "):
            out.append(line)
            continue
        out.extend(
            textwrap.wrap(
                line,
                width=width,
                subsequent_indent="  ",
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return out


def follows_colon(out: list[str]) -> bool:
    """Report whether the last non-blank line introduces a literal block."""
    for line in reversed(out):
        if len(line.strip()) == 0:
            continue
        return line.rstrip().endswith(":")
    return False


def close(out: list[str]) -> None:
    """Close an open fence, trimming blank lines before it."""
    while len(out) > 0 and len(out[-1].strip()) == 0:
        out.pop()
    out.extend(["```", ""])


def soften_rst(line: str) -> str:
    """Replace RST roles and markup with their markdown equivalents."""
    for role in (":class:", ":meth:", ":func:", ":attr:", ":mod:", ":exc:"):
        line = line.replace(role + "`", "`")
    line = line.replace("``", "`")
    if line.rstrip().endswith("::"):
        line = line.rstrip()[:-1]
    return escape_dunders(line)


def escape_dunders(line: str) -> str:
    """Wrap bare ``__name__`` tokens in backticks so they do not read as bold."""
    out: list[str] = []
    for i, span in enumerate(line.split("`")):
        if i % 2 == 1 or "__" not in span:
            out.append(span)
            continue
        words = [
            f"`{word}`"
            if word.startswith("__") and word.endswith("__") and len(word) > 4
            else word
            for word in span.split(" ")
        ]
        out.append(" ".join(words))
    return "`".join(out)


def render_function(node: ast.FunctionDef, heading: str) -> list[str]:
    """Render one function, method, or property as markdown lines."""
    decs = [ast.unparse(dec) for dec in node.decorator_list]
    out = [f"{heading} `{node.name}`", ""]
    if "property" in decs:
        returns = ast.unparse(node.returns) if node.returns is not None else None
        out.append(f"*Property.* Returns `{returns}`." if returns else "*Property.*")
        out.append("")
    else:
        prefix = "@staticmethod " if "staticmethod" in decs else ""
        out.extend(["```python", f"{prefix}{unparse_signature(node)}", "```", ""])
    doc = clean_docstring(ast.get_docstring(node), heading)
    if len(doc) > 0:
        out.extend([doc, ""])
    return out


def render_class(node: ast.ClassDef) -> list[str]:
    """Render one class and its public members as markdown lines."""
    bases = ", ".join(ast.unparse(base) for base in node.bases)
    title = f"### `{node.name}`" + (f" (extends `{bases}`)" if len(bases) > 0 else "")
    out = [title, ""]
    doc = clean_docstring(ast.get_docstring(node), "###")
    if len(doc) > 0:
        out.extend([doc, ""])

    enum_members = [
        f"- `{node.name}.{stmt.targets[0].id}` = `{ast.unparse(stmt.value)}`"
        for stmt in node.body
        if isinstance(stmt, ast.Assign)
        and len(stmt.targets) == 1
        and isinstance(stmt.targets[0], ast.Name)
        and not stmt.targets[0].id.startswith("_")
    ]
    if len(enum_members) > 0:
        out.extend(["#### Members", "", *enum_members, ""])

    for stmt in node.body:
        if not isinstance(stmt, ast.FunctionDef):
            continue
        if stmt.name in SKIP_METHODS:
            continue
        if stmt.name.startswith("_") and stmt.name != "__init__":
            continue
        if stmt.name == "__init__" and internal_constructor(node):
            continue
        out.extend(render_function(stmt, "####"))
    return out


def internal_constructor(node: ast.ClassDef) -> bool:
    """Report whether instances of this class come from the library, not the caller."""
    return any(ast.unparse(base) == "Handle" for base in node.bases)


def render_module(name: str, path: Path, wanted: list[str] | None) -> list[str]:
    """Render the wanted members of one module as markdown lines."""
    tree = ast.parse(path.read_text())
    out = [f"## `abr_sdk.{name}`", ""]
    doc = clean_docstring(ast.get_docstring(tree), "##")
    if len(doc) > 0:
        out.extend([doc, ""])

    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            if wanted is not None and stmt.name not in wanted:
                continue
            if wanted is None and stmt.name.startswith("_"):
                continue
            out.extend(render_class(stmt))
        elif isinstance(stmt, ast.FunctionDef) and not stmt.name.startswith("_"):
            if wanted is not None and stmt.name not in wanted:
                continue
            out.extend(render_function(stmt, "###"))
    return out


def main() -> None:
    """Write the API reference for every module in MODULES."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "Code" / "abr-sdk" / "abr-sdk-py" / "abr_sdk",
        help="abr_sdk package directory to read",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "docs"
        / "api"
        / "reference.md",
        help="markdown file to write",
    )
    args = parser.parse_args()

    out = [
        "# Python API reference",
        "",
        "The public `abr_sdk` surface, generated from the package source. For",
        "task-oriented walkthroughs start with the",
        "[ASR overview](../asr/overview.md) or the",
        "[TTS overview](../tts/overview.md) instead.",
        "",
    ]
    for name, wanted in MODULES.items():
        out.extend(render_module(name, args.source / f"{name}.py", wanted))

    args.dest.parent.mkdir(parents=True, exist_ok=True)
    args.dest.write_text("\n".join(out).rstrip() + "\n")
    print(f"wrote {args.dest}")


if __name__ == "__main__":
    main()
