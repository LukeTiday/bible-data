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

# Default frontmatter values. Edit these per reading plan.
PLAN_TITLE = "The Prophets' Future Hope"
PLAN_SLUG = "prophets-hope"
PLAN_DESCRIPTION = (
    "a collection of passages that explore the future hopes of the major and minor prophets"
)
PLAN_IMAGE_URL = ""

# For very long chapters, this keeps prompts from getting absurdly large.
# Increase if you want the whole chapter text passed to Ollama.
MAX_PROMPT_TEXT_CHARS = 8000

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

def strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)


def strip_thinking(text):
    """
    Removes common local-model thinking text.
    Handles complete and incomplete <think> blocks.
    """

    text = strip_ansi(text or "")

    # Complete think block.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # If the model produced an opening <think> but no closing tag, keep only text before it.
    text = re.sub(r"<think>.*$", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove occasional literal thinking labels.
    text = re.sub(r"^Thinking\.\.\..*$", "", text, flags=re.IGNORECASE | re.DOTALL)

    return text.strip()


def clean_title(raw_title):
    title = strip_thinking(raw_title)

    lines = [line.strip() for line in title.splitlines() if line.strip()]
    title = lines[0] if lines else ""

    # Remove labels and surrounding quotes.
    title = re.sub(r"^(title|passage title)\s*:\s*", "", title, flags=re.IGNORECASE)
    title = title.strip().strip('"').strip("'").strip()

    # Remove markdown heading markers or bullets.
    title = re.sub(r"^#+\s*", "", title).strip()
    title = re.sub(r"^[-*]\s*", "", title).strip()

    # Remove reference if the model disobeys.
    title = re.sub(r"^[1-3]?\s?[A-Za-z ]+\s+\d+(:\d+)?(-\d+)?\s*[-:—–]?\s*", "", title).strip()

    title = re.sub(r"\s+", " ", title)

    if len(title) > 80:
        title = title[:77].rstrip(" ,;:-") + "..."

    return title


def build_title_prompt(reference, text):
    if len(text) > MAX_PROMPT_TEXT_CHARS:
        text = text[:MAX_PROMPT_TEXT_CHARS].rstrip() + "\n...[truncated]"

    return f"""/no_think
You are generating titles for a Bible reading plan.

Task:
Write exactly one short passage title for the Bible passage below.

Strict rules:
- Return only the title.
- No explanation.
- No thinking.
- No quotation marks.
- Do not include the Bible reference.
- Use Title Case.
- Maximum 7 words.

Bible reference:
{reference}

Bible passage text:
{text}

Title:"""


def run_ollama(prompt):
    """
    Uses stdin rather than shell=True so Windows paths/special chars are safe.
    """

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

    return result.stdout or ""


def fallback_title_from_reference(reference):
    """
    Only used if Ollama gives no usable title.
    This keeps the markdown readable instead of producing Untitled Passage.
    """

    book = reference.split()[0]

    # Handle books like "1 Samuel".
    if reference[:1].isdigit():
        pieces = reference.split()
        if len(pieces) >= 2:
            book = f"{pieces[0]} {pieces[1]}"

    return f"{book} Reading"


def generate_passage_title(reference, text):
    prompt = build_title_prompt(reference, text)
    raw_output = run_ollama(prompt)
    title = clean_title(raw_output)

    if title:
        return title, raw_output

    # Retry once with an even shorter prompt. This helps Qwen if it only returns thinking.
    retry_prompt = f"""/no_think
Return only a short Title Case Bible passage title.
Do not include the reference.
Title should be reflective of the content and distinctive between other old testament prophecies of future hope
Good Examples:
Valley of Dry Bones
Parable of Josephs Twig
New Growth Metaphor for Israel's Return

Avoid titles that could go with many prophecy
Bad Examples:
Israel's Regathering
Ezekiel Prophecy
Prophecy of Hope

Maximum 7 words.

Reference: {reference}
Passage: {text[:1200]}

Title:"""

    raw_retry_output = run_ollama(retry_prompt)
    retry_title = clean_title(raw_retry_output)

    if retry_title:
        return retry_title, raw_output + "\n\n--- RETRY OUTPUT ---\n" + raw_retry_output

    return fallback_title_from_reference(reference), raw_output + "\n\n--- RETRY OUTPUT ---\n" + raw_retry_output


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


def build_reading_plan(references, output_log_path, raw_ollama_path):
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
            title, raw_ollama_output = generate_passage_title(reference, text)

            days.append(render_day(index, reference, title))

            record = {
                "day": index,
                "reference": reference,
                "title": title,
                "text": text,
            }

            raw_record = {
                "day": index,
                "reference": reference,
                "cleaned_title": title,
                "raw_ollama_output": raw_ollama_output,
            }

            title_records.append(record)
            append_jsonl(output_log_path, record)
            append_jsonl(raw_ollama_path, raw_record)

            print(f"  Title: {title}")

        except Exception as e:
            fallback_title = fallback_title_from_reference(reference)
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
        raw_ollama_path = input_path.with_name(f"{input_path.stem}_reading_plan_raw_ollama.jsonl")

        reset_file(output_log_path)
        reset_file(raw_ollama_path)

        markdown, title_records, errors = build_reading_plan(
            references,
            output_log_path,
            raw_ollama_path,
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
        print(f"Raw Ollama output written to: {raw_ollama_path}")

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
