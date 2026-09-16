#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Copy the ABR SDK Sphinx docs into ``docs/``, converting MyST to plain markdown.

The upstream pages are written in MyST for Sphinx: ``{doc}`` cross-references,
``:::{admonition}`` blocks, ``{py:meth}`` roles, toctrees, and YAML frontmatter.
None of that renders on GitHub or reads well as LLM context, so this script
rewrites each construct into ordinary markdown.

Usage:
    ./scripts/sync_docs.py [--source PATH] [--dest PATH]
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

SKIP_DIRS = frozenset(["api", "build", "_static"])

PY_ROLES = frozenset(
    [
        "py:mod",
        "py:class",
        "py:meth",
        "py:func",
        "py:obj",
        "py:attr",
        "py:data",
        "py:exc",
    ]
)

LOCAL_PAGES = [("Hackathon notes", [("raspberry-pi", "Running on a Raspberry Pi 5")])]


def strip_frontmatter(text: str) -> str:
    """Drop the leading YAML frontmatter block, if there is one."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 3)
    if end == -1:
        return text
    return text[end + 5 :].lstrip("\n")


def split_role(text: str, start: int) -> tuple[str, str, int] | None:
    """
    Parse a MyST role at ``text[start] == '{'``.

    Returns
    -------
    tuple or None
        ``(role_name, content, end_index)``, or None if this is not a role.
    """
    close_brace = text.find("}", start)
    if close_brace == -1:
        return None
    name = text[start + 1 : close_brace]
    if len(name) == 0 or "`" in name or "\n" in name:
        return None
    if close_brace + 1 >= len(text) or text[close_brace + 1] != "`":
        return None
    close_tick = text.find("`", close_brace + 2)
    if close_tick == -1:
        return None
    return name, text[close_brace + 2 : close_tick], close_tick + 1


def split_explicit_target(content: str) -> tuple[str | None, str]:
    """Split a MyST role body into its optional label and its target."""
    if content.endswith(">"):
        open_angle = content.rfind("<")
        if open_angle != -1:
            return content[:open_angle].strip(), content[open_angle + 1 : -1]
    return None, content


def doc_link(target: str, page: str, titles: dict[str, str]) -> str:
    """Render a ``{doc}`` role target as a relative markdown link."""
    label, target = split_explicit_target(target)
    slug = target.lstrip("/")
    if label is None:
        label = titles.get(slug, slug)
    depth = page.count("/")
    prefix = "../" * depth
    return f"[{label}]({prefix}{slug}.md)"


def py_target(content: str) -> str:
    """Strip the ``~`` prefix and any explicit ``<target>`` from a py role."""
    label, target = split_explicit_target(content)
    return (label if label is not None else target).lstrip("~")


def convert_roles(line: str, page: str, titles: dict[str, str]) -> str:
    """Rewrite every MyST role on one line into plain markdown."""
    out: list[str] = []
    i = 0
    while i < len(line):
        char = line[i]
        if char == "`":
            close = line.find("`", i + 1)
            if close == -1:
                out.append(line[i:])
                break
            out.append(line[i : close + 1])
            i = close + 1
            continue
        if char == "{":
            parsed = split_role(line, i)
            if parsed is not None:
                name, content, end = parsed
                if name == "doc":
                    out.append(doc_link(content, page, titles))
                    i = end
                    continue
                if name in PY_ROLES:
                    out.append(f"`{py_target(content)}`")
                    i = end
                    continue
        out.append(char)
        i += 1
    return "".join(out)


def convert(text: str, page: str, titles: dict[str, str]) -> str:
    """Convert one MyST page into plain markdown."""
    lines = strip_frontmatter(text).split("\n")
    out: list[str] = []
    in_code = False
    skipping = False
    toctree: list[str] = []
    code_fence = ""
    in_admonition = False

    for raw in lines:
        stripped = raw.strip()

        if skipping:
            if stripped == code_fence:
                skipping = False
                code_fence = ""
            else:
                toctree.append(stripped)
            continue

        if in_code:
            if stripped == code_fence:
                in_code = False
            out.append(quote(raw, in_admonition))
            continue

        if stripped.startswith("```"):
            fence = stripped[: len(stripped) - len(stripped.lstrip("`"))]
            directive = stripped[len(fence) :].strip()
            code_fence = fence
            if directive == "{toctree}":
                skipping = True
                continue
            in_code = True
            out.append(
                quote(fence if directive.startswith("{") else raw, in_admonition)
            )
            continue

        if stripped.startswith(":::"):
            directive = stripped.lstrip(":").strip()
            if in_admonition:
                in_admonition = False
                out.append("")
            if len(directive) == 0:
                continue
            if last_was_admonition(out):
                out.extend(["<!-- -->", ""])
            out.append(quote(f"**{admonition_title(directive)}**", True))
            out.append(quote("", True))
            in_admonition = True
            continue

        if in_admonition and stripped.startswith(":class:"):
            continue

        out.append(quote(convert_roles(raw, page, titles), in_admonition))

    out.extend(render_contents(toctree, titles))
    return collapse_blank(reflow(out))


def reflow(lines: list[str], width: int = 100) -> list[str]:
    """Wrap prose that the link rewriting pushed past the line limit."""
    out: list[str] = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "> ```")):
            in_code = not in_code
        if in_code or len(line) <= width or stripped.startswith(("|", "#")):
            out.append(line)
            continue
        out.extend(fold(line, width))
    return out


def fold(line: str, width: int) -> list[str]:
    """Wrap one long line, preserving its quote and list markers."""
    marker = next((m for m in ("> - ", "> ", "- ") if line.startswith(m)), "")
    if marker.startswith("> "):
        cont = "> " + " " * (len(marker) - 2)
    else:
        cont = " " * len(marker)
    return textwrap.wrap(
        line[len(marker) :],
        width=width,
        initial_indent=marker,
        subsequent_indent=cont,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [line]


def render_contents(toctree: list[str], titles: dict[str, str]) -> list[str]:
    """Turn the collected toctree entries into a markdown table of contents."""
    if len(toctree) == 0:
        return []
    out = ["", "## Contents"]
    caption = ""
    entries: list[str] = []

    def flush() -> None:
        if len(entries) == 0:
            return
        out.extend(["", f"### {caption}", ""])
        out.extend(entries)
        entries.clear()

    for entry in toctree:
        if entry.startswith(":caption:"):
            flush()
            caption = entry[len(":caption:") :].strip()
            continue
        if len(entry) == 0 or entry.startswith(":") or entry.endswith(">"):
            continue
        slug = entry.lstrip("/")
        if slug == "api/index":
            entries.append("- [Python API reference](api/reference.md)")
        elif slug in titles:
            entries.append(f"- [{titles[slug]}]({slug}.md)")
        else:
            print(
                f"warning: toctree entry {slug!r} has no copied page", file=sys.stderr
            )
    flush()
    for local_caption, pages in LOCAL_PAGES:
        caption = local_caption
        entries.extend(f"- [{title}]({slug}.md)" for slug, title in pages)
        flush()
    return out


def last_was_admonition(out: list[str]) -> bool:
    """Report whether the lines so far end with a block quote."""
    for line in reversed(out):
        if len(line.strip()) == 0:
            continue
        return line.startswith(">")
    return False


def admonition_title(directive: str) -> str:
    """Derive the bold label to use for an admonition directive."""
    if directive.startswith("{admonition}"):
        return directive[len("{admonition}") :].strip() or "Note"
    return directive.strip("{}").capitalize()


def quote(line: str, quoted: bool) -> str:
    """Prefix a line with a block-quote marker when inside an admonition."""
    if not quoted:
        return line
    if len(line.strip()) == 0:
        return ">"
    return "> " + line.strip()


def collapse_blank(lines: list[str]) -> str:
    """Join lines, collapsing runs of blank lines into one."""
    out: list[str] = []
    blank = 0
    for line in lines:
        if len(line.strip()) == 0 or line.strip() == ">":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(line.rstrip())
    while len(out) > 0 and len(out[-1].strip()) == 0:
        out.pop()
    return "\n".join(out) + "\n"


def find_pages(source: Path) -> list[str]:
    """List every hand-written upstream page, relative to *source*."""
    pages = []
    for path in sorted(source.rglob("*.md")):
        relative = path.relative_to(source)
        if len(SKIP_DIRS & set(relative.parts)) == 0:
            pages.append(str(relative))
    return pages


def read_titles(source: Path, pages: list[str]) -> dict[str, str]:
    """Map each page slug to its first-level heading."""
    titles: dict[str, str] = {}
    for page in pages:
        slug = page[: -len(".md")]
        for line in (source / page).read_text().split("\n"):
            if line.startswith("# "):
                titles[slug] = line[2:].strip()
                break
    return titles


def main() -> None:
    """Convert every page listed in PAGES into the destination directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "Code" / "abr-sdk" / "abr-sdk-py" / "docs",
        help="abr-sdk-py/docs checkout to copy from",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs",
        help="destination docs directory",
    )
    args = parser.parse_args()

    pages = find_pages(args.source)
    titles = read_titles(args.source, pages)
    for page in pages:
        target = args.dest / page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(convert((args.source / page).read_text(), page, titles))
        print(f"wrote {target.relative_to(args.dest.parent)}")


if __name__ == "__main__":
    main()
