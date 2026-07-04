import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


# ============================================================
# Config
# ============================================================

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
# Reference parsing
# ============================================================

SINGLE_REF_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)$"
)

SAME_CHAPTER_RANGE_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)-(\d+)$"
)


def expected_verse_count(reference):
    """
    Returns expected number of verses for simple refs:
      Zechariah 1:3      -> 1
      Jeremiah 3:12-18   -> 7

    Returns None for complex refs:
      John 3:16-4:2
      John 3:16-John 4:2
      Psalm 1
    """

    reference = reference.strip()

    single_match = SINGLE_REF_RE.match(reference)
    if single_match:
        return 1

    range_match = SAME_CHAPTER_RANGE_RE.match(reference)
    if range_match:
        start_verse = int(range_match.group(3))
        end_verse = int(range_match.group(4))

        if end_verse < start_verse:
            return None

        return end_verse - start_verse + 1

    return None


# ============================================================
# JSON helpers
# ============================================================

def load_json_list(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in: {path}")

    refs = []

    for item in data:
        if isinstance(item, str) and item.strip():
            refs.append(item.strip())

    return refs


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# Verse helpers
# ============================================================

def get_reference_text(reference):
    """
    Fetches verse text for a reference or range.

    Counts text only, not reference labels.

    Defensive behavior:
    - Single verse refs only count the first returned verse.
    - Same-chapter ranges only count the expected number of verses.
    - Complex refs use whatever VerseFetch returns.
    """

    verses = list(iter_verses(reference))

    if not verses:
        raise ValueError(f"No verses found for reference: {reference}")

    expected_count = expected_verse_count(reference)

    if expected_count is not None:
        verses = verses[:expected_count]

    texts = []

    for verse in verses:
        text = verse.get("text", "").strip()

        if text:
            texts.append(text)

    if not texts:
        raise ValueError(f"No verse text found for reference: {reference}")

    return " ".join(texts).strip()


def count_ascii_chars(text):
    """
    Counts only ASCII characters.

    Included:
      normal letters, numbers, spaces, regular punctuation

    Excluded:
      curly quotes, em dashes, special unicode punctuation, etc.
    """

    return sum(1 for char in text if ord(char) < 128)


def count_non_ascii_chars(text):
    return sum(1 for char in text if ord(char) >= 128)


def count_total_chars(text):
    return len(text)


# ============================================================
# Main processing
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


def build_sorted_records(input_path):
    references = load_json_list(input_path)

    records = []
    errors = []

    total = len(references)

    print(f"Using VerseFetch from: {VerseFetch.__file__}")
    print(f"Loaded {total} references.")
    print(f"Input: {input_path}")
    print()

    for index, reference in enumerate(references, start=1):
        print(f"[{index}/{total}] Counting {reference}...")

        try:
            text = get_reference_text(reference)

            ascii_count = count_ascii_chars(text)
            non_ascii_count = count_non_ascii_chars(text)
            total_char_count = count_total_chars(text)

            records.append({
                "reference": reference,
                "ascii_char_count": ascii_count,
                "non_ascii_char_count": non_ascii_count,
                "total_char_count": total_char_count,
                "text": text,
            })

            print(f"  ASCII chars: {ascii_count}")

        except Exception as e:
            error_record = {
                "reference": reference,
                "error": str(e),
            }

            errors.append(error_record)
            print(f"  ERROR: {e}")

    records.sort(
        key=lambda item: item["ascii_char_count"],
        reverse=True,
    )

    return records, errors


def main():
    input_path = choose_json_file()

    if input_path is None:
        print("No file selected.")
        return

    try:
        records, errors = build_sorted_records(input_path)

        sorted_refs = [record["reference"] for record in records]

        sorted_refs_path = input_path.with_name(
            f"{input_path.stem}_sorted_by_ascii_length.json"
        )

        detailed_counts_path = input_path.with_name(
            f"{input_path.stem}_ascii_counts_sorted.json"
        )

        errors_path = input_path.with_name(
            f"{input_path.stem}_ascii_count_errors.json"
        )

        save_json(sorted_refs_path, sorted_refs)
        save_json(detailed_counts_path, records)

        if errors:
            save_json(errors_path, errors)

        print()
        print("Done.")
        print(f"Sorted references written to: {sorted_refs_path}")
        print(f"Detailed counts written to: {detailed_counts_path}")

        if errors:
            print(f"Errors written to: {errors_path}")
            print(f"Error count: {len(errors)}")

        print(f"Successfully counted: {len(records)}")

        messagebox.showinfo(
            "Done",
            "Verse references sorted by ASCII character count.\n\n"
            f"Sorted refs:\n{sorted_refs_path}\n\n"
            f"Detailed counts:\n{detailed_counts_path}"
        )

    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise


if __name__ == "__main__":
    main()