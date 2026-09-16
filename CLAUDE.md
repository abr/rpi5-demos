# Notes for coding assistants

Context for anyone writing ABR SDK code. The full documentation is in `docs/`;
read it rather than guessing at the API.

## What this repository is

Demos and documentation for the ABR SDK on a Raspberry Pi 5. The SDK does
streaming speech recognition (ASR) and speech synthesis (TTS) on the device.

- `asr-led-demo/led_demo.py` drives LEDs from continuous voice commands.
- `llm-pipeline-demo/llm_demo.py` is a spoken conversation loop through Gemini.
- `docs/` is the SDK documentation as plain markdown.
- `samples/` holds two clips in the ASR's input format.

Each demo is a single self-contained file with PEP 723 inline dependencies, run
with `uv`. Keep it that way. Do not factor shared helpers out into a common
module; people copy one file and hack on it, and that is the point.

## Facts that are easy to get wrong

**Audio is always 16 kHz, mono, signed 16-bit little-endian PCM.** Both
directions, no exceptions. Wrong-format audio produces confident gibberish
rather than an error.

**ASR text chunks replace, they do not append.** A chunk carries
`replace_byte_offset_begin` and `replace_byte_offset_end`, both non-positive,
counted back from the end of the transcript so far. Later passes revise earlier
guesses. Apply each chunk with `chunk.update(buf)` on a `bytearray`, or collect
them in an `AsrTranscript` and read `.text`. Concatenating chunk payloads gives
you a transcript with duplicated and stale words.

**The models are not in this repository.** They ship as application packages,
one `.tar.gz` per combination of task, language, model, and platform. Each
unpacks to a directory holding a `lib*.so` plus model blobs. Construct `Asr` or
`Tts` with the path to that `.so`.

**Packages live under `~/abr-packages`**, set by `ABR_PACKAGES_ROOT` at the top
of each demo script. A Pi 5 needs the `linux-arm64` builds.

**Activation only happens once**, using any application package, with network access:
`abr-sdk activate <path-to-.so> --key-file abr_license.key`. Inference is
offline afterwards. An unactivated device raises `AbrSdkError` with
`ERR_LICENSE`.

**`push` is non-blocking, `wait_for_completion` is blocking.** `push` returns as soon
as the bytes are accepted. Call `wait_for_completion` after the last chunk to
flush the pipeline and deliver every pending callback. Forgetting it silently
truncates the tail of the output.

**Use the context manager.** `Asr` and `Tts` hold a native handle. `with` closes
it; leaking one leaks the model's memory.

## Which page answers which question

| Question                                 | Page                                     |
| ---------------------------------------- | ---------------------------------------- |
| How do I install and get a package?      | `docs/getting-started/installation.md`   |
| How do I transcribe from a microphone?   | `docs/getting-started/asr-quickstart.md` |
| How do I synthesize a sentence?          | `docs/getting-started/tts-quickstart.md` |
| What is the exact signature of X?        | `docs/api/reference.md`                  |
| Why did the transcript change under me?  | `docs/asr/transcription-stages.md`       |
| What audio format, exactly?              | `docs/asr/input-format.md`               |
| How do push and callbacks actually work? | `docs/concepts/streaming-and-chunks.md`  |
| What do package names mean?              | `docs/concepts/naming.md`                |
| When are handles created and destroyed?  | `docs/concepts/sdk-lifecycle.md`         |
| Which voices exist?                      | `docs/tts/voices.md`                     |
| Audio, GPIO, or throttling on the Pi     | `docs/raspberry-pi.md`                   |
| Something else                           | `docs/faq.md`                            |

## Conventions

- Python 3.10 or newer. Modern typing: `str | None`, `list`, `dict`.
- `pathlib.Path`, never `os.path`.
- Run things with `uv run`, never bare `python`.
- The docs in `docs/` are generated. To change them, fix `scripts/sync_docs.py`
  or `scripts/gen_api_docs.py` rather than editing the output. See
  [docs/SOURCE.md](docs/SOURCE.md) for the full refresh recipe.
