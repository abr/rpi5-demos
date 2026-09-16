# License activation

Application packages are licensed per device. Before the SDK can load a package's shared library,
you
must activate this device with the `abr-sdk activate` command. Activation binds your license key to
this machine and writes a signed license file that the SDK reads when it loads a package.

You only need to activate once per device.

## Get a license key

License keys are issued per account. To set up an account and receive a key, email
[support@appliedbrainresearch.com](mailto:support@appliedbrainresearch.com).

## Activate this device

Run `abr-sdk activate`, pointing it at the shared library (`.so`) from your extracted application
package and passing your license key:

```bash
abr-sdk activate /path/to/niagara-38m-live.en/libniagara_38m_live.so --key YOUR_LICENSE_KEY
```

To keep the key out of your shell history, write it to a file and use `--key-file` instead:

```bash
abr-sdk activate /path/to/niagara-38m-live.en/libniagara_38m_live.so --key-file ~/abr-license.key
```

On success the command prints where the license was installed:

```text
abr-sdk: activation succeeded; license installed in ~/.local/state/abr-sdk/license
```

## Options

| Option                 | Description                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| `library` (positional) | Path to the application package's shared library (`.so`). The device fingerprint is read from it. |
| `--key STRING`         | Your ABR license key. Mutually exclusive with `--key-file`; one of the two is required.           |
| `--key-file FILE`      | Path to a file containing the license key. Surrounding whitespace is trimmed.                     |
| `--license-dir DIR`    | Directory to write the license into. Defaults to `~/.local/state/abr-sdk/license`.                |

## Troubleshooting

If activation fails, `abr-sdk activate` will tell you why. The most common causes are:

- **Network errors**: the licensing service could not be reached. Check your connection and retry.
- **License errors**: the key is invalid, or already bound to too many different devices. Confirm
  the key and the `library` path, or contact
  [support@appliedbrainresearch.com](mailto:support@appliedbrainresearch.com).

> **Next steps**
>
> With your device activated, produce your first transcript in the [ASR
> quickstart](../getting-started/asr-quickstart.md)
> or synthesize speech in the [TTS quickstart](../getting-started/tts-quickstart.md).
