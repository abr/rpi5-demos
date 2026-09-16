# Package naming

Every application package name encodes the dimensions that make it specific: which model
it contains, how large it is, which variant, the language, the target platform, and (for
TTS) the voice. Reading the name tells you whether a package fits your use case and device
before you download it.

## Anatomy of a package name

An ASR package:

```text
niagara-38m-live.en-linux-x86_64
   │      │    │  │  │
   │      │    │  │  └── platform: Linux, x86-64
   │      │    │  └───── language: English
   │      │    └──────── variant: live (streaming, low-latency)
   │      └───────────── size: ~38 million parameters
   └──────────────────── model family: Niagara (ASR)
```

A TTS package additionally carries a voice:

```text
nith-5m-live.en-m1-linux-x86_64
  │   │    │ │  │  │
  │   │    │ │  │  └── platform: Linux, x86-64
  │   │    │ │  └───── voice: m1 (male, voice 1)
  │   │    │ └──────── language: English
  │   │    └────────── variant: live (streaming, low-latency)
  │   └─────────────── size: ~5 million parameters
  └─────────────────── model family: Nith (TTS)
```

## Fields

| Field    | Meaning                             | Example values                                 |
| -------- | ----------------------------------- | ---------------------------------------------- |
| Family   | The model, which implies ASR or TTS | `niagara` (ASR), `nith` (TTS)                  |
| Size     | Approximate parameter count         | `38m` (~38M), `5m` (~5M)                       |
| Variant  | Model line                          | `live` (streaming, low-latency)                |
| Language | Spoken language                     | `en` (English), `es` (Spanish)                 |
| Platform | Operating system and architecture   | `linux-x86_64`, `linux-arm64`, `android-arm64` |
| Voice    | TTS only: gender and voice number   | `f1` (female), `m1` (male)                     |

## Shared library name

The shared library inside a package mirrors the family, size, and variant, so
`niagara-38m-live` ships `libniagara_38m_live.so` and `nith-5m-live` ships
`libnith_5m_live.so`. You pass the path to this `.so` when constructing an
`abr_sdk.asr.Asr` or `abr_sdk.tts.Tts` object.

> **Next steps**
>
> - [Application packages](../concepts/application-packages.md): what a package contains and how to
>   extract it.
> - [Voices](../tts/voices.md): the available TTS voices and how to select one.
