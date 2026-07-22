#!/usr/bin/env python3
"""Reprocess a draft post's existing images through the three-tier OCR chain.

This is the "manual reprocess" path that runs alongside the live scan
sidecar. It exercises the same ocr_backends.recognize_pages() helper that
scan_to_post.py uses, so the only thing it skips is the rsync+render
preamble.

Usage:
  python3 reprocess_draft.py <post-dir>
  python3 reprocess_draft.py /opt/data/lukemillermakes-hugo/content/post/_drafts/id-1048
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running from anywhere — repo root contains scripts/ocr-pipeline/ocr_backends.py.
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "ocr-pipeline"
sys.path.insert(0, str(SCRIPTS_DIR))

from ocr_backends import (  # noqa: E402  (sys.path manipulation above)
    build_ocr_chain_from_env,
    recognize_pages,
)


def collect_images(post_dir: Path) -> list[Path]:
    """Return the page-*.jpg files for the post, sorted by name."""
    images = sorted((post_dir / "images").glob("page-*.jpg"))
    if not images:
        # Fall back to any JPG in the images dir — works for partial drafts.
        images = sorted((post_dir / "images").glob("*.jpg"))
    return images


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("post_dir", type=Path, help="Path to a Hugo post page bundle")
    p.add_argument("--out-json", type=Path, default=None,
                   help="Optional path to dump the per-page provider results as JSON")
    args = p.parse_args(argv)

    post_dir: Path = args.post_dir
    if not (post_dir / "index.md").exists():
        print(f"ERROR: no index.md under {post_dir}", file=sys.stderr)
        return 2

    images = collect_images(post_dir)
    if not images:
        print(f"ERROR: no images under {post_dir}/images", file=sys.stderr)
        return 2

    chain = build_ocr_chain_from_env()
    pages, providers = recognize_pages(chain, images)

    print(f"==> reprocess {post_dir}")
    print(f"    provider chain: {[p.__class__.__name__ for p in chain.providers]}")
    print(f"    pages: {len(pages)}")
    for i, (img, page, prov) in enumerate(zip(images, pages, providers), start=1):
        status = "OK" if page.strip() else "EMPTY"
        print(f"    [{i}] {img.name}  provider={prov}  status={status}  chars={len(page)}")
        if page.strip():
            preview = page.strip().replace("\n", " ")[:80]
            print(f"        preview: {preview!r}")

    if args.out_json:
        args.out_json.write_text(json.dumps({
            "post": str(post_dir),
            "providers": providers,
            "pages": pages,
            "chain": [p.__class__.__name__ for p in chain.providers],
        }, indent=2, ensure_ascii=False))
        print(f"    wrote {args.out_json}")

    return 0 if all(p.strip() for p in pages) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
