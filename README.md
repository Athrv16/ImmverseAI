# Synthetic Manuscript Generator

Python pipeline that generates folio images and paired Markdown transcriptions for Devanagari, Modi, and Sharada. By default it creates 100 image/annotation pairs per script and splits each script into 85 train, 10 validation, and 5 test examples.

## Run on a Mac

Open this folder in VS Code. In its Terminal, run the one-time setup:

```sh
chmod +x setup_macos.sh
./setup_macos.sh
```

The setup script installs Homebrew text-shaping libraries, creates `.venv`, builds Pillow with HarfBuzz/RAQM support, and checks that Indic shaping is available. Activate the environment whenever you reopen VS Code:

```sh
source .venv/bin/activate
```

Generate the default dataset:

```sh
python generate.py
```

This writes 300 PNG images and 300 paired `.md` annotations to `output/`. Use `--count 20` for a small preview, `--seed 123` for a repeatable variation, or `--width` and `--height` to adjust page size. You can replace the bundled passages and fonts with `--text SCRIPT=PATH` and `--font SCRIPT=PATH` (repeat for all desired scripts).

Check the generated file counts and image/annotation pairing with:

```sh
python validate.py
```

## Dataset layout

```text
output/
  devanagari/{train,validation,test}/...png and ...md
  modi/{train,validation,test}/...png and ...md
  sharada/{train,validation,test}/...png and ...md
```

The `.md` file stores the exact Unicode main passage and any repeated marginal word rendered in its paired image. The bundled source passage is the Marathi Devanagari sample from the assignment. Modi and Sharada text are Unicode script conversions of that same passage. Each script therefore has limited linguistic variety; the 100 images per script reuse one passage with different image treatments. Replace the files under `data/text/` with reviewed, varied text before treating this as a substantial OCR corpus.

## Font and visual limitations

The defaults use Kalam (handwriting-style Devanagari), MarathiCursive (Unicode Modi), and Noto Sans Sharada. These fonts improve the script-specific look, but they do not reproduce the range of real manuscript handwriting. An experimental Satisar Sharada font is included as an optional alternative. The generator varies materials, stains, folds, text position, slant, ink tone, and highlighted passages. This procedural baseline does not establish 90% visual parity with real folios. For that target, use reviewed historical-script handwriting fonts or reference scans and validate the generated images with a domain expert. Font sources and licenses are listed under `assets/fonts/`.

## Optional Hugging Face upload

Install the optional libraries and log in locally with a Hugging Face write token:

```sh
python -m pip install -r requirements-hub.txt
hf auth login
```

Then create a dataset repository and upload all three configurations:

```sh
python generate.py --upload --repo-id YOUR_USERNAME/synthetic-manuscripts
```

The upload creates a private repository with configurations named `devanagari`, `modi`, and `sharada`; each configuration contains `train`, `validation`, and `test` splits. Grant the hiring team access through Hugging Face. Never put the token in the code or repository.

## Files

- `generate.py` — folio generation, paired annotations, and optional Hub upload.
- `setup_macos.sh` — Mac setup with Indic shaping support.
- `requirements.txt` — Python runtime packages.
- `requirements-hub.txt` — optional Hub upload packages.
- `validate.py` — checks file counts, pairings, image decoding, dimensions, and source-text alignment.
- `assets/fonts/` — Unicode fonts and their licenses.
- `data/text/` — bundled Unicode passages.
