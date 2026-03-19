#!/usr/bin/env python3
"""
Sample Picker
==============
Scans a local sample library (Splice, downloaded packs, etc.) and picks
drum samples organized into a project-ready folder.

Focused on percussion: kick, snare, hat, perc. Picks 3-5 options per
slot so you can quickly audition and choose in your DAW.

Usage:
    python3 sample_picker.py ~/Splice/sounds -o my_project/samples
    python3 sample_picker.py ~/Splice/sounds --picks 5 --vibe lofi
    python3 sample_picker.py ~/Splice/sounds --vibe trap --seed 42
    python3 sample_picker.py ~/Splice/sounds --scan-only
    python3 sample_picker.py ~/Splice/sounds --vibe dark --exclude acoustic

How it works:
    1. Recursively scans the folder for .wav / .aif / .flac / .mp3 files
    2. Classifies each file as kick, snare, hat, or perc based on filename
    3. Optionally filters by a "vibe" keyword (lofi, trap, acoustic, etc.)
    4. Picks N random candidates per slot
    5. Copies them into a clean folder structure ready to drag into your DAW

Output structure:
    samples/
    ├── kick/
    │   ├── 1_kick_808_dark_punch.wav
    │   ├── 2_kick_sub_heavy.wav
    │   └── 3_kick_analog_deep.wav
    ├── snare/
    │   ├── 1_snare_crispy_crack.wav
    │   └── ...
    ├── hat/
    │   └── ...
    └── perc/
        └── ...

Requirements:
    - Python 3.7+
    - No external dependencies
"""

import argparse
import os
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set


# ──────────────────────────────────────────────
# Classification Rules
# ──────────────────────────────────────────────

# Each slot has primary keywords (strong match) and secondary keywords (weaker match).
# Files are classified by checking the filename against these keywords.
# A file only lands in one slot — first strong match wins.

SLOTS = {
    'kick': {
        'primary': [
            'kick', 'kck', 'kik', 'bd', 'bassdrum', 'bass_drum', 'bass drum',
        ],
        'secondary': [
            '808',  # 808 often means kick/bass — but could be a tag
        ],
        'exclude': [
            'sidekick', 'hat', 'snare', 'perc', 'rim', 'clap', 'bass',
        ],
    },
    'snare': {
        'primary': [
            'snare', 'snr', 'sd', 'clap', 'clp', 'rim', 'rimshot', 'snap',
        ],
        'secondary': [],
        'exclude': [
            'kick', 'hat', 'ride',
        ],
    },
    'hat': {
        'primary': [
            'hat', 'hh', 'hihat', 'hi-hat', 'hi hat',
            'closedhat', 'openhat', 'closed_hat', 'open_hat',
            'ch', 'oh',  # common abbreviations
        ],
        'secondary': [
            'cymbal', 'ride', 'crash',
        ],
        'exclude': [
            'kick', 'snare', 'clap',
        ],
    },
    'perc': {
        'primary': [
            'perc', 'percussion', 'conga', 'bongo', 'shaker', 'tambourine',
            'tamb', 'cowbell', 'woodblock', 'clave', 'guiro', 'triangle',
            'tom', 'timbale', 'djembe', 'tabla', 'agogo', 'cabasa',
            'maracas', 'vibraslap', 'castanet',
        ],
        'secondary': [
            'click', 'tick', 'knock', 'tap', 'hit', 'impact',
            'noise', 'fx', 'effect', 'rattle', 'scrape', 'metallic',
        ],
        'exclude': [
            'kick', 'snare', 'hat', 'hihat', 'clap',
        ],
    },
}

# Audio file extensions we care about
AUDIO_EXTENSIONS = {'.wav', '.aif', '.aiff', '.flac', '.mp3', '.ogg'}


# ──────────────────────────────────────────────
# Scanner
# ──────────────────────────────────────────────

