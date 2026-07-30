#!/usr/bin/env python3
"""
scan_to_post.py — Phase 9 scan-to-blog pipeline.

For each new PDF in the inbox not yet recorded in the state file:

  1. Parse filename (YYYYMMDD_slug.pdf → date + slug + title)
  2. Render pages to JPG via pdftoppm
  3. OCR via ocrmypdf --sidecar
  4. Generate a Hugo page bundle (index.md + images/) with draft: true
  5. Move the original PDF to /processed (or /failed)

Idempotency via .processed.json state file. Re-runnable safely.

Usage (inside the blog-scan container):
    scan_to_post.py \
        --inbox      /inbox \
        --processed  /processed \
        --failed     /failed \
        --content    /site/content \
        --state      /var/lib/scan/.processed.json
"""

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

LOG = logging.getLogger("scan_to_post")

# Filename pattern: YYYYMMDD_slug.pdf (slug may contain letters, digits, hyphens,
# underscores). Case-insensitive .pdf extension.
FILENAME_RE = re.compile(r"^(\d{8})_(.+)\.pdf$", re.IGNORECASE)

# Words that should stay lowercase in a title unless they're the first word.
STOPWORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
    "as", "at", "by", "in", "of", "on", "to", "up", "via",
    "from", "into", "onto", "over", "with", "is", "are",
}

# Render DPI for scans — 200 is the sweet spot for typewritten text on
# letter/A4 paper (per Phase 9 §9.5).
DPI = 200


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------

