# Voice-controlled LEDs: ABR ASR → GPIO

The mic is always listening — there's no start/stop button. Speech
recognition runs continuously and entirely locally on ABR's library; there
is no cloud step.

    1. LISTEN     microphone, continuously                    (sounddevice)
    2. TRANSCRIBE speech → text, streaming                    (ABR niagara ASR)
    3. ACT        colour + action words heard → drive an LED  (gpiozero)

Say the colour before the action, e.g. "red on", "blue blink", or "all
lights off", and the LEDs react as you speak.

## Files

| File | Purpose |
| --- | --- |
| `led_demo.py` | The listening loop + all the reusable pieces (continuous audio capture, streaming ASR, voice-command reactor, LED control). |

The ABR ASR library is **not part of this repo** — obtain it from ABR and
unpack it here so the layout is:

    niagara-38m-live.en-<arch>/          ABR niagara ASR library + model blobs

Use the build matching your CPU (`linux-arm64` on a Raspberry Pi 5).
`led_demo.py` expects the `linux-arm64` directory name and the default
location is `~/abr-packages`; point it at another path by editing `ASR_LIB`
at the top of the file.

## Hardware

Wire one LED per colour (with a current-limiting resistor, e.g. ~330 Ω) from
a GPIO pin to ground. The default pin assignment (BCM numbering) is:

| Colour | GPIO pin |
| --- | --- |
| red | 17 |
| green | 27 |
| blue | 22 |

Edit `LED_PINS` at the top of `led_demo.py` to match your wiring, or to add
more colours — each key becomes both the GPIO pin to drive and a word the
voice reactor listens for.

## Setup

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** (once, if you don't have it):

       curl -LsSf https://astral.sh/uv/install.sh | sh

   `led_demo.py` declares its Python dependencies inline (PEP 723); `uv` reads
   them straight from the script and builds an ephemeral environment on first
   run, so there's no separate install step.

2. **Install the system packages the dependencies need**:

       sudo apt update
       sudo apt install -y libportaudio2 swig

   `libportaudio2` backs `sounddevice`; `swig` is needed for `uv` to
   compile `lgpio`'s native extension from source (`lgpio` is gpiozero's
   GPIO backend on a Pi 5).

3. **Activate the ABR library** once (needs a license key + network; ASR
   runs offline afterwards):

       abr-sdk activate niagara-38m-live.en-linux-arm64/libniagara_38m_live.so   --key-file abr_license.key

4. Update `ASR_LIB` in `led_demo.py` to the arm64 directory name.

## Run

    ./led_demo.py                    # start listening, Ctrl+C to quit
    ./led_demo.py --list-devices     # list audio devices
    ./led_demo.py --input-device 7   # pick a microphone

(or `uv run led_demo.py ...` if the file isn't executable on your system)

The script starts listening immediately — no key press needed. Speak a
command and the LEDs react as soon as each word is confirmed — usually the
instant the next word starts, or after a brief pause for the last word of
a command — the running transcript prints live to the terminal so you can
see what the ASR is hearing as it happens. Say "reset" or "clear" to bail
out of a command said by mistake without stopping the program. Press
Ctrl+C (or say "quit" or "exit") to stop at any time.

## Command grammar

There are no discrete recordings in a continuous stream, so commands are
recognized from a trailing window of the last few words as they arrive:

| Action words | Effect |
| --- | --- |
| on, activate, enable | LED turns on steady |
| off, deactivate, disable, stop | LED turns off |
| blink, blinking, flash, flashing | LED blinks at a fixed rate |

Say the colour name (or "all"/"everything"/"every"/"light"/"lights"/"leds"
for every LED) *before* the action word, e.g. "red on" rather than "turn
on red". An action word heard with no colour or "all"-type word named yet
doesn't fire — it keeps listening rather than guessing you meant every
LED. (The exact word lists are the `ON_WORDS`/`OFF_WORDS`/`BLINK_WORDS`/
`ALL_WORDS` sets near the top of `led_demo.py`, in case they've been
tuned since this was written.)
