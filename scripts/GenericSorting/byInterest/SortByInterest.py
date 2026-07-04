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

# Your ranked per-verse reference counts file.
REFERENCE_COUNTS_PATH = Path(
    r"C:\git_repos\bible-data\BibleVsRankedByReference\01_verses_counted_and_sorted.json"
)

# If a verse is not present in REFERENCE_COUNTS_PATH, treat it as 0 references.
# This matters because your ranked file may only include verses that were referenced at least once.
MISSING_VERSE_COUNT_VALUE = 0

POSSIBLE_VERSEFETCH_DIRS = [
    Path(r"C:\git_repos\bible_data\WorldEnglishBible"),
    Path(r"C:\git_repos\bible-data\WorldEnglishBible"),
    SCRIPT_DIR.parent / "WorldEnglishBible",
]

# Add parent-safe guesses like:
#   C:\git_repos\bible-data\scripts\GenericSorting\byInterest
#   -> C:\git_repos\bible-data\WorldEnglishBible
for parent in SCRIPT_DIR.parents:
    POSSIBLE_VERSEFETCH_DIRS.append(parent / "WorldEnglishBible")

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
# Regexes / parsing
# ============================================================

SINGLE_REF_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)$"
)

SAME_CHAPTER_RANGE_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)-(\d+)$"
)

FULL_CHAPTER_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+)$"
)

VERSE_ID_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+)[:_](\d+)$"
)


BOOK_ALIASES = {
    # Common WEB / reference-list differences.
    "psalm": "psalms",
    "psalms": "psalms",
    "ps": "psalms",
    "psa": "psalms",

    "song": "song of solomon",
    "song of songs": "song of solomon",
    "song of solomon": "song of solomon",
    "canticles": "song of solomon",

    # Common abbreviations, in case VerseFetch emits shorter names.
    "gen": "genesis",
    "exo": "exodus",
    "exod": "exodus",
    "lev": "leviticus",
    "num": "numbers",
    "deut": "deuteronomy",
    "jos": "joshua",
    "josh": "joshua",
    "judg": "judges",
    "rth": "ruth",
    "1 sam": "1 samuel",
    "2 sam": "2 samuel",
    "1 kgs": "1 kings",
    "2 kgs": "2 kings",
    "1 chr": "1 chronicles",
    "2 chr": "2 chronicles",
    "neh": "nehemiah",
    "esth": "esther",
    "eccl": "ecclesiastes",
    "isa": "isaiah",
    "jer": "jeremiah",
    "lam": "lamentations",
    "ezek": "ezekiel",
    "dan": "daniel",
    "hos": "hosea",
    "obad": "obadiah",
    "jon": "jonah",
    "mic": "micah",
    "nah": "nahum",
    "hab": "habakkuk",
    "zeph": "zephaniah",
    "hag": "haggai",
    "zech": "zechariah",
    "mal": "malachi",
    "matt": "matthew",
    "mk": "mark",
    "jn": "john",
    "rom": "romans",
    "1 cor": "1 corinthians",
    "2 cor": "2 corinthians",
    "gal": "galatians",
    "eph": "ephesians",
    "phil": "philippians",
    "col": "colossians",
    "1 thess": "1 thessalonians",
    "2 thess": "2 thessalonians",
    "1 tim": "1 timothy",
    "2 tim": "2 timothy",
    "heb": "hebrews",
    "jas": "james",
    "jam": "james",
    "1 pet": "1 peter",
    "2 pet": "2 peter",
    "1 jn": "1 john",
    "2 jn": "2 john",
    "3 jn": "3 john",
    "jude": "jude",
    "rev": "revelation",
}


def normalize_book_name(book):
    book = str(book).strip().lower()
    book = book.replace(".", "")
    book = re.sub(r"\s+", " ", book)

    # Normalize things like "1John" -> "1 john".
    book = re.sub(r"^([1-3])\s*([a-z])", r"\1 \2", book)
    book = re.sub(r"\s+", " ", book).strip()

    return BOOK_ALIASES.get(book, book)


def make_count_key(book, chapter, verse):
    return (
        normalize_book_name(book),
        int(chapter),
        int(verse),
    )


def format_verse_id(book, chapter, verse):
    """
    Output format matches your reference-count JSON style:
      John 1_1
    """
    return f"{str(book).strip()} {int(chapter)}_{int(verse)}"


