# Sample Picker

Scans a local sample library and organizes drum picks into a project-ready folder. No dependencies, no accounts required.

## What it does

1. Recursively scans a folder for `.wav`, `.aif`, `.flac`, and `.mp3` files
2. Classifies each file as kick, snare, hat, or perc based on filename
3. Optionally filters by a "vibe" keyword (lofi, trap, dark, acoustic, etc.)
4. Picks N random candidates per slot
5. Copies them into a clean folder structure ready to drag into your DAW

## Output

```
samples/
├── kick/
│   ├── 1_kick_808_dark_punch.wav
│   ├── 2_kick_sub_heavy.wav
│   └── 3_kick_analog_deep.wav
├── snare/
├── hat/
└── perc/
```

## Usage

```bash
# Basic pick — 3 options per drum slot
python3 sample_picker.py ~/Splice/sounds -o my_project/samples

# Filter by vibe
python3 sample_picker.py ~/Splice/sounds --vibe lofi

# More options, exclude keywords, reproducible seed
python3 sample_picker.py ~/Splice/sounds --picks 5 --vibe trap --seed 42 --exclude acoustic

# Just scan the library (no copy)
python3 sample_picker.py ~/Splice/sounds --scan-only
```

## Flags

| Flag | Description |
|------|-------------|
| `-o DIR` | Output folder (default: `./samples`) |
| `--picks N` | Options per drum slot (default: 3) |
| `--vibe KEYWORD` | Filter samples by keyword |
| `--exclude WORDS` | Keywords to exclude |
| `--seed N` | Random seed for reproducible picks |
| `--scan-only` | Report counts without copying anything |

## Requirements

- Python 3.7+
- No external dependencies

---

> Also available as part of the [Ableton Production Toolkit](https://github.com/kkojwang/ableton_production_toolkit), which integrates sample picking directly into session generation.
