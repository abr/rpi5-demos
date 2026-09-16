# ABR SDK Introduction

The ABR SDK is an on-device AI engine that enables streaming automatic speech recognition (ASR) and
text-to-speech (TTS). It is:

- **Fully streaming**, delivering the lowest latency while achieving maximum accuracy
- **Computationally efficient**, with a small memory footprint
- **Supported on multiple OS and hardware platforms:**
  - Linux (x86-64, arm64)
  - Android (arm64)
- **Available in multiple languages**, including English, Spanish, Chinese (Mandarin), Japanese,
  Korean, and more

## Getting set up

You need an ABR Developer account and an SDK access token to access and operate the SDK on your
device. You can start your journey as an ABR developer on the
[ABR developer portal](https://dev.appliedbrainresearch.com).

To install and run the SDK, you need Python 3.10 or later and a package installer
like `pip` or `uv`. See [Installation](getting-started/installation.md) for full setup instructions.

## SDK models and features

The SDK gives you the following on-device speech AI capabilities:

- **Niagara ASR**: transcribe streaming voice audio to text in real time
  - Punctuation and capitalization
  - Custom vocabulary support coming soon
- **Nith TTS**: synthesize natural-sounding speech from a text stream
  - Custom vocabulary pronunciation dictionary
  - Normalizes text to correctly pronounce dates, temperatures, currencies, and more

Both run entirely on your device. No audio or transcript data is sent to an external service during
processing.

## SDK model technology

ABR's speech AI models are built on state-space models (SSMs), a technology we invented with the
Legendre Memory Unit (LMU), which we introduced in 2019. Unlike transformer models, SSMs are derived
from continuous-time representations and require significantly less computation. Our selective use
of
attention layers lets our SSMs achieve much higher performance than transformers of similar size, so
ABR's models deliver competitive performance while remaining much smaller. These models also deliver
true streaming performance, with no look-ahead or batch accumulation before producing output.

These properties make SSM-based models practical and ideal on devices with limited compute and
memory. You do not need to understand SSMs to use the SDK, but if you want to learn more you can
[read about it
here](https://www.appliedbrainresearch.com/why-state-space-models-are-the-future-of-edge-ai).
The distinction matters if you are evaluating whether ABR's models fit your device's hardware
budget.

## SDK architecture

The SDK is a thin API layer over a stable C application binary interface (ABI). Neural network
execution and platform-specific optimizations happen inside a compiled library you download
separately, called an [application package](concepts/application-packages.md).

Once you extract the package to a directory on your device, the SDK loads the library and weights
directly from that directory path when you create an [Asr](asr/overview.md) or
[Tts](tts/overview.md)
object. There is no need to select a hardware backend or configure execution targets; the
application
package already contains the correct code for the platform you selected.

## Who this documentation is for

This documentation assumes you are a developer integrating speech AI into a device or application,
and
that you have the requisite Python skills to integrate this SDK.

## Contents

### Getting Started

- [Installation](getting-started/installation.md)
- [License activation](getting-started/license-activation.md)
- [ASR quickstart](getting-started/asr-quickstart.md)
- [TTS quickstart](getting-started/tts-quickstart.md)

### Core Concepts

- [Application packages](concepts/application-packages.md)
- [Package naming](concepts/naming.md)
- [Streaming and chunks](concepts/streaming-and-chunks.md)
- [SDK lifecycle](concepts/sdk-lifecycle.md)

### Automatic Speech Recognition

- [Overview](asr/overview.md)
- [Transcription stages](asr/transcription-stages.md)
- [Input format](asr/input-format.md)
- [Benchmarking](asr/benchmarking.md)
- [Examples](asr/examples.md)

### Text-to-Speech

- [Overview](tts/overview.md)
- [Input format](tts/input-format.md)
- [Voices](tts/voices.md)
- [Examples](tts/examples.md)

### API Reference

- [Python API reference](api/reference.md)

### Help

- [Frequently asked questions](faq.md)

### Hackathon notes

- [Running on a Raspberry Pi 5](raspberry-pi.md)
