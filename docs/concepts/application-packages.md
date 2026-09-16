# Application packages

An application package is the `.tar.gz` archive you download from the
[ABR developer portal](https://dev.appliedbrainresearch.com) for your target device. It contains
everything the SDK needs to run inference: the compiled neural network library, the model weights,
and supporting configuration files. You extract it once onto the device and point the SDK at it when
creating an `abr_sdk.asr.Asr` or `abr_sdk.tts.Tts` instance.

## Package contents

Every application package contains three things:

- **A compiled shared library** (`.so`). The hardware-specific inference backend is already compiled
  into this library.
- **Neural network weight files.** Binary data encoding the trained model parameters.
- **Supporting configuration files.** Metadata the library reads during initialization.

The library, weights, and configuration files are a unit. After you extract the package, keep all of
them in the same directory. The shared library expects to find the weight files beside it; moving
the library file out of the directory will break initialization.

## Platform specificity

Each package targets a specific combination of capability, language, model variant, and hardware
platform. For example, `niagara-38m-live.en-linux-x86_64.tar.gz` is an English-language ASR package
for Linux on x86-64.

Available targets are Linux x86-64, Linux ARM64, and Android ARM64. The package you download
determines which inference backend runs on your device. You do not configure or select backends in
code.

## Extracting a package

Extract the package into a directory on the device where the SDK will run:

```bash
mkdir -p ~/abr-packages
tar xzf niagara-38m-live.en-linux-x86_64.tar.gz -C ~/abr-packages
```

The resulting directory contains the shared library and all supporting files. Do not move the shared
library out of this directory after extraction.

For the full download-and-extract walkthrough, see
[Installation](../getting-started/installation.md).

## Pointing the SDK at the package

Pass the path to the shared library as the first argument when you create an
`abr_sdk.asr.Asr` or `abr_sdk.tts.Tts` instance:

```python
from abr_sdk.asr import Asr

LIBRARY_PATH = "/home/user/abr-packages/niagara-38m-live.en-linux-x86_64/libniagara_38m_live.so"

with Asr(LIBRARY_PATH) as asr:
    ...
```

```python
from abr_sdk.tts import Tts

# female voice
LIBRARY_PATH = "/home/user/abr-packages/nith-5m-live.en-f1-linux-x86_64/libnith_5m_live.so"

with Tts(LIBRARY_PATH) as tts:
    ...
```

An absolute path is the most predictable option. When you pass a relative path, the SDK searches for
it in this order:

1. Any directories you pass in `lib_search_paths`.
2. The current working directory.
3. Directories listed in `LD_LIBRARY_PATH`.

To skip the environment-variable directories and rely only on paths you supply, set
`use_default_lib_search_paths=False`:

```python
with Asr(
    "libniagara_38m_live.so",
    lib_search_paths=["/home/user/abr-packages/niagara-38m-live.en-linux-x86_64"],
    use_default_lib_search_paths=False,
) as asr:
    ...
```

The same `lib_search_paths` and `use_default_lib_search_paths` options apply to
`abr_sdk.tts.Tts`.

## Weights directory

The SDK locates the weight files using the directory that contains the shared library. This default
works when a package is extracted in its original layout. If you store the weights in a separate
directory, pass its path with `resources_dir`:

```python
with Asr(
    "/path/to/libniagara_38m_live.so",
    resources_dir="/path/to/weights",
) as asr:
    ...
```

```python
with Tts(
    "/path/to/libnith_5m_live.so",
    resources_dir="/path/to/weights",
) as tts:
    ...
```

> **Next steps**
>
> - [Streaming and chunks](../concepts/streaming-and-chunks.md): how Buffers, Events, and EventSets
>   work underneath the
>   high-level API.
> - [SDK lifecycle](../concepts/sdk-lifecycle.md): how object lifetimes work and when to call
>   `close()`.
> - `abr_sdk.asr.Asr`: full constructor parameter list.
> - `abr_sdk.tts.Tts`: full constructor parameter list.
