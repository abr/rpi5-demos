# Voices

A voice in Nith TTS is a specific application package. You select a voice by pointing
`LIBRARY_PATH` at the `libnith_5m_live.so` inside the extracted package directory for
that voice; the Python API is the same regardless of which voice you load.

## Built-in voices

Two English voices are available:

| Voice | Package              | Description  |
| ----- | -------------------- | ------------ |
| `f1`  | `nith-5m-live.en-f1` | Female voice |
| `m1`  | `nith-5m-live.en-m1` | Male voice   |

The full package name appends the target platform, for example
`nith-5m-live.en-f1-linux-x86_64`; see [Package naming](../concepts/naming.md).

Both packages contain a shared library named `libnith_5m_live.so`. To switch voices,
point `LIBRARY_PATH` at the `.so` in the other package directory; no code change is
required:

```python
from abr_sdk.tts import Tts

# Female voice
LIBRARY_PATH = "/path/to/nith-5m-live.en-f1/libnith_5m_live.so"

# Male voice
LIBRARY_PATH = "/path/to/nith-5m-live.en-m1/libnith_5m_live.so"
```

See [Examples](../tts/examples.md) for complete, runnable synthesis examples using both voices.

## Custom voices

Nith TTS supports creating a **custom voice** from a short reference recording of the
target speaker, producing a custom voice package you load exactly like a built-in voice.

> **Note**
>
> To create a custom voice, contact
> [support@appliedbrainresearch.com](mailto:support@appliedbrainresearch.com)
> or see the [ABR developer portal](https://dev.appliedbrainresearch.com).

<!-- -->

> **Next steps**
>
> - [Examples](../tts/examples.md): full examples showing how to synthesize with each voice.
> - [Overview](../tts/overview.md): the TTS streaming model and output format.