def parse_verse_id(value):
    """
    Parses values like:
      John 1_1
      John 1:1
    """
    match = VERSE_ID_RE.match(str(value).strip())
    if not match:
        return None

    return make_count_key(
        match.group(1),
        match.group(2),
        match.group(3),
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


def fallback_keys_from_reference(reference, returned_verse_count):
    """
    Builds verse keys from the original reference when VerseFetch records do not
    expose book/chapter/verse metadata.

    Handles:
      John 1:1
      John 1:1-5
      John 1

    Cross-chapter references depend on VerseFetch returning metadata.
    """
    reference = reference.strip()

    single_match = SINGLE_REF_RE.match(reference)
    if single_match:
        book = single_match.group(1)
        chapter = int(single_match.group(2))
        verse = int(single_match.group(3))
        return [make_count_key(book, chapter, verse)]

    same_chapter_match = SAME_CHAPTER_RANGE_RE.match(reference)
    if same_chapter_match:
        book = same_chapter_match.group(1)
        chapter = int(same_chapter_match.group(2))
        start_verse = int(same_chapter_match.group(3))
        end_verse = int(same_chapter_match.group(4))

        if end_verse < start_verse:
            return None

        return [
            make_count_key(book, chapter, verse)
            for verse in range(start_verse, end_verse + 1)
        ]

    full_chapter_match = FULL_CHAPTER_RE.match(reference)
    if full_chapter_match:
        book = full_chapter_match.group(1)
        chapter = int(full_chapter_match.group(2))

        return [
            make_count_key(book, chapter, verse_num)
            for verse_num in range(1, returned_verse_count + 1)
        ]

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
        elif isinstance(item, dict):
            # Allows input lists like {"reference": "John 1:1"} too.
            reference = item.get("reference") or item.get("ref")
            if isinstance(reference, str) and reference.strip():
                refs.append(reference.strip())

    return refs


def load_reference_count_map(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in reference count file: {path}")

    count_map = {}
    skipped = []

    for item in data:
        if not isinstance(item, dict):
            skipped.append({"item": item, "error": "Not an object"})
            continue

        verse_id = item.get("verse")
        count = item.get("count")

        key = parse_verse_id(verse_id)

        if key is None:
            skipped.append({"item": item, "error": "Could not parse verse id"})
            continue

        try:
            count_map[key] = int(count)
        except Exception:
            skipped.append({"item": item, "error": "Count is not an integer"})

    return count_map, skipped


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# VerseFetch helpers
# ============================================================


def first_value(record, keys):
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def verse_record_to_key(verse_record):
    """
    Tries to pull book/chapter/verse from whatever VerseFetch.iter_verses returns.

    Expected common shapes include:
      {"book": "John", "chapter": 1, "verse": 1, "text": "..."}
      {"book_name": "John", "chapter": 1, "verse_num": 1, "text": "..."}
      {"reference": "John 1:1", "text": "..."}
    """
    if not isinstance(verse_record, dict):
        return None

    # Direct reference label, if present.
    for ref_key in ["reference", "ref", "verse_reference", "id"]:
        ref_value = verse_record.get(ref_key)
        if isinstance(ref_value, str):
            parsed = parse_verse_id(ref_value)
            if parsed is not None:
                return parsed

    book = first_value(
        verse_record,
        ["book", "book_name", "bookName", "book_title", "bookTitle"],
    )
    chapter = first_value(
        verse_record,
        ["chapter", "chapter_num", "chapterNum", "chapter_number", "chapterNumber", "c"],
    )
    verse = first_value(
        verse_record,
        ["verse", "verse_num", "verseNum", "verse_number", "verseNumber", "v"],
    )

    # Some objects may use "verse" for a full string like "John 1_1".
    if book is None and isinstance(verse, str):
        parsed = parse_verse_id(verse)
        if parsed is not None:
            return parsed

    if book is None or chapter is None or verse is None:
        return None

    try:
        return make_count_key(book, chapter, verse)
    except Exception:
        return None


def get_verse_keys_for_reference(reference):
    """
    Expands a reference / range / full chapter into individual verse keys.
    """
    verses = list(iter_verses(reference))

    if not verses:
        raise ValueError(f"No verses found for reference: {reference}")

    expected_count = expected_verse_count(reference)

    if expected_count is not None:
        verses = verses[:expected_count]

    fallback_keys = fallback_keys_from_reference(reference, len(verses))

    keys = []

    for index, verse_record in enumerate(verses):
        key = verse_record_to_key(verse_record)

        if key is None and fallback_keys is not None and index < len(fallback_keys):
            key = fallback_keys[index]

        if key is None:
            raise ValueError(
                "Could not determine book/chapter/verse for one returned verse. "
                "This usually means the reference is cross-chapter and VerseFetch "
                "did not return metadata. Reference: "
                f"{reference}. Verse record: {verse_record}"
            )

        keys.append(key)

    return keys


# ============================================================
# Main processing
# ============================================================


def choose_json_file():
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        title="Choose JSON list of verse references / verse sets",
        filetypes=[
            ("JSON files", "*.json"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()

    if not path:
        return None

    return Path(path)


def build_sorted_records(input_path, reference_counts_path):
    references = load_json_list(input_path)
    reference_counts, skipped_count_records = load_reference_count_map(reference_counts_path)

    records = []
    errors = []

    total = len(references)

    print(f"Using VerseFetch from: {VerseFetch.__file__}")
    print(f"Loaded {total} references / verse sets.")
    print(f"Loaded {len(reference_counts)} verse reference counts.")
    print(f"Input: {input_path}")
    print(f"Reference counts: {reference_counts_path}")

    if skipped_count_records:
        print(f"Skipped malformed count records: {len(skipped_count_records)}")

    print()

    for index, reference in enumerate(references, start=1):
        print(f"[{index}/{total}] Scoring {reference}...")

        try:
            verse_keys = get_verse_keys_for_reference(reference)

            verse_records = []
            counts = []
            missing_count = 0

            for key in verse_keys:
                count_was_found = key in reference_counts
                count = reference_counts.get(key, MISSING_VERSE_COUNT_VALUE)
                counts.append(count)

                if not count_was_found:
                    missing_count += 1

                normalized_book, chapter, verse_num = key

                verse_records.append({
                    "verse": format_verse_id(normalized_book.title(), chapter, verse_num),
                    "count": count,
                    "count_was_found": count_was_found,
                })

            if not counts:
                raise ValueError(f"No verse counts produced for reference: {reference}")

            total_reference_count = sum(counts)
            verse_count = len(counts)
            average_reference_count = total_reference_count / verse_count

            records.append({
                "reference": reference,
                "average_reference_count_per_verse": average_reference_count,
                "total_reference_count": total_reference_count,
                "verse_count": verse_count,
                "missing_count_verses": missing_count,
                "verses": verse_records,
            })

            print(
                "  Avg refs/verse: "
                f"{average_reference_count:.4f} "
                f"({total_reference_count} refs / {verse_count} verses, "
                f"missing={missing_count})"
            )

        except Exception as e:
            error_record = {
                "reference": reference,
                "error": str(e),
            }

            errors.append(error_record)
            print(f"  ERROR: {e}")

    records.sort(
        key=lambda item: (
            item["average_reference_count_per_verse"],
            item["total_reference_count"],
            -item["verse_count"],
            item["reference"],
        ),
        reverse=True,
    )

    return records, errors, skipped_count_records


def main():
    input_path = choose_json_file()

    if input_path is None:
        print("No file selected.")
        return

    if not REFERENCE_COUNTS_PATH.exists():
        raise FileNotFoundError(
            "Could not find reference counts JSON:\n"
            f"{REFERENCE_COUNTS_PATH}"
        )

    try:
        records, errors, skipped_count_records = build_sorted_records(
            input_path,
            REFERENCE_COUNTS_PATH,
        )

        sorted_refs = [record["reference"] for record in records]

        sorted_refs_path = input_path.with_name(
            f"{input_path.stem}_sorted_by_average_reference_count.json"
        )

        detailed_counts_path = input_path.with_name(
            f"{input_path.stem}_reference_interest_scores_sorted.json"
        )

        errors_path = input_path.with_name(
            f"{input_path.stem}_reference_interest_errors.json"
        )

        skipped_counts_path = input_path.with_name(
            f"{input_path.stem}_malformed_reference_count_records.json"
        )

        save_json(sorted_refs_path, sorted_refs)
        save_json(detailed_counts_path, records)

        if errors:
            save_json(errors_path, errors)

        if skipped_count_records:
            save_json(skipped_counts_path, skipped_count_records)

        print()
        print("Done.")
        print(f"Sorted references written to: {sorted_refs_path}")
        print(f"Detailed scores written to: {detailed_counts_path}")

        if errors:
            print(f"Errors written to: {errors_path}")
            print(f"Error count: {len(errors)}")

        if skipped_count_records:
            print(f"Malformed count records written to: {skipped_counts_path}")
            print(f"Malformed count record count: {len(skipped_count_records)}")

        print(f"Successfully scored: {len(records)}")

        messagebox.showinfo(
            "Done",
            "Verse references sorted by average reference count per verse.\n\n"
            f"Sorted refs:\n{sorted_refs_path}\n\n"
            f"Detailed scores:\n{detailed_counts_path}"
        )

    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise


if __name__ == "__main__":
    main()