def scan_samples(root_dir: str, verbose: bool = False) -> Dict[str, List[str]]:
    """
    Recursively scan a directory and classify audio files into slots.

    Returns a dict: { 'kick': [path, ...], 'snare': [...], ... }
    """
    classified: Dict[str, List[str]] = defaultdict(list)
    total_files = 0
    audio_files = 0

    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"Error: Directory not found: {root_dir}")
        sys.exit(1)

    for filepath in root_path.rglob('*'):
        if not filepath.is_file():
            continue
        total_files += 1

        if filepath.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        audio_files += 1

        # Build a searchable string from the full path (catches folder names too)
        # e.g. "Splice/sounds/Trap Essentials/kicks/kick_808_hard.wav"
        search_str = str(filepath).lower()
        filename_str = filepath.stem.lower()

        # Classify
        slot = _classify(search_str, filename_str)
        if slot:
            classified[slot].append(str(filepath))

    if verbose:
        print(f"  Scanned {total_files} files, {audio_files} audio files")
        for slot in ['kick', 'snare', 'hat', 'perc']:
            count = len(classified.get(slot, []))
            print(f"  {slot:>6}: {count} samples found")

    return dict(classified)


def _classify(search_str: str, filename_str: str) -> Optional[str]:
    """Classify a file into a slot based on keywords in its path/name."""
    # Try primary keywords first (strongest signal)
    for slot, rules in SLOTS.items():
        for keyword in rules['primary']:
            if keyword in filename_str or keyword in search_str.split(os.sep)[-3:]:
                # Check exclusions
                excluded = False
                for excl in rules['exclude']:
                    if excl in filename_str:
                        excluded = True
                        break
                if not excluded:
                    return slot

    # Try secondary keywords (weaker signal, filename only)
    for slot, rules in SLOTS.items():
        for keyword in rules['secondary']:
            if keyword in filename_str:
                excluded = False
                for excl in rules['exclude']:
                    if excl in filename_str:
                        excluded = True
                        break
                if not excluded:
                    return slot

    return None


# ──────────────────────────────────────────────
# Filtering & Picking
# ──────────────────────────────────────────────

def filter_by_vibe(samples: Dict[str, List[str]], vibe: str) -> Dict[str, List[str]]:
    """Filter samples to prefer those matching a vibe keyword."""
    filtered = {}
    for slot, paths in samples.items():
        matching = [p for p in paths if vibe.lower() in p.lower()]
        # If we got matches, use them. Otherwise fall back to full list.
        filtered[slot] = matching if matching else paths
    return filtered


def filter_by_exclude(samples: Dict[str, List[str]], exclude: List[str]) -> Dict[str, List[str]]:
    """Remove samples whose paths contain any of the exclude keywords."""
    filtered = {}
    for slot, paths in samples.items():
        kept = []
        for p in paths:
            p_lower = p.lower()
            if not any(ex.lower() in p_lower for ex in exclude):
                kept.append(p)
        filtered[slot] = kept if kept else paths  # fallback if everything excluded
    return filtered


def pick_samples(
    samples: Dict[str, List[str]],
    picks_per_slot: int = 3,
    seed: Optional[int] = None,
) -> Dict[str, List[str]]:
    """Pick N random samples per slot."""
    if seed is not None:
        random.seed(seed)

    picked = {}
    for slot in ['kick', 'snare', 'hat', 'perc']:
        pool = samples.get(slot, [])
        if not pool:
            picked[slot] = []
            continue
        n = min(picks_per_slot, len(pool))
        picked[slot] = random.sample(pool, n)

    return picked


# ──────────────────────────────────────────────
# Output
# ──────────────────────────────────────────────

def copy_picks(picks: Dict[str, List[str]], output_dir: str, verbose: bool = False):
    """Copy picked samples into a clean output folder structure."""
    out_path = Path(output_dir)

    # Don't nuke an existing folder — create alongside
    out_path.mkdir(parents=True, exist_ok=True)

    for slot in ['kick', 'snare', 'hat', 'perc']:
        slot_dir = out_path / slot
        slot_dir.mkdir(exist_ok=True)

        paths = picks.get(slot, [])
        if not paths:
            if verbose:
                print(f"  {slot:>6}: no samples found")
            continue

        for i, src_path in enumerate(paths, 1):
            src = Path(src_path)
            # Prefix with number for easy ordering
            dest_name = f"{i}_{src.name}"
            dest = slot_dir / dest_name
            shutil.copy2(str(src), str(dest))

            if verbose:
                # Show a compact relative path
                try:
                    rel = src.name
                except ValueError:
                    rel = src.name
                print(f"  {slot:>6} {i}: {rel}")


