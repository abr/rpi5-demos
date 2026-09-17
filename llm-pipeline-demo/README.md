# Voice chat: ABR ASR → Gemini → ABR TTS

A spoken conversation loop. Speech recognition and speech synthesis run on the
device using ABR's libraries. Gemini generates the reply in the cloud.

    1. LISTEN     microphone                 (sounddevice)
    2. TRANSCRIBE speech → text              (ABR niagara ASR, streaming)
    3. THINK      text → reply               (Gemini, cloud API)
    4. SPEAK      reply → speakers           (ABR nith TTS, streamed)

Your speech is streamed into the ASR while you talk, and Gemini's reply is
streamed back and synthesized one sentence at a time, so audio starts before the
full reply has arrived.

## Files

`llm_demo.py` holds everything: the interactive pipeline plus the reusable
pieces for audio input and output, streaming ASR, the Gemini client, and
streaming TTS.

The ABR ASR and TTS libraries are not part of this repository. Get them from ABR
and unpack them so the layout is:

    niagara-38m-live.en-<arch>/          ABR niagara ASR library + model blobs
    nith-5m-live.en-f1-<arch>/           ABR nith TTS, f1 voice (female, default)
    nith-5m-live.en-m1-<arch>/           ABR nith TTS, m1 voice (male, --tts m1)

Use the build matching your CPU (`linux-arm64` on a Raspberry Pi 5).
`llm_demo.py` expects the `linux-arm64` directory names, read from
`~/abr-packages`. Point it elsewhere by editing `ABR_PACKAGES_ROOT` at the top
of the file; `ASR_LIB` and `TTS_LIBS` are derived from it.

## Setup

Do the shared setup first: uv, the system libraries, the ABR application
packages, and license activation are all in the
[top-level README](../README.md). Activation covers the whole device, so the TTS
packages need nothing beyond unpacking them. This demo needs two things on top
of that.

**The package path**, if you did not unpack into `~/abr-packages`. Edit
`ABR_PACKAGES_ROOT` at the top of `llm_demo.py`; `ASR_LIB` and `TTS_LIBS` below
it follow.

**A Gemini API key**, free from Google AI Studio:

1. Go to <https://aistudio.google.com/apikey> and sign in with a Google account.
2. Click **Create API key**, then copy it.
3. Put it in the environment:

       export GEMINI_API_KEY=...      # or GOOGLE_API_KEY

   Add that to your `~/.bashrc` to keep it across sessions. The free tier is
   rate-limited to a handful of requests per minute; enable billing on the
   project for more. Keep the key secret and don't commit it.

Playback goes through `aplay` over ALSA. A Pi 5 has no 3.5 mm jack, so set the
output to HDMI, USB, or Bluetooth with `raspi-config` or `alsamixer`. The
[Raspberry Pi notes](../docs/raspberry-pi.md) cover the rest.

## Run

    ./llm_demo.py                       # start chatting
    ./llm_demo.py --list-devices        # list audio devices
    ./llm_demo.py --input-device 7      # pick a microphone
    ./llm_demo.py --output-device 3     # pick a plughw speaker
    ./llm_demo.py --model gemini-3.6-flash-lite
    ./llm_demo.py --tts m1              # male voice (default: f1, female)

(or `uv run llm_demo.py ...` if the file isn't executable on your system)

Press Enter to start recording, speak, Enter again to stop; `q` then Enter quits.
