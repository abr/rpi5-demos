# Frequently asked questions

## What is the ABR SDK?

The ABR SDK, from Applied Brain Research (ABR), is an on-device AI engine for streaming
automatic speech recognition (ASR) and text-to-speech (TTS), exposed through a Python
API for real-time transcription and synthesis.

## What are Niagara and Nith?

Niagara is ABR's ASR model, which turns voice audio into text. Nith is ABR's TTS model,
which turns text into speech. They are the two models the ABR SDK exposes.

## What is a state-space model, and why does ABR use one instead of a transformer?

ABR's models are state-space models (SSMs), built on the Legendre Memory Unit (LMU).
Unlike transformers, SSMs derive from continuous-time representations and need far less
computation, so they stay small while remaining competitive on accuracy, which makes
them practical on hardware with limited compute and memory.

## How is on-device speech recognition different from cloud speech APIs?

A cloud speech API sends your audio to a remote server for processing; the ABR SDK
processes it locally on the device. As a result, the ABR SDK needs no connectivity for
inference, adds no network latency, and keeps audio and transcripts on the device. A
cloud API, by contrast, requires an internet connection and a network round-trip for
every request.

## Does the ABR SDK work offline? Does it need an internet connection?

Yes, it works offline. Speech recognition and synthesis run locally and need no
connection. The one exception is **license activation**, which contacts ABR's licensing
service once per device to bind your key (see [License
activation](getting-started/license-activation.md));
after that the ABR SDK runs fully offline. If your own application calls a cloud
service, for example a hosted language model, that part needs connectivity, but the SDK
itself does not.

## Does the ABR SDK run in the cloud, and does it need a GPU?

No to both. Processing runs on the device's CPU, with no GPU or dedicated accelerator
required, because state-space models need far less computation than transformers of
similar size.

## Is my audio private? What data leaves the device?

Your audio is private: nothing leaves the device during speech processing, and audio and
transcripts stay local. The ABR SDK's only outbound network call is to the licensing
service during activation.

## Can the ABR SDK run in real time and stream audio?

Yes. You push audio (ASR) or text (TTS) in pieces as it arrives and receive results
through a callback before the input is complete, making it suitable for live microphone
input, network audio streams, and real-time synthesis.

## What's the latency? How fast are ASR and TTS?

- **ASR:** In FAST mode, Niagara emits text almost as soon as the audio arrives;
  ACCURATE mode waits for a little more audio as context, trading latency for accuracy.
  [Transcription stages](asr/transcription-stages.md) has the latency figures.
- **TTS:** Nith streams audio as it synthesizes, sentence by sentence, so the first
  audio plays before the full text has been consumed. Pushing text at sentence
  boundaries minimizes time to first audio. See [Examples](tts/examples.md).

## Does ASR add punctuation and capitalization?

Yes, by default. A post-processing stage adds punctuation, capitalization, and spell
correction to the transcript in both FAST and ACCURATE modes; the `enable_punctuation`
and `enable_spellcheck` arguments to `abr_sdk.asr.Asr` turn each off. Some
language packages ship models that emit punctuation directly rather than in
post-processing. See [Transcription stages](asr/transcription-stages.md).

## What audio format do ASR and TTS use?

Raw PCM: signed 16-bit little-endian, mono, 16 kHz, with no container headers. ASR
consumes this format and TTS produces it. The ABR SDK does not resample, so convert your
audio first; see [Input format](asr/input-format.md).

## Do I need to select a hardware backend or compile for my device?

No. Each application package already contains the compiled inference code for the
platform you chose; the ABR SDK loads it directly from the extracted directory. See
[Application packages](concepts/application-packages.md).

## Can I use the ABR SDK with a language model or voice assistant?

Yes. This is a common pattern: feed FAST ASR output straight into a language model, then
stream the model's reply to Nith TTS to speak it. Running speech on-device around an LLM
improves the loop on three fronts:

- **Reliability:** language models absorb minor transcription differences, so
  low-latency FAST output can be forwarded as soon as it is produced, without waiting
  for corrections.
- **Latency:** recognition and synthesis add no network round-trip and both stream:
  the LLM can start generating before the user stops speaking, and the reply is spoken
  before the LLM finishes.
- **Cost:** speech runs locally, so there are no per-request cloud speech-to-text or
  text-to-speech charges in the loop.

See [Transcription stages](asr/transcription-stages.md) and [Examples](tts/examples.md).

## Which platforms and operating systems are supported?

Linux (x86-64 and arm64) and Android (arm64). See [Installation](getting-started/installation.md)
for setup.

## Which spoken languages are supported?

English, Spanish, Chinese (Mandarin), Japanese, and Korean, with more languages in
development.

## What programming languages and bindings can I use the ABR SDK from?

The ABR SDK documented here is a Python package (Python 3.10 or later), installed with
`pip` or `uv` (see [Installation](getting-started/installation.md)). C and Java SDKs are coming
soon.

## Can I add custom vocabulary or custom voices?

Nith TTS supports a custom pronunciation dictionary today, and custom voices from a
short reference recording (see [Voices](tts/voices.md)). Custom vocabulary for Niagara ASR is
coming soon.