def print_summary(picks: Dict[str, List[str]], output_dir: str):
    """Print a summary of what was picked."""
    print(f"\n{'═' * 60}")
    print(f"  Sample Picks")
    print(f"{'═' * 60}")

    total = 0
    for slot in ['kick', 'snare', 'hat', 'perc']:
        paths = picks.get(slot, [])
        total += len(paths)
        if not paths:
            print(f"  {slot:>6}: (none found)")
            continue

        print(f"\n  {slot.upper()} ({len(paths)} options):")
        for i, p in enumerate(paths, 1):
            name = Path(p).name
            # Truncate long names
            if len(name) > 50:
                name = name[:47] + '...'
            print(f"    {i}. {name}")

    print(f"\n{'─' * 60}")
    print(f"  {total} samples → {output_dir}/")
    print(f"  Drag into your DAW and audition!")
    print()


def write_sample_map(picks: Dict[str, List[str]], output_dir: str):
    """Write a sample_map.txt alongside the picks for reference."""
    map_path = Path(output_dir) / "sample_map.txt"
    lines = ["Sample Picks", "=" * 40, ""]

    for slot in ['kick', 'snare', 'hat', 'perc']:
        paths = picks.get(slot, [])
        lines.append(f"{slot.upper()} ({len(paths)} options):")
        for i, p in enumerate(paths, 1):
            lines.append(f"  {i}. {Path(p).name}")
            lines.append(f"     Source: {p}")
        lines.append("")

    lines.append("Drag your favorites into your DAW session.")
    lines.append("Delete the rest, or keep them for later.")

    map_path.write_text('\n'.join(lines))


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description='Sample Picker — scan your library, pick drum samples',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/Splice/sounds
  %(prog)s ~/Splice/sounds --picks 5 --vibe lofi
  %(prog)s ~/Splice/sounds --vibe trap --exclude acoustic orchestral
  %(prog)s ~/Splice/sounds --scan-only
  %(prog)s /path/to/any/sample/folder --seed 42 -o my_project/samples

The output folder can be placed inside your Ableton project folder
for easy access via the browser sidebar.
        """
    )

    parser.add_argument('sample_dir', type=str,
                        help='Root directory to scan for samples (e.g. ~/Splice/sounds)')
    parser.add_argument('--output', '-o', type=str, default='./sample_picks',
                        help='Output directory for picked samples (default: ./sample_picks)')
    parser.add_argument('--picks', '-n', type=int, default=3,
                        help='Number of options per slot (default: 3, max: 10)')
    parser.add_argument('--vibe', type=str, default=None,
                        help='Filter keyword to match a vibe (e.g. lofi, trap, dark, vinyl, acoustic)')
    parser.add_argument('--exclude', nargs='+', default=None,
                        help='Keywords to exclude (e.g. --exclude acoustic orchestral bright)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducible picks')
    parser.add_argument('--scan-only', action='store_true',
                        help='Just scan and report counts, don\'t copy anything')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed output')

    return parser.parse_args()


def main():
    args = parse_args()
    args.picks = max(1, min(10, args.picks))

    # Expand ~ in path
    sample_dir = os.path.expanduser(args.sample_dir)

    print(f"\n🔍 Scanning: {sample_dir}")
    classified = scan_samples(sample_dir, verbose=True)

    total_found = sum(len(v) for v in classified.values())
    if total_found == 0:
        print("\n  No drum samples found. Check the directory path.")
        print("  Common Splice locations:")
        print("    Mac:     ~/Splice/sounds")
        print("    Windows: C:\\Documents\\Splice\\sounds")
        sys.exit(1)

    if args.scan_only:
        print("\n  (scan-only mode, not copying)")
        return

    # Filter
    filtered = classified
    if args.vibe:
        print(f"\n🎨 Filtering for vibe: '{args.vibe}'")
        filtered = filter_by_vibe(filtered, args.vibe)
        for slot in ['kick', 'snare', 'hat', 'perc']:
            orig = len(classified.get(slot, []))
            filt = len(filtered.get(slot, []))
            if filt < orig:
                print(f"  {slot:>6}: {orig} → {filt} matching '{args.vibe}'")

    if args.exclude:
        print(f"\n🚫 Excluding: {', '.join(args.exclude)}")
        filtered = filter_by_exclude(filtered, args.exclude)

    # Pick
    picks = pick_samples(filtered, args.picks, args.seed)

    # Copy
    output_dir = args.output
    if args.verbose:
        print(f"\n📁 Copying to: {output_dir}")

    copy_picks(picks, output_dir, verbose=args.verbose)
    write_sample_map(picks, output_dir)

    # Summary
    print_summary(picks, output_dir)


if __name__ == '__main__':
    main()
