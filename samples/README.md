# Sample audio

Two short clips in the exact format the ASR expects: 16 kHz, mono, signed
16-bit little-endian PCM in a WAV container. Use them to check that the ASR
works before you fight with microphone configuration.

| File                   | Language | Length | Spoken text                                                                              |
| ---------------------- | -------- | ------ | ---------------------------------------------------------------------------------------- |
| `synth-en-weather.wav` | English  | 4.6 s  | "The weather right now is sunny and warm. We expect it will be cloudy in the afternoon." |
| `synth-es-weather.wav` | Spanish  | 5.5 s  | "La mañana está fresca y tranquila. Después de comer iremos a la playa con los niños."   |

Both were synthesized with ABR's own TTS, so there is no third-party recording
or speaker to worry about.

## Transcribing one

```bash
python - <<'PY'
import wave
from abr_sdk.asr import Asr

with wave.open("samples/synth-en-weather.wav", "rb") as wav:
    pcm = wav.readframes(wav.getnframes())

with Asr("/path/to/libniagara_38m_live.so") as asr:
    print(asr.process(pcm).text)
PY
```

The English clip should come back close to the text in the table. An exact match
is not guaranteed; punctuation and casing come from a separate pass, and the
model may differ slightly from the one used to build these files.

Note that `wave.readframes` hands you the whole clip at once, which is the
blocking API. The demos stream instead, pushing about 100 ms at a time. See
[Streaming and chunks](../docs/concepts/streaming-and-chunks.md).
