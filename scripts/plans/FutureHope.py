import json
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


# ============================================================
# Config
# ============================================================

# Set to an int like 5 while testing. Keep as None for full run.
TEST_LIMIT = 5

# Change this to whatever model you have installed in Ollama.
MODEL_NAME = "qwen3:14b"

# Default frontmatter values. You can edit these per reading plan.
PLAN_TITLE = "The Prophets' Future Hope"
PLAN_SLUG = "prophets-hope"
PLAN_DESCRIPTION = (
    "a collection of passages that explore the future hopes of the major and minor prophets"
)
PLAN_IMAGE_URL = ""

SCRIPT_DIR = Path(__file__).resolve().parent

POSSIBLE_VERSEFETCH_DIRS = [
    Path(r"C:\git_repos\bible_data\WorldEnglishBible"),
    Path(r"C:\git_repos\bible-data\WorldEnglishBible"),
    SCRIPT_DIR.parent / "WorldEnglishBible",
    SCRIPT_DIR.parents[1] / "WorldEnglishBible",
]

VERSEFETCH_DIR = None

for possible_dir in POSSIBLE_VERSEFETCH_DIRS:
    if (possible_dir / "VerseFetch.py").exists():
        VERSEFETCH_DIR = possible_dir
        break

if VERSEFETCH_DIR is None:
    raise FileNotFoundError(
        "Could not find VerseFetch.py. Checked:\n"
        + "\n".join(str(p) for p in POSSIBLE_VERSEFETCH_DIRS)
    )

sys.path.insert(0, str(VERSEFETCH_DIR))

import VerseFetch  # noqa: E402
from VerseFetch import iter_verses  # noqa: E402


# ============================================================
# Basic file helpers
# ============================================================

