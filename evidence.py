"""Reproduce every number and figure used in the lab report.

The script runs the completed encoder stage by stage, compares each stage with
the supplied reference arrays (comparison only, never as an input), times the
forward pass and draws three figures. Run it from this directory:

    python evidence.py

Outputs: docs/results.csv, docs/figures/fig1_patches.png,
docs/figures/fig2_errors.png, docs/figures/fig3_similarity.png
"""
from pathlib import Path
import argparse
import csv
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from image_encoder import ImageEncoder
from preprocess_image import PreprocessImage
from runtime import ROOT, image_records, load_images, load_weights

# Stage name -> (comparison tolerance, human readable shape rule).
TOLERANCE = {
    'preprocess': 2e-6,
    'patches': 2e-4,
    'tokens': 2e-4,
    'block0': 2e-4,
    'last_tokens': 2e-4,
    'output': 2e-5,
    'batch': 2e-5,
}
RTOL = 2e-4
STAGES = tuple(TOLERANCE)


# --------------------------------------------------------------------------
# Numerical evaluation
# --------------------------------------------------------------------------
def compare(name, actual, expected):
    """Mirror check.py: shape, float32, finite and allclose, then report error."""
    assert actual.shape == expected.shape, f'{name}: shape mismatch'
    assert actual.dtype == np.float32, f'{name}: expected float32'
    assert np.isfinite(actual).all(), f'{name}: non-finite value'
    error = np.abs(actual - expected)
    ok = np.allclose(actual, expected, rtol=RTOL, atol=TOLERANCE[name])
    return ok, float(error.max()), float(error.mean())


def run_stages(encoder, images):
    """Return {stage: (ok, max_abs, mean_abs, shape, seconds)}."""
    results = {}
    with np.load(ROOT / 'assets/reference_outputs.npz', allow_pickle=False) as ref:
        inputs = {
            'preprocess': (images, ref['preprocessed']),
            'patches': (encoder.patchify(images[:2]), ref['patches'][:2]),
            'tokens': (encoder.embed(images[:2]), ref['input_tokens'][:2]),
            'block0': (encoder.blocks[0](encoder.pre_norm(encoder.embed(images[:2]))),
                       ref['block0_tokens'][:2]),
            'last_tokens': (encoder.encode_tokens(images[:2]), ref['last_tokens'][:2]),
        }
        order = [1, 0, 1]
        for stage in ('output', 'batch'):
            start = time.perf_counter()
            actual = encoder(images if stage == 'output' else images[order])
            seconds = time.perf_counter() - start
            expected = ref['output_tokens'] if stage == 'output' else ref['output_tokens'][order]
            ok, max_abs, mean_abs = compare(stage, actual, expected)
            results[stage] = (ok, max_abs, mean_abs, actual.shape, seconds)
        for stage, (actual, expected) in inputs.items():
            ok, max_abs, mean_abs = compare(stage, actual, expected)
            results[stage] = (ok, max_abs, mean_abs, actual.shape, 0.0)
    return results


def timing(encoder, images):
    """Time the three forward phases for the report's performance paragraph."""
    start = time.perf_counter()
    tensor = load_images()
    preprocess_seconds = time.perf_counter() - start

    start = time.perf_counter()
    tokens = encoder.embed(images)
    embed_seconds = time.perf_counter() - start

    start = time.perf_counter()
    encoded = encoder.encode_tokens(images)
    encode_seconds = time.perf_counter() - start

    start = time.perf_counter()
    encoder(images)
    forward_seconds = time.perf_counter() - start
    del tensor, tokens, encoded
    return preprocess_seconds, embed_seconds, encode_seconds, forward_seconds


# --------------------------------------------------------------------------
# Drawing helpers (Pillow only, no plotting dependency)
# --------------------------------------------------------------------------
FONT_CANDIDATES = (
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/System/Library/Fonts/Supplemental/Arial.ttf',
)


def font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def blue(t):
    """Blues-style colormap for the similarity matrix."""
    t = float(np.clip(t, 0.0, 1.0))
    low, high = np.array([247, 251, 255]), np.array([8, 48, 107])
    return tuple(int(round(v)) for v in low + (high - low) * t)


def draw_axes(draw, box, ymin, ymax, ticks):
    """Log-scale y axis with labels; box is (left, top, right, bottom)."""
    left, top, right, bottom = box
    draw.line([left, top, left, bottom], fill=(90, 90, 90), width=2)
    draw.line([left, bottom, right, bottom], fill=(90, 90, 90), width=2)
    lo, hi = np.log10(ymin), np.log10(ymax)
    for value in ticks:
        t = (np.log10(value) - lo) / (hi - lo)
        y = bottom - t * (bottom - top)
        draw.line([left, y, right, y], fill=(225, 225, 228), width=1)
        draw.line([left - 8, y, left, y], fill=(90, 90, 90), width=2)
        label = f'1e{int(round(np.log10(value)))}'
        draw.text((left - 12, y), label, font=font(20), fill=(60, 60, 60), anchor='rm')


def figure_patches(images, path):
    """(a) 7x7 patch grid with indices, (b) the 50-row token sequence."""
    canvas = Image.new('RGB', (1400, 660), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((60, 30), '(a) 224x224 image cut into 7x7 patches (32x32 each)',
              font=font(26), fill=(20, 20, 20))
    draw.text((760, 30), '(b) token sequence: CLS + 49 patches',
              font=font(26), fill=(20, 20, 20))

    # Panel (a): recover an RGB view from the normalized tensor.
    tensor = images[0]
    mean = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)[:, None, None]
    std = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)[:, None, None]
    rgb = np.clip(tensor * std + mean, 0.0, 1.0).transpose(1, 2, 0)
    picture = Image.fromarray((rgb * 255).astype('uint8')).resize((448, 448), Image.NEAREST)
    left, top = 90, 90
    canvas.paste(picture, (left, top))
    for index in range(8):
        offset = index * 64
        draw.line([left + offset, top, left + offset, top + 448], fill=(255, 255, 255), width=2)
        draw.line([left, top + offset, left + 448, top + offset], fill=(255, 255, 255), width=2)
    small = font(17)
    for row in range(7):
        for col in range(7):
            x = left + col * 64 + 32
            y = top + row * 64 + 32
            text = str(row * 7 + col)
            draw.rectangle([x - 15, y - 11, x + 15, y + 11], fill=(0, 0, 0))
            draw.text((x, y), text, font=small, fill=(255, 255, 255), anchor='mm')
    draw.text((left, top + 470), 'patch index runs left to right, then top to bottom',
              font=font(19), fill=(70, 70, 70))

    # Panel (b): 50 token rows, each 768 numbers wide.
    cell_w, cell_h = 300, 9
    left, top = 900, 90
    draw.rectangle([left, top, left + cell_w, top + 50 * cell_h], outline=(60, 60, 60), width=2)
    for row in range(50):
        colour = (240, 160, 70) if row == 0 else (70, 120, 190)
        draw.rectangle([left + 1, top + row * cell_h + 1,
                        left + cell_w - 1, top + (row + 1) * cell_h - 1], fill=colour)
    draw.text((left - 18, top + cell_h // 2), 'CLS', font=font(19), fill=(20, 20, 20), anchor='rm')
    # Bracket the 49 patch rows so the second label clearly covers rows 1-49.
    bracket_x = left + cell_w + 10
    draw.line([bracket_x, top + cell_h + 2, bracket_x + 10, top + cell_h + 2], fill=(60, 60, 60), width=2)
    draw.line([bracket_x, top + 49 * cell_h - 2, bracket_x + 10, top + 49 * cell_h - 2], fill=(60, 60, 60), width=2)
    draw.line([bracket_x + 10, top + cell_h + 2, bracket_x + 10, top + 49 * cell_h - 2], fill=(60, 60, 60), width=2)
    draw.text((bracket_x + 18, top + 25 * cell_h), '49 patch rows',
              font=font(19), fill=(20, 20, 20), anchor='lm')
    draw.text((bracket_x + 18, top + 25 * cell_h + 28), 'shape [50, 768]',
              font=font(20), fill=(20, 20, 20), anchor='lm')
    draw.text((bracket_x + 18, top + 25 * cell_h + 56), 'one row per token',
              font=font(18), fill=(90, 90, 90), anchor='lm')

    canvas.save(path)


def figure_errors(results, path):
    """Log-scale bars of max absolute error, one group per checked stage."""
    width, height = 1400, 720
    canvas = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((70, 30), 'max absolute error per stage (float32 NumPy vs FP32 reference)',
              font=font(26), fill=(20, 20, 20))

    box = (150, 110, 1340, 610)
    ymin, ymax = 1e-7, 1e-3
    draw_axes(draw, box, ymin, ymax, [1e-7, 1e-6, 1e-5, 1e-4, 1e-3])
    left, top, right, bottom = box
    lo, hi = np.log10(ymin), np.log10(ymax)

    def y_of(value):
        return bottom - (np.log10(value) - lo) / (hi - lo) * (bottom - top)

    # Tolerance lines: internal stages 2e-4, output stages 2e-5.
    for value, label in ((2e-4, 'atol 2e-4 (internal)'), (2e-5, 'atol 2e-5 (output)')):
        y = y_of(value)
        for x in range(left, right, 22):
            draw.line([x, y, x + 12, y], fill=(200, 60, 60), width=2)
        draw.text((right - 6, y - 6), label, font=font(18), fill=(200, 60, 60), anchor='rs')

    count = len(STAGES)
    slot = (right - left) / count
    bar_w = slot * 0.46
    for index, stage in enumerate(STAGES):
        _, max_abs, _, _, _ = results[stage]
        centre = left + slot * (index + 0.5)
        if max_abs > 0:
            y = y_of(max(max_abs, ymin))
            draw.rectangle([centre - bar_w / 2, y, centre + bar_w / 2, bottom],
                           fill=(58, 106, 176))
            draw.text((centre, y - 10), f'{max_abs:.1e}', font=font(19),
                      fill=(20, 20, 20), anchor='ms')
        else:
            draw.rectangle([centre - bar_w / 2, bottom - 4, centre + bar_w / 2, bottom],
                           fill=(58, 106, 176))
            draw.text((centre, bottom - 18), '0', font=font(21), fill=(20, 20, 20), anchor='ms')
        draw.text((centre, bottom + 18), stage, font=font(20), fill=(40, 40, 40), anchor='mt')

    draw.text((70, 660), 'Bars start at 1e-7 for display; exact zeros are labelled 0.',
              font=font(19), fill=(90, 90, 90))
    canvas.save(path)


def figure_similarity(tokens, path):
    """Cosine similarity matrix of the ten 512-d output tokens."""
    similarity = tokens @ tokens.T
    cell = 46
    left, top = 130, 82
    canvas = Image.new('RGB', (780, 650), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 20), 'cosine similarity of the ten output tokens',
              font=font(22), fill=(20, 20, 20))

    low, high = float(similarity.min()), float(similarity.max())
    off_diagonal = similarity[~np.eye(10, dtype=bool)]
    for row in range(10):
        for col in range(10):
            value = similarity[row, col]
            x0 = left + col * cell
            y0 = top + row * cell
            draw.rectangle([x0, y0, x0 + cell, y0 + cell], fill=blue((value - low) / (high - low)))
            text = '1.00' if value > 0.9999 else f'{value:.2f}'
            ink = (255, 255, 255) if (value - low) / (high - low) > 0.55 else (20, 20, 20)
            draw.text((x0 + cell / 2, y0 + cell / 2), text, font=font(22), fill=ink, anchor='mm')

    for index in range(10):
        x = left + index * cell + cell / 2
        y = top + index * cell + cell / 2
        draw.text((x, top - 12), str(index + 1), font=font(19), fill=(40, 40, 40), anchor='mb')
        draw.text((left - 12, y), str(index + 1), font=font(19), fill=(40, 40, 40), anchor='rm')
    draw.text((left + 5 * cell, top + 10 * cell + 26), 'image index (1-10)',
              font=font(19), fill=(40, 40, 40), anchor='mt')
    draw.text((30, top + 10 * cell + 62), f'diagonal = 1.00, off-diagonal in '
              f'[{off_diagonal.min():.2f}, {off_diagonal.max():.2f}]',
              font=font(18), fill=(90, 90, 90))

    # Colour bar.
    bar_x, bar_top, bar_h, bar_w = 645, 130, 290, 26
    for step in range(bar_h):
        t = 1.0 - step / (bar_h - 1)
        draw.rectangle([bar_x, bar_top + step, bar_x + bar_w, bar_top + step + 1], fill=blue(t))
    draw.rectangle([bar_x, bar_top, bar_x + bar_w, bar_top + bar_h], outline=(80, 80, 80), width=2)
    draw.text((bar_x + bar_w + 8, bar_top), f'{high:.2f}', font=font(17), fill=(40, 40, 40), anchor='lm')
    draw.text((bar_x + bar_w + 8, bar_top + bar_h), f'{low:.2f}', font=font(17), fill=(40, 40, 40), anchor='lm')
    canvas.save(path)


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'docs' / 'figures')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    weights = load_weights()
    encoder = ImageEncoder(weights)
    images = load_images()

    # Time a cold forward pass first (same process, caches warm afterwards).
    preprocess_s, embed_s, encode_s, forward_s = timing(encoder, images)

    results = run_stages(encoder, images)
    tokens = encoder(images)

    rows = []
    for stage in STAGES:
        ok, max_abs, mean_abs, shape, seconds = results[stage]
        rows.append({'stage': stage, 'shape': 'x'.join(map(str, shape)),
                     'max_abs': f'{max_abs:.3e}', 'mean_abs': f'{mean_abs:.3e}',
                     'atol': f'{TOLERANCE[stage]:.0e}', 'pass': 'yes' if ok else 'no',
                     'seconds': f'{seconds:.3f}'})
    with (ROOT / 'docs/results.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    figure_patches(images, args.out / 'fig1_patches.png')
    figure_errors(results, args.out / 'fig2_errors.png')
    figure_similarity(tokens, args.out / 'fig3_similarity.png')

    print('stage        shape              max_abs     mean_abs    atol    pass')
    for row in rows:
        print(f"{row['stage']:12} {row['shape']:18} {row['max_abs']:>11} "
              f"{row['mean_abs']:>11} {row['atol']:>7}  {row['pass']}")
    norms = np.sqrt((tokens * tokens).sum(-1))
    print(f'\nunit length: max |norm-1| = {np.abs(norms - 1).max():.2e}')
    print(f'timing (10 images): preprocess {preprocess_s:.2f}s, embed {embed_s:.2f}s, '
          f'12 blocks {encode_s:.2f}s, full forward {forward_s:.2f}s '
          f'({forward_s / 10 * 1000:.0f} ms/image)')
    print('figures ->', args.out)


if __name__ == '__main__':
    main()
