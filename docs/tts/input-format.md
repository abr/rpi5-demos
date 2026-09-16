# Input format

The TTS API accepts raw UTF-8 text bytes. The backend normalizes pushed text itself, one sentence
at a time, so numbers, dates, currency amounts, acronyms, and abbreviations can be pushed as-is.
This page describes what that normalization does, the character set the model ends up speaking,
and the SSML markup the model understands.

## Pushing text

Pass text as UTF-8-encoded `bytes` to `abr_sdk.tts.Tts.push`:

```python
tts.push("Dr. Smith owed $42 to the WHO.".encode("utf-8"))
# spoken as "doctor Smith owed forty two dollars to the W H O."
```

## What normalization does

The backend runs these steps, in order, on the spoken text:

| Step                           | Example                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------- |
| Spell out acronyms             | `WHO` → `W H O`, `HTTP2` → `H T T P two`                                        |
| Normalize dates                | `12/25/2024` → `December twenty fifth, two thousand twenty four`                |
| Numbers to words               | `$42.50` → `forty two dollars and fifty cents`, `3.14` → `three point one four` |
| Read a leading minus as a sign | `-5` → `negative five`, `-$3.50` → `negative three dollars and fifty cents`     |
| Unicode normalization          | `é` → `e`, `—` → `,`, `…` → `, , ,`                                             |
| Collapse repeated punctuation  | `!!!!` → `!`                                                                    |
| Collapse whitespace            | multiple spaces → single space                                                  |
| Remove special characters      | drops anything outside the model alphabet                                       |
| Expand abbreviations           | `Dr.` → `doctor`, `St.` → `street`, `etc.` → `et cetera`                        |

A trailing period is added when the utterance has no sentence-ending punctuation, so the synthesis
pipeline has a terminal to flush on.

The minus reads as a sign only directly before a digit, at the start of the text or after
whitespace; ranges (`5-10`), compounds (`COVID-19`), and list bullets (`- 5`) keep the hyphen.

An all-caps token that the pronunciation dictionary knows as a word is spoken as that word rather
than spelled out, so `NASA` is voiced. Tokens shorter than four characters are always spelled, so
`US` and `IT` are not mistaken for the everyday words they spell.

The result uses the restricted character set the model's phoneme dictionary operates on:

| Accepted                      | Examples         |
| ----------------------------- | ---------------- |
| Letters (upper and lowercase) | `a`–`z`, `A`–`Z` |
| Space                         | ` `              |
| Apostrophe                    | `'`              |
| Comma, period                 | `,` `.`          |
| Question mark, exclamation    | `?` `!`          |
| Hyphen                        | `-`              |

## SSML markup

The model supports a subset of SSML (Speech Synthesis Markup Language) for controlling prosody and
emotion. Well-formed tags pass through normalization untouched: only the spoken text between tags
is normalized. Malformed tags (an unquoted attribute value, a missing closing quote) are dropped
with a warning through the SDK log callback, so one bad tag cannot abort the utterance. Tags and
attributes outside the table below are passed through and ignored by the model.

### Supported tags

| Tag                                             | Description                                                                                                                                                                                                                               |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<speak>`                                       | Optional top-level wrapper. A closing `</speak>` forces a pipeline flush.                                                                                                                                                                 |
| `<prosody rate="..." pitch="..." volume="...">` | Controls speech rate, pitch, and volume. Accepts named presets (`x-slow`, `slow`, `medium`, `fast`, `x-fast` for rate; `x-low` through `x-high` for pitch; `silent` through `x-loud` for volume) or percentage values. Tags are nestable. |
| `<abr:emotion type="...">`                      | Applies a composite prosody preset. Nestable with `<prosody>`.                                                                                                                                                                            |

Supported `<abr:emotion>` types: `apologetic`, `calm`, `empathetic`, `firm`, `lively`.

When SSML tags are present, no trailing period is added between or after the spoken runs. Use
explicit sentence-ending punctuation, a `</speak>` tag, or the flush byte to end a tagged
utterance.

> **Next steps**
>
> - [Examples](../tts/examples.md): full examples showing how to synthesize text.
> - [Overview](../tts/overview.md): overview of the TTS streaming model and output format.
