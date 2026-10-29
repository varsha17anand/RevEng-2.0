#!/usr/bin/env python3
"""TruthLens Real-World AI Image Metadata & C2PA Inspector.

Scans the samples/real/ directory for images exported from commercial AI tools
(e.g., ChatGPT, DALL-E, Adobe Firefly, Midjourney) and inspects what Instagram
mode finds for each file.

Skips gracefully if no files are present in samples/real/.
Never fakes results.
"""

import glob
import os
import sys

# Ensure backend is on PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.labeler import instagram_mode_label


def check_real_files():
    real_dir = os.path.join(ROOT, "samples", "real")
    os.makedirs(real_dir, exist_ok=True)

    # Collect files excluding hidden files like .gitkeep or .DS_Store
    all_entries = sorted(glob.glob(os.path.join(real_dir, "*")))
    image_files = [f for f in all_entries if not os.path.basename(f).startswith(".")]

    if not image_files:
        print(f"No files present in {os.path.relpath(real_dir, ROOT)}/ — skipping gracefully.")
        print("To test real AI images, export photos from ChatGPT or Adobe Firefly into samples/real/.")
        return 0

    print("=" * 80)
    print("TruthLens — Real Files Instagram-Mode Inspection")
    print(f"Directory: {os.path.relpath(real_dir, ROOT)}/ ({len(image_files)} file(s))")
    print("=" * 80)

    for path in image_files:
        fname = os.path.basename(path)
        size_bytes = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read()

        res = instagram_mode_label(data)
        sig = res.get("detection_signal", {})

        print(f"\nFile: {fname} ({size_bytes:,} bytes)")
        print(f"  Instagram Label: {res['label']}")
        print(f"  AI Detected:     {res['has_ai_label']}")
        print(f"  Primary Signal:  {sig.get('signal', 'none')}")
        print(f"  C2PA Manifest:   {sig.get('c2pa', False)}")
        print(f"  IPTC Source:     {sig.get('iptc_source_type')}")
        print(f"  Reason:          {res['reason']}")

    print("\n" + "=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(check_real_files())