def load_state(path: Path) -> dict:
    """Load the .processed.json state file. Returns {} if missing or corrupt."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        LOG.warning("state file unreadable (%s); starting fresh", e)
        return {}


def save_state(path: Path, state: dict) -> None:
    """Persist the state file atomically (write-then-rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

def parse_filename(filename: str) -> tuple[datetime, str, str] | None:
    """
    Parse a filename like '20260624_test-post.pdf'.

    Returns (post_date, slug, title), or None if the filename doesn't match.
    """
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    date_str, slug_raw = m.group(1), m.group(2)

    try:
        post_date = datetime.strptime(date_str, "%Y%m%d").replace(
            hour=12, tzinfo=timezone.utc,
        )
    except ValueError:
        return None

    slug = slug_raw.strip("-_").lower()
    slug = re.sub(r"[^a-z0-9-_]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        return None

    title = titleize_slug(slug)
    return post_date, slug, title


def titleize_slug(slug: str) -> str:
    """
    Convert 'ramble-on-typewriters' → 'Ramble on Typewriters'.

    Lowercases stopwords (unless first), capitalizes the rest. Hyphens and
    underscores become spaces.
    """
    words = slug.replace("_", "-").split("-")
    out = []
    for i, word in enumerate(words):
        if not word:
            continue
        # Preserve digits as-is.
        if word.isdigit():
            out.append(word)
            continue
        # Strip accents for a clean title (é → e).
        word = "".join(
            c for c in unicodedata.normalize("NFKD", word)
            if not unicodedata.combining(c)
        )
        if i == 0 or word.lower() not in STOPWORDS:
            out.append(word.capitalize())
        else:
            out.append(word.lower())
    return " ".join(out)


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def render_pages(pdf: Path, dest_dir: Path) -> list[Path]:
    """Render each PDF page to a zero-padded JPG in dest_dir. Returns paths."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    prefix = dest_dir / "page"
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", str(DPI), str(pdf), str(prefix)],
        check=True,
    )
    # pdftoppm emits page-1.jpg, page-2.jpg, ... (no zero-pad by default).
    # Rename to page-01.jpg etc.
    rendered = sorted(dest_dir.glob("page-*.jpg"))
    final = []
    for i, src in enumerate(rendered, start=1):
        dst = dest_dir / f"page-{i:02d}.jpg"
        if src.name != dst.name:
            src.rename(dst)
        final.append(dst)
    return final


def ocr_pdf(pdf: Path, sidecar: Path) -> list[str]:
    """
    Run ocrmypdf --sidecar and parse the resulting text by form-feed.

    Returns a list of per-page OCR strings (possibly empty if OCR fails silently).

    `--force-ocr` is intentional: the typical input here is a typewritten
    page scan (image-only PDF), so the flag is a no-op there. If a born-digital
    PDF lands in the inbox, it gets rasterized + OCRed rather than aborting
    with PriorOcrFoundError. See Phase 9 §9.5.

    `--jobs 1` keeps memory bounded: ocrmypdf defaults to one worker per
    physical core, which can OOM-kill the container on multi-page PDFs (each
    worker holds a full-page rasterization in memory). Sequential is plenty
    fast for low-page-count scans — a 10-page scan at ~2s/page is 20s.
    """
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    # Output to /dev/null: we don't want a re-encoded PDF, just the sidecar text.
    # ocrmypdf requires the OUTPUT path to exist as a writable file or /dev/null.
    subprocess.run(
        ["ocrmypdf", "--force-ocr", "--jobs", "1", "--sidecar", str(sidecar),
         "--output-type", "pdf", str(pdf), "/dev/null"],
        check=True,
    )
    text = sidecar.read_text(errors="replace")
    pages = [p.strip() for p in text.split("\x0c")]
    return pages


def clean_ocr_text(pages: list[str]) -> list[str]:
    """
    Normalize per-page OCR text. Collapses runs of blank lines, strips trailing
    whitespace, returns non-empty cleaned pages.
    """
    cleaned = []
    for page in pages:
        lines = [ln.rstrip() for ln in page.split("\n")]
        # Collapse 3+ blank lines into 2 (paragraph break).
        out, blank = [], 0
        for ln in lines:
            if not ln.strip():
                blank += 1
                if blank <= 1:
                    out.append("")
            else:
                blank = 0
                out.append(ln)
        text = "\n".join(out).strip()
        if text:
            cleaned.append(text)
    return cleaned


def write_post_bundle(
    content_root: Path,
    post_date: datetime,
    slug: str,
    title: str,
    image_paths: list[Path],
    ocr_pages: list[str],
) -> Path:
    """
    Create the Hugo page bundle at content_root/post/YYYY-MM-DD-slug/.

    Returns the bundle directory path. The bundle contains:
      index.md       — front matter + image refs + <details>-wrapped OCR text
      images/        — page-NN.jpg files (relative refs in index.md)
      ocr_raw.txt    — the raw OCR text for reference
    """
    iso_date = post_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    bundle = content_root / "post" / f"{post_date.strftime('%Y-%m-%d')}-{slug}"
    bundle.mkdir(parents=True, exist_ok=True)

    images_dir = bundle / "images"
    images_dir.mkdir(exist_ok=True)

    # Move (not copy) the rendered JPGs into the bundle. They're already in
    # dest_dir from render_pages(); move them to keep the source PDF dir clean.
    for src in image_paths:
        dst = images_dir / src.name
        if src.resolve() != dst.resolve():
            shutil.move(str(src), str(dst))

    # Build the body.
    image_md = "\n\n".join(
        f"![Page {i+1}](images/page-{i+1:02d}.jpg)"
        for i in range(len(image_paths))
    )

    if ocr_pages:
        ocr_body = "\n\n---\n\n".join(ocr_pages)
        details_block = (
            "<details>\n"
            "<summary>OCR text transcript</summary>\n\n"
            f"{ocr_body}\n\n"
            "</details>"
        )
    else:
        details_block = (
            "<details>\n"
            "<summary>OCR text transcript</summary>\n\n"
            "*OCR did not produce text for this scan — please transcribe manually.*\n\n"
            "</details>"
        )

    frontmatter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {iso_date}\n"
        "draft: true\n"
        'categories: ["typosphere"]\n'
        'tags: ["scan"]\n'
        "---\n"
    )

    body = f"{image_md}\n\n{details_block}\n"
    (bundle / "index.md").write_text(frontmatter + "\n" + body)

    # Drop a copy of the raw OCR text alongside for reference / future edits.
    if ocr_pages:
        (bundle / "ocr_raw.txt").write_text("\n\n---\n\n".join(ocr_pages))

    return bundle


# ---------------------------------------------------------------------------
# Top-level processing of one PDF
# ---------------------------------------------------------------------------

def process_one(
    pdf: Path,
    *,
    content_root: Path,
    processed_dir: Path,
    failed_dir: Path,
) -> tuple[bool, str]:
    """
    Process a single PDF. Returns (success: bool, detail: str).

    On success: moves pdf to processed_dir.
    On failure: moves pdf to failed_dir.
    """
    parsed = parse_filename(pdf.name)
    if not parsed:
        msg = f"filename doesn't match YYYYMMDD_slug.pdf: {pdf.name}"
        LOG.warning(msg)
        move_to(pdf, failed_dir)
        return False, msg

    post_date, slug, title = parsed
    LOG.info("processing %s → %s (%s)", pdf.name, slug, post_date.date())

    work = Path(tempfile.mkdtemp(prefix="scan_"))
    try:
        # 1. Render pages → JPG in work/pages/
        pages_dir = work / "pages"
        try:
            images = render_pages(pdf, pages_dir)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pdftoppm failed: {e}") from e

        if not images:
            raise RuntimeError("pdftoppm produced no images")

        # 2. OCR → sidecar
        sidecar = work / "ocr.txt"
        try:
            raw_pages = ocr_pdf(pdf, sidecar)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ocrmypdf failed: {e}") from e

        ocr_pages = clean_ocr_text(raw_pages)

        # 3. Write the bundle
        bundle = write_post_bundle(
            content_root=content_root,
            post_date=post_date,
            slug=slug,
            title=title,
            image_paths=images,
            ocr_pages=ocr_pages,
        )

        # 4. Move original to processed
        move_to(pdf, processed_dir)
        LOG.info("ok: %s → %s (pages=%d, ocr_pages=%d)",
                 pdf.name, bundle, len(images), len(ocr_pages))
        return True, f"{bundle} ({len(images)} pages, {len(ocr_pages)} OCR)"
    except Exception as e:
        LOG.exception("failed: %s: %s", pdf.name, e)
        move_to(pdf, failed_dir)
        return False, str(e)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def move_to(pdf: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pdf), str(dest_dir / pdf.name))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox",      required=True, type=Path,
                        help="directory where new PDFs land")
    parser.add_argument("--processed",  required=True, type=Path,
                        help="directory for successfully processed PDFs")
    parser.add_argument("--failed",     required=True, type=Path,
                        help="directory for failed PDFs (manual review)")
    parser.add_argument("--content",    required=True, type=Path,
                        help="Hugo content root (writes to <content>/post/...)")
    parser.add_argument("--state",      required=True, type=Path,
                        help="path to .processed.json state file")
    parser.add_argument("--log-level",  default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    for d in (args.inbox, args.processed, args.failed, args.content):
        d.mkdir(parents=True, exist_ok=True)

    state = load_state(args.state)
    # Snapshot of known keys BEFORE processing — anything new we touch gets added.
    known = set(state.keys())

    candidates = sorted(
        p for p in args.inbox.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    )
    LOG.info("inbox scan: %d candidate(s), %d already in state",
             len(candidates), len(known))

    new_count = skip_count = fail_count = 0
    for pdf in candidates:
        if pdf.name in known:
            LOG.debug("skipping already-processed: %s", pdf.name)
            skip_count += 1
            continue
        ok, detail = process_one(
            pdf,
            content_root=args.content,
            processed_dir=args.processed,
            failed_dir=args.failed,
        )
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        state[pdf.name] = {
            "processed_at": now,
            "ok": ok,
            "detail": detail,
        }
        if ok:
            new_count += 1
        else:
            fail_count += 1

    save_state(args.state, state)
    LOG.info("done: new=%d skipped=%d failed=%d", new_count, skip_count, fail_count)
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))