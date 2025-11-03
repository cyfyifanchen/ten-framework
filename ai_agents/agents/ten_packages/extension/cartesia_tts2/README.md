# cartesia_tts2

TEN async TTS extension that streams audio from Cartesia’s Sonic family over
WebSockets. The default configuration now targets the latest `sonic-3`
snapshot, giving you expressive, multilingual synthesis with low latency.

## Features

- Sonic 3 streaming with automatic snapshot routing or explicit snapshot ids.
- Fine-grained `generation_config` passthrough (speed & volume) plus SSML
  emotion tags for tone control.
- Optional raw PCM dumping for debugging and latency (TTFB) telemetry.

## Configuration

1. Provide a Cartesia API key through `CARTESIA_API_KEY` or override
   `params.api_key` in the extension property.
2. Adjust the TTS profile in [property.json](property.json):
   - `model_id`: defaults to `sonic-3` (update to a dated snapshot for prod).
   - `voice`: select a Cartesia voice id or name that fits your character.
   - `generation_config.speed` (default `1.0`) and `.volume` (default `1.0`)
     control pacing and loudness per request.
   - `output_format.sample_rate`: choose one of Cartesia’s supported PCM
     sample rates (e.g. `44100`, `24000`, `16000`).
   - `language`: specify the ISO language code; Sonic 3 covers 42 languages
     across English, European, and Asian locales.
3. Attach the extension to your TEN agent via the manifest or TEN Studio and
   ensure the downstream audio sink matches the selected sample rate.

Any additional fields accepted by Cartesia’s `tts.websocket` endpoint can be
added under `params`; they are forwarded untouched.

## Development

### Build & install

The extension depends on the `cartesia` Python SDK. Install requirements with:

```bash
python3 -m pip install -r requirements.txt
```

### Unit test

Run the mocked regression suite (no network calls) with:

```bash
task test-extension EXTENSION=agents/ten_packages/extension/cartesia_tts2
```

## Misc

- Egress PCM dumps are written to `dump_path` when `dump=true`; remember to
  disable this in production workloads.
- For more Sonic 3 details, see Cartesia’s documentation:
  https://docs.cartesia.ai/build-with-cartesia/tts-models/latest
