# Where these docs came from

Most of `docs/` is a local copy of the ABR SDK Python documentation, which is
published at <https://docs.appliedbrainresearch.com/sdk/>. The copy exists so
that the pages sit in the repository alongside the demos, where both people and
coding assistants can read them without a network round trip.

Two pages are not copies. `raspberry-pi.md` was written for this hackathon, and
this file describes the copy itself. Everything else is generated.

The copy was done on 2026-09-16.

## What changed in the copy

The upstream pages are MyST for Sphinx, which does not render on GitHub. The
`scripts/sync_docs.py` script rewrites each construct into ordinary markdown:

- `{doc}` cross-references become relative links between the copied pages.
- `:::{admonition}` and `:::{note}` blocks become block quotes with a bold label.
- `{py:meth}` and friends become inline code spans.
- YAML frontmatter is dropped, and the toctrees on the index page become a
  markdown table of contents.

The API reference is not the upstream autodoc2 output, which is also MyST. It is
regenerated from the package source by `scripts/gen_api_docs.py`. It covers
`asr`, `tts`, and `exceptions` in full. From `core` it takes only the types you
handle directly: `Library`, `Application`, `Buffer`, `BufferDirection`,
`EventSet`, `EventFlags`, and `Event`. The C ABI bindings, the licensing client,
and the internal handle plumbing are left out, as are the constructors of classes
the library hands you rather than you building.

## Refreshing

With an `abr-sdk` checkout next to this one:

```bash
./scripts/sync_docs.py
./scripts/gen_api_docs.py
bones format --no-notice
```

Both scripts accept `--source` if your checkout lives somewhere else. The
formatting step is required, not a tidy-up: the scripts emit correct markdown but
do not align tables, so committing without it leaves the copy failing lint. The
upstream commit above is recorded by hand, so check it when you re-sync.

The published site is always authoritative; this copy will drift.
