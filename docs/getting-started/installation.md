# Installation

The ABR SDK is delivered in two parts: the **Python package**, which is the programming interface
you
install with pip, and an **application package**, which contains the neural network and compiled
inference backend for your target device. You need both to run the SDK.

## Prerequisites

Python 3.10 or later is required.

## Install the SDK

```bash
pip install abr-sdk
```

If your project uses `uv`:

```bash
uv add abr-sdk
```

## Get an application package

The neural network and the compiled inference backend are delivered in an **application package**, a
`.tar.gz` archive you download from the
[ABR developer portal](https://dev.appliedbrainresearch.com) after logging in.

Each package is built for a specific combination of functionality (ASR or TTS), language, model
variant, and hardware platform. Packaging them separately keeps the Python install small and lets
you
choose the package that fits your device.

A package filename encodes those dimensions. For example, `niagara-38m-live.en-linux-x86_64.tar.gz`
is an English ASR package for x86-64 Linux. Download the package that matches your target device and
use case. See [Package naming](../concepts/naming.md) for how to read each segment of a package
name.

## Extract the package

Extract the package into a directory on the device that will run the SDK:

```bash
mkdir -p ~/abr-packages
tar xzf niagara-38m-live.en-linux-x86_64.tar.gz -C ~/abr-packages
```

The extracted directory contains a shared library, neural network weight files, and supporting
configuration. Keep all of these files together in the same directory, the SDK loads the library and
weights as a unit at runtime. Moving the shared library file out of the directory will break
loading.

## Verify

Confirm the Python package installed correctly:

```python
import abr_sdk
print(abr_sdk.__version__)
```

You should see the SDK version number. This checks only the Python package; it does not load the
application package.

> **Next steps**
>
> [License activation](../getting-started/license-activation.md): activate this device so the SDK
> can load your package,
> then [ASR quickstart](../getting-started/asr-quickstart.md) to produce your first transcript.
