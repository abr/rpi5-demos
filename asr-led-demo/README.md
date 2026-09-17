# Voice-controlled LEDs: ABR ASR → GPIO

The microphone is always listening, so there is no start or stop button.
Speech recognition runs continuously on ABR's library, on the device.

    1. LISTEN     microphone, continuously                    (sounddevice)
    2. TRANSCRIBE speech → text, streaming                    (ABR niagara ASR)
    3. ACT        colour + action words heard → drive an LED  (gpiozero)

Say the colour before the action, e.g. "red on", "blue blink", or "all
lights off", and the LEDs react as you speak.

## Files

`led_demo.py` holds everything: the listening loop plus the reusable pieces for
continuous audio capture, streaming ASR, the voice-command reactor, and LED
control.

The ABR ASR library is not part of this repository. Get it from ABR and
unpack it so the layout is:

    niagara-38m-live.en-<arch>/          ABR niagara ASR library + model blobs

Use the build matching your CPU (`linux-arm64` on a Raspberry Pi 5).
`led_demo.py` expects the `linux-arm64` directory name and the default
location is `~/abr-packages`.

## Hardware

Wire one LED per colour (with a current-limiting resistor, e.g. ~330 Ω) from
a GPIO pin to ground. The default pin assignment (BCM numbering) is:

| Colour | GPIO pin |
| ------ | -------- |
| red    | 17       |
| green  | 27       |
| blue   | 22       |

Edit `LED_PINS` at the top of `led_demo.py` to match your wiring, or to add
more colours. Each key is both the GPIO pin to drive and a word the voice
reactor listens for.

## Setup

Do the shared setup first: uv, the ABR application packages, and license
activation are all in the [top-level README](../README.md). Two things to check
on top of it.

**`swig`** must be installed so `uv` can compile `lgpio` from source. That is
gpiozero's GPIO backend on a Pi 5, and it has no prebuilt wheel. The shared
setup installs it; if you skipped that step, do it before the first run.

**The package path**, if you did not unpack into `~/abr-packages`. Edit
`ABR_PACKAGES_ROOT` at the top of `led_demo.py`; `ASR_LIB` below it follows.

The first run is slow because `uv` builds the environment from the inline
dependencies in the script. Later runs reuse it.

The [Raspberry Pi notes](../docs/raspberry-pi.md) cover audio and GPIO problems
specific to a Pi 5.

## Run

    ./led_demo.py                    # start listening, Ctrl+C to quit
    ./led_demo.py --list-devices     # list audio devices
    ./led_demo.py --input-device 7   # pick a microphone

(or `uv run led_demo.py ...` if the file isn't executable on your system)

The script starts listening immediately, without waiting for a key press.
Speak a command and the LEDs react as soon as each word is confirmed. That
is usually the instant the next word starts, or after a brief pause for the
last word of a command. The running transcript prints live to the terminal,
so you can see what the ASR hears as it happens. Say "reset" or "clear" to
bail out of a command you said by mistake without stopping the program.
Press Ctrl+C, or say "quit" or "exit", to stop.

## Command grammar

There are no discrete recordings in a continuous stream, so commands are
recognized from a trailing window of the last few words as they arrive:

| Action words                     | Effect                     |
| -------------------------------- | -------------------------- |
| on, activate, enable             | LED turns on steady        |
| off, deactivate, disable, stop   | LED turns off              |
| blink, blinking, flash, flashing | LED blinks at a fixed rate |

Say the colour name (or "all"/"everything"/"every"/"light"/"lights"/"leds"
for every LED) _before_ the action word, e.g. "red on" rather than "turn
on red". An action word heard with no colour or "all"-type word named yet
doesn't fire. It keeps listening rather than guessing you meant every LED.
The exact word lists are the `ON_WORDS`, `OFF_WORDS`, `BLINK_WORDS`, and
`ALL_WORDS` sets near the top of `led_demo.py`, in case they have been tuned
since this was written.