def load_json_list(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in: {path}")

    references = []
    seen = set()

    for item in data:
        if not isinstance(item, str):
            continue

        reference = item.strip()

        if not reference:
            continue

        # Keep the first occurrence only.
        if reference in seen:
            continue

        seen.add(reference)
        references.append(reference)

    return references


def save_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def reset_file(path):
    if path.exists():
        path.unlink()


# ============================================================
# Reference text
# ============================================================

def get_reference_text(reference):
    """
    Uses your WorldEnglishBible VerseFetch.iter_verses helper.

    Works for:
      Isaiah 26:19
      Zechariah 14:10-15
      Isaiah 10
    """

    verses = list(iter_verses(reference))

    if not verses:
        raise ValueError(f"No verses found for reference: {reference}")

    parts = []

    for verse in verses:
        verse_ref = verse.get("reference", reference)
        verse_text = verse.get("text", "").strip()

        if verse_text:
            parts.append(f"{verse_ref} {verse_text}")

    text = "\n".join(parts).strip()

    if not text:
        raise ValueError(f"No verse text found for reference: {reference}")

    return text


# ============================================================
# Ollama title generation
# ============================================================

def strip_thinking(text):
    """
    Removes common local-model thinking tags if the model outputs them.
    """

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^Thinking\.\.\..*", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


def clean_title(raw_title):
    title = strip_thinking(raw_title)

    # Use first non-empty line only.
    lines = [line.strip() for line in title.splitlines() if line.strip()]
    title = lines[0] if lines else "Untitled Passage"

    # Remove labels and surrounding quotes.
    title = re.sub(r"^(title|passage title)\s*:\s*", "", title, flags=re.IGNORECASE)
    title = title.strip().strip('"').strip("'").strip()

    # Remove markdown heading markers if the model adds them.
    title = re.sub(r"^#+\s*", "", title).strip()

    # Keep titles compact.
    title = re.sub(r"\s+", " ", title)

    if len(title) > 80:
        title = title[:77].rstrip(" ,;:-") + "..."

    if not title:
        title = "Untitled Passage"

    return title


def build_title_prompt(reference, text):
    return f"""You are titling a Bible reading-plan passage.

Create one short, clear passage title for this reference.

Rules:
- Return only the title.
- Do not include quotation marks.
- Do not include the reference.
- Do not include a subtitle.
- Use Title Case.
- Keep it under 8 words.
- Make it specific to the passage's main theme.

Reference:
{reference}

Passage text:
{text}
"""


def generate_passage_title(reference, text):
    prompt = build_title_prompt(reference, text)

    result = subprocess.run(
        ["ollama", "run", MODEL_NAME],
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown Ollama error."
        raise RuntimeError(stderr)

    return clean_title(result.stdout)


# ============================================================
# Markdown rendering
# ============================================================

def render_frontmatter():
    return (
        f"title: {PLAN_TITLE}\n"
        f"slug: {PLAN_SLUG}\n"
        f"description: {PLAN_DESCRIPTION}\n"
        f"image_url: {PLAN_IMAGE_URL}\n"
        "---\n\n"
    )


def render_day(day_number, reference, title):
    return (
        f"# Day {day_number}: {reference} {title}\n\n"
        "::scripture\n"
        f"{reference}\n"
        "::\n"
    )


def build_reading_plan(references, output_log_path):
    days = []
    title_records = []
    errors = []

    total = len(references)

    print(f"Using VerseFetch from: {VerseFetch.__file__}")
    print(f"Using Ollama model: {MODEL_NAME}")
    print(f"Loaded {total} references.")
    print()

    for index, reference in enumerate(references, start=1):
        print(f"[{index}/{total}] Building Day {index}: {reference}")

        try:
            text = get_reference_text(reference)
            title = generate_passage_title(reference, text)

            days.append(render_day(index, reference, title))

            record = {
                "day": index,
                "reference": reference,
                "title": title,
                "text": text,
            }

            title_records.append(record)
            append_jsonl(output_log_path, record)

            print(f"  Title: {title}")

        except Exception as e:
            fallback_title = "Passage Reading"
            days.append(render_day(index, reference, fallback_title))

            error_record = {
                "day": index,
                "reference": reference,
                "title": fallback_title,
                "error": str(e),
            }

            errors.append(error_record)
            append_jsonl(output_log_path, error_record)

            print(f"  ERROR: {e}")
            print(f"  Fallback title: {fallback_title}")

        print("-" * 80)

    markdown = render_frontmatter() + "\n\n".join(days).rstrip() + "\n"

    return markdown, title_records, errors


# ============================================================
# UI
# ============================================================

def choose_json_file():
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        title="Choose JSON list of verse references",
        filetypes=[
            ("JSON files", "*.json"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()

    if not path:
        return None

    return Path(path)


# ============================================================
# Main
# ============================================================

def main():
    input_path = choose_json_file()

    if input_path is None:
        print("No file selected.")
        return

    try:
        references = load_json_list(input_path)

        if TEST_LIMIT is not None:
            references = references[:TEST_LIMIT]

        output_md_path = input_path.with_name(f"{input_path.stem}_reading_plan.md")
        output_titles_path = input_path.with_name(f"{input_path.stem}_reading_plan_titles.json")
        output_errors_path = input_path.with_name(f"{input_path.stem}_reading_plan_errors.json")
        output_log_path = input_path.with_name(f"{input_path.stem}_reading_plan_log.jsonl")

        reset_file(output_log_path)

        markdown, title_records, errors = build_reading_plan(
            references,
            output_log_path,
        )

        save_text(output_md_path, markdown)
        save_json(output_titles_path, title_records)

        if errors:
            save_json(output_errors_path, errors)

        print()
        print("Done.")
        print(f"Reading plan written to: {output_md_path}")
        print(f"Title records written to: {output_titles_path}")
        print(f"Log written to: {output_log_path}")

        if errors:
            print(f"Errors written to: {output_errors_path}")
            print(f"Error count: {len(errors)}")

        print(f"Successfully processed: {len(title_records)}")

        messagebox.showinfo(
            "Done",
            "Reading plan built.\n\n"
            f"Markdown:\n{output_md_path}\n\n"
            f"Titles JSON:\n{output_titles_path}"
        )

    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise


if __name__ == "__main__":
    main()
