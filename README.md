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

## Run on Windows

These steps are for Windows 10/11 with 64-bit Python and PowerShell in the VS Code terminal. Install Python 3.10 or newer and Git first, then open this folder in VS Code.

Pillow's Windows wheel needs the FriBiDi runtime library for the RAQM text layout engine used to shape Indic scripts. Install [MSYS2](https://www.msys2.org/), open **MSYS2 UCRT64** from the Start menu, and install FriBiDi:

```sh
pacman -S mingw-w64-ucrt-x86_64-fribidi
```

In the VS Code PowerShell terminal, add the MSYS2 UCRT64 binaries to this terminal's `PATH` (use the default MSYS2 install location shown below), then create and activate a virtual environment and install the project requirements:

```powershell
$env:PATH = "C:\msys64\ucrt64\bin;$env:PATH"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, allow it for this terminal session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Confirm that Pillow can use RAQM before generating images:

```powershell
python -c "from PIL import features; print('RAQM:', features.check('raqm'))"
```

The output must be `RAQM: True`. If MSYS2 was installed in a different folder, replace `C:\msys64\ucrt64\bin` with its `ucrt64\bin` path. Keep the MSYS2 path in the VS Code terminal's `PATH` whenever you run the generator. Then run:

```powershell
python generate.py
python validate.py
```

For a small preview, use `python generate.py --count 20 --seed 123`. The generator and output layout are the same as on Mac.

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

Use the standalone uploader to verify and upload the already-generated dataset:

```sh
python scripts/upload_to_huggingface.py --help
python scripts/upload_to_huggingface.py
```

After `hf auth login`, it uses the authenticated username to create or use the assignment's dataset repository. It verifies exactly 300 PNGs and 300 matching Markdown annotations, then uploads the `devanagari`, `modi`, and `sharada` configurations, each with `train`, `validation`, and `test` splits. It makes the repository public after all three configurations upload successfully. Generate the full dataset first with `python generate.py` if needed. Never put the token in the code or repository.

On Windows, run the same commands in the activated PowerShell virtual environment, using `python -m pip install -r requirements-hub.txt` and `hf auth login` before uploading.

## Files

- `generate.py` — folio generation, paired annotations, and optional Hub upload.
- `scripts/upload_to_huggingface.py` — verify and upload an existing generated dataset without regenerating it.
- `setup_macos.sh` — Mac setup with Indic shaping support.
- `requirements.txt` — Python runtime packages.
- `requirements-hub.txt` — optional Hub upload packages.
- `validate.py` — checks file counts, pairings, image decoding, dimensions, and source-text alignment.
- `assets/fonts/` — Unicode fonts and their licenses.
- `data/text/` — bundled Unicode passages.
