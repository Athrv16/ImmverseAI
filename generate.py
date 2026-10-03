#!/usr/bin/env python3
"""Generate synthetic manuscript folios and aligned Markdown transcriptions."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from fontTools.ttLib import TTFont

SAMPLE = """लक्षण। अपूर्व असे परियेसा ।८। ऋषि म्हणे रायासी। पुत्रभविष्य पुससी। ऐकोनि दुःख पावसी। कवणेपरी सांगावे ।९। राव विनवी तये वेळी। निरोपावे सकळी। उपाय करिसी तात्काळी। दुःखावेगळा तूचि करिसी ।१०। ऐकोनिया ऋषीश्वर। सांगता झाला विस्तार। ऐक राजा तुझा कुमार। बारा वर्षे आयुष्य असे ।११। तया बारा वर्षात। राहिले असती दिवस सात। आठवे दिवसी येईल मृत्यु। तुझ्या पुत्रासी परियेसा ।१२। ऐकोनि ऋषीचे वचन। राजा मूर्च्छित जाहला तत्क्षण। करिता"""
SCRIPTS = ("devanagari", "modi", "sharada")
ROOT = Path(__file__).resolve().parent
DEFAULT_FONTS = {
    "devanagari": ROOT / "assets/fonts/Kalam/Kalam-Regular.ttf",
    "modi": ROOT / "assets/fonts/MarathiCursive/MarathiCursiveT.ttf",
    "sharada": ROOT / "assets/fonts/NotoSansSharada/NotoSansSharada-Regular.ttf",
}
DEFAULT_TEXTS = {script: ROOT / "data/text" / f"{script}.txt" for script in SCRIPTS}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--count", type=int, default=100, help="folios per script (default: 100)")
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--height", type=int, default=800)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--text", action="append", default=[], metavar="SCRIPT=PATH",
                   help="UTF-8 source text for a script; repeat for each script")
    p.add_argument("--font", action="append", default=[], metavar="SCRIPT=PATH",
                   help="font file override; repeat for each script")
    p.add_argument("--upload", action="store_true", help="push three configs to HF (requires HF_TOKEN)")
    p.add_argument("--repo-id", help="Hugging Face dataset repo, e.g. username/manuscripts")
    return p.parse_args()


def load_lines(text_file: Path | None) -> list[str]:
    raw = text_file.read_text(encoding="utf-8") if text_file else SAMPLE
    lines = [" ".join(p.split()) for p in raw.splitlines() if p.strip()]
    if not lines:
        raise ValueError("Text input is empty")
    return lines


def paper_background(w: int, h: int, rng: random.Random, material: str) -> Image.Image:
    base = (rng.randint(190, 224), rng.randint(155, 195), rng.randint(105, 150))
    if material == "palm_leaf":
        base = (rng.randint(174, 207), rng.randint(151, 183), rng.randint(99, 130))
    noise = np.random.default_rng(rng.randrange(2**32)).normal(0, 8, (h, w, 1))
    arr = np.clip(np.array(base, dtype=np.float32)[None, None, :] + noise, 0, 255)
    # Broad, low-frequency stains and fine grain.
    small = Image.fromarray(np.uint8(rng.randrange(256) * np.ones((max(2, h // 24), max(2, w // 24)), dtype=np.uint8)))
    stains = np.asarray(small.resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16)), dtype=np.float32)
    arr += ((stains[:, :, None] - 127) * 0.12)
    im = Image.fromarray(np.uint8(np.clip(arr, 0, 255)), "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    # Edges and age spots
    for _ in range(rng.randrange(18, 45)):
        x, y = rng.randrange(w), rng.randrange(h)
        r = rng.randrange(2, max(3, min(w, h) // 45))
        d.ellipse((x-r, y-r, x+r, y+r), fill=(82, 48, 20, rng.randrange(5, 25)))
    if material == "palm_leaf":
        for y in range(rng.randrange(25, 60), h, rng.randrange(40, 75)):
            d.line((20, y, w-20, y+rng.randrange(-2, 3)), fill=(95, 63, 32, 28), width=1)
        if rng.random() < .65:
            x = rng.randrange(w // 4, 3*w // 4)
            d.ellipse((x-9, h//2-9, x+9, h//2+9), fill=(70, 43, 23, 135))
    else:
        # Subtle folded or curled edge shadows.
        if rng.random() < .45:
            x = rng.randrange(40, w-40)
            d.line((x, 0, x+rng.randrange(-18, 18), h), fill=(65, 43, 25, 24), width=rng.randrange(2, 6))
    return im


def render_folio(text: str, font_path: Path, w: int, h: int, seed: int) -> tuple[Image.Image, str | None]:
    rng = random.Random(seed)
    material = rng.choice(("paper", "palm_leaf"))
    im = paper_background(w, h, rng, material)
    draw = ImageDraw.Draw(im, "RGBA")
    margin_x = rng.randint(65, 115)
    margin_y = rng.randint(60, 95)
    font_size = rng.randint(27, 34)
    # Reserve a slim annotation column; wrap by measured glyph width.
    side = rng.random() < .45
    text_right = w - (margin_x + 85 if side else margin_x)
    line_width = text_right - margin_x - 40  # room for padding and the slight line rotation
    words = text.split()
    lines: list[str] = []
    # Shrink oversized input until every word and line fits the usable page area.
    while font_size >= 14:
        font = ImageFont.truetype(str(font_path), font_size, layout_engine=ImageFont.Layout.RAQM)
        candidate_lines: list[str] = []
        current = ""
        too_wide = False
        for word in words:
            if draw.textlength(word, font=font) > line_width:
                too_wide = True
                break
            candidate = f"{current} {word}".strip()
            if current and draw.textlength(candidate, font=font) > line_width:
                candidate_lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            candidate_lines.append(current)
        line_h = max(int(font_size * 1.75), font_size + 24)
        if not too_wide and len(candidate_lines) * (line_h + 4) <= h - 2 * margin_y:
            lines = candidate_lines
            break
        font_size -= 1
    if not lines:
        raise ValueError(f"Passage does not fit on a {w}x{h} folio: {text[:60]!r}")
    y = margin_y
    for idx, line in enumerate(lines):
        # Render each line to a layer to add mild slant/waviness without changing transcription.
        bbox = font.getbbox(line, stroke_width=0)
        lw = max(1, int(draw.textlength(line, font=font)) + 16)
        lh = max(font_size + 20, bbox[3] - bbox[1] + 20)
        layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ink = rng.choice(((48, 34, 27, 220), (61, 39, 30, 205), (80, 53, 40, 195)))
        ld.text((5, 5 - bbox[1]), line, font=font, fill=ink, stroke_width=0)
        if rng.random() < .55:
            layer = layer.rotate(rng.uniform(-1.4, 1.4), resample=Image.Resampling.BICUBIC, expand=True)
        x = margin_x + rng.randint(-3, 4)
        if idx == 0 and rng.random() < .7:
            # Pale mineral-pigment wash behind a short highlighted section.
            highlight_w = min(int(draw.textlength(line, font=font) * rng.uniform(.25, .5)), line_width)
            draw.rounded_rectangle((x-3, y+font_size//2, x+highlight_w, y+font_size+5),
                                   radius=3, fill=(218, 177, 83))
        im.alpha_composite(layer, (x, y)) if im.mode == "RGBA" else im.paste(layer, (x, y), layer)
        y += line_h + rng.randint(-3, 4)
    # Margin note repeats a short word from the source, so it can be recorded exactly.
    draw = ImageDraw.Draw(im, "RGBA")
    small_font = ImageFont.truetype(str(font_path), max(17, font_size - 10), layout_engine=ImageFont.Layout.RAQM)
    marginal_note = None
    if side:
        candidates = [word for word in words if draw.textlength(word, font=small_font) <= 66]
        if candidates:
            marginal_note = rng.choice(candidates)
            draw.text((w-margin_x-70, margin_y+20), marginal_note, font=small_font,
                      fill=(75, 45, 32, 190))
    if rng.random() < .6 and text:
        marker = next((char for char in reversed(text) if char in "।॥"), "")
        if marker:
            draw.text((margin_x, h-margin_y//2), marker, font=small_font, fill=(73, 45, 31, 185))
    # Mild blur and fine specks imitate worn ink/surface.
    if rng.random() < .35:
        im = im.filter(ImageFilter.GaussianBlur(radius=.25))
    return im.convert("RGB"), marginal_note


def validate_font_coverage(script: str, font_path: Path, passages: list[str]) -> None:
    cmap = TTFont(font_path, lazy=True).getBestCmap()
    missing = sorted({char for passage in passages for char in passage if not char.isspace() and ord(char) not in cmap})
    if missing:
        sample = " ".join(f"U+{ord(char):04X}" for char in missing[:8])
        raise SystemExit(f"{script} font {font_path.name} lacks {len(missing)} source glyph(s): {sample}")


def upload_script(repo_id: str, script: str, root: Path) -> None:
    try:
        from datasets import Dataset, DatasetDict, Features, Image as HFImage, Value
    except ImportError as exc:
        raise SystemExit("For --upload, install optional packages: pip install 'datasets>=3' huggingface_hub") from exc
    splits = {}
    first_index = 1
    for split, count in (("train", 85), ("validation", 10), ("test", 5)):
        rows = []
        for i in range(count):
            stem = f"{script}_{split}_{first_index+i:04d}"
            folder = root / script / split
            rows.append({"image": str(folder / f"{stem}.png"),
                         "text": (folder / f"{stem}.md").read_text(encoding="utf-8")})
        splits[split] = Dataset.from_list(rows, features=Features({"image": HFImage(), "text": Value("string")}))
        first_index += count
    DatasetDict(splits).push_to_hub(repo_id, config_name=script, private=True)


def main() -> None:
    args = parse_args()
    if args.count <= 0:
        raise SystemExit("--count must be positive")
    font_map = dict(DEFAULT_FONTS)
    for item in args.font:
        if "=" not in item:
            raise SystemExit("--font must be SCRIPT=PATH")
        key, value = item.split("=", 1)
        font_map[key.lower()] = Path(value).expanduser()
    missing = [s for s in SCRIPTS if not font_map[s].is_file()]
    if missing:
        raise SystemExit("Provide an existing handwritten font for each script with --font SCRIPT=PATH. Missing: " + ", ".join(missing))
    text_paths = dict(DEFAULT_TEXTS)
    for item in args.text:
        if "=" not in item:
            raise SystemExit("--text must be SCRIPT=PATH")
        key, value = item.split("=", 1)
        path = Path(value).expanduser()
        if not path.is_file():
            raise SystemExit(f"Text file not found: {path}")
        text_paths[key.lower()] = path
    missing = [script for script in SCRIPTS if not text_paths[script].is_file()]
    if missing:
        raise SystemExit("Missing text files for: " + ", ".join(missing))
    text_map = {script: load_lines(text_paths[script]) for script in SCRIPTS}
    rng = random.Random(args.seed)
    for script in SCRIPTS:
        for index in range(args.count):
            split = "train" if index < round(args.count * .85) else "validation" if index < round(args.count * .95) else "test"
            folder = args.output / script / split
            folder.mkdir(parents=True, exist_ok=True)
            script_text = text_map[script]
            text = script_text[index % len(script_text)]
            if index == 0:
                validate_font_coverage(script, font_map[script], script_text)
            name = f"{script}_{split}_{index+1:04d}"
            image, marginal_note = render_folio(text, font_map[script], args.width, args.height, rng.randrange(2**32))
            image.save(folder / f"{name}.png", optimize=True)
            annotation = f"# Main text\n\n{text}\n"
            if marginal_note:
                annotation += f"\n## Marginal note\n\n{marginal_note}\n"
            (folder / f"{name}.md").write_text(annotation, encoding="utf-8")
        print(f"Generated {args.count} {script} folios")
    if args.upload:
        if not args.repo_id:
            raise SystemExit("--repo-id is required with --upload")
        if args.count != 100:
            raise SystemExit("--upload expects the required 100 folios per script; omit --count or set --count 100")
        for script in SCRIPTS:
            upload_script(args.repo_id, script, args.output)
            print(f"Uploaded config {script} to {args.repo_id}")


if __name__ == "__main__":
    main()
