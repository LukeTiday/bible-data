from pathlib import Path
import csv
import json
import re
from collections import defaultdict

# -----------------------------
# Config
# -----------------------------

INPUT_PATH = Path("tskxref.txt")
VERSE_COUNTS_PATH = Path(
    r"C:\git_repos\bible-data\ReferenceDatasets\verses_per_chapter.json"
)
OUTPUT_PATH = Path("chapter_incoming_reference_counts_normalized.json")

BOOKS = {
    1: "Genesis",
    2: "Exodus",
    3: "Leviticus",
    4: "Numbers",
    5: "Deuteronomy",
    6: "Joshua",
    7: "Judges",
    8: "Ruth",
    9: "1 Samuel",
    10: "2 Samuel",
    11: "1 Kings",
    12: "2 Kings",
    13: "1 Chronicles",
    14: "2 Chronicles",
    15: "Ezra",
    16: "Nehemiah",
    17: "Esther",
    18: "Job",
    19: "Psalms",
    20: "Proverbs",
    21: "Ecclesiastes",
    22: "Song of Solomon",
    23: "Isaiah",
    24: "Jeremiah",
    25: "Lamentations",
    26: "Ezekiel",
    27: "Daniel",
    28: "Hosea",
    29: "Joel",
    30: "Amos",
    31: "Obadiah",
    32: "Jonah",
    33: "Micah",
    34: "Nahum",
    35: "Habakkuk",
    36: "Zephaniah",
    37: "Haggai",
    38: "Zechariah",
    39: "Malachi",
    40: "Matthew",
    41: "Mark",
    42: "Luke",
    43: "John",
    44: "Acts",
    45: "Romans",
    46: "1 Corinthians",
    47: "2 Corinthians",
    48: "Galatians",
    49: "Ephesians",
    50: "Philippians",
    51: "Colossians",
    52: "1 Thessalonians",
    53: "2 Thessalonians",
    54: "1 Timothy",
    55: "2 Timothy",
    56: "Titus",
    57: "Philemon",
    58: "Hebrews",
    59: "James",
    60: "1 Peter",
    61: "2 Peter",
    62: "1 John",
    63: "2 John",
    64: "3 John",
    65: "Jude",
    66: "Revelation",
}

ABBREV_TO_BOOK_KEY = {
    "ge": 1,
    "ex": 2,
    "le": 3,
    "nu": 4,
    "de": 5,
    "jos": 6,
    "jud": 7,
    "ru": 8,
    "1sa": 9,
    "2sa": 10,
    "1ki": 11,
    "2ki": 12,
    "1ch": 13,
    "2ch": 14,
    "ezr": 15,
    "ne": 16,
    "es": 17,
    "job": 18,
    "ps": 19,
    "pr": 20,
    "ec": 21,
    "so": 22,
    "isa": 23,
    "jer": 24,
    "la": 25,
    "eze": 26,
    "da": 27,
    "ho": 28,
    "joe": 29,
    "am": 30,
    "ob": 31,
    "jon": 32,
    "mic": 33,
    "na": 34,
    "hab": 35,
    "zep": 36,
    "hag": 37,
    "zec": 38,
    "mal": 39,
    "mt": 40,
    "mr": 41,
    "lu": 42,
    "joh": 43,
    "ac": 44,
    "ro": 45,
    "1co": 46,
    "2co": 47,
    "ga": 48,
    "eph": 49,
    "php": 50,
    "col": 51,
    "1th": 52,
    "2th": 53,
    "1ti": 54,
    "2ti": 55,
    "tit": 56,
    "phm": 57,
    "heb": 58,
    "jas": 59,
    "1pe": 60,
    "2pe": 61,
    "1jo": 62,
    "2jo": 63,
    "3jo": 64,
    "jude": 65,
    "re": 66,
}


def make_chapter_reference(book_key: int, chapter: int) -> str:
    return f"{BOOKS[book_key]} {chapter}"


def parse_reference_list(reference_list: str) -> list[str]:
    if not reference_list:
        return []

    return [
        ref.strip().lower()
        for ref in reference_list.split(";")
        if ref.strip()
    ]


def parse_target_chapter(ref: str):
    """
    Parses refs like:
        ge 10:6
        ge 11:1-9
        lu 3:35,36

    Returns:
        (book_key, chapter)

    Important:
        ge 11:1-9 counts as ONE reference to Genesis 11.
    """

    match = re.match(r"^([1-3]?[a-z]+)\s+(\d+):", ref.strip().lower())
    if not match:
        return None

    abbrev, chapter_raw = match.groups()

    if abbrev not in ABBREV_TO_BOOK_KEY:
        return None

    return ABBREV_TO_BOOK_KEY[abbrev], int(chapter_raw)


def load_verse_counts(path: Path) -> dict[tuple[int, int], int]:
    """
    Loads verses_per_chapter.json shaped like:

    [
        {
            "abbr": "Gen",
            "book": "Genesis",
            "chapters": [
                {
                    "chapter": "1",
                    "verses": "31"
                }
            ]
        }
    ]

    Returns:
        {
            (book_key, chapter): verse_count
        }
    """

    if not path.exists():
        raise FileNotFoundError(f"Could not find verse counts file: {path}")

    book_name_to_key = {
        book_name: book_key
        for book_key, book_name in BOOKS.items()
    }

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    verse_counts = {}

    for book_entry in data:
        book_name = book_entry["book"]

        if book_name not in book_name_to_key:
            print(f"Warning: unknown book in verse counts file: {book_name}")
            continue

        book_key = book_name_to_key[book_name]

        for chapter_entry in book_entry["chapters"]:
            chapter = int(chapter_entry["chapter"])
            verse_count = int(chapter_entry["verses"])

            verse_counts[(book_key, chapter)] = verse_count

    return verse_counts


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Could not find input file: {INPUT_PATH}")

    verse_counts = load_verse_counts(VERSE_COUNTS_PATH)

    chapter_incoming_counts = defaultdict(int)

    with INPUT_PATH.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter="\t")

        for row in reader:
            if len(row) != 6:
                continue

            _, _, _, _, _, reference_list = row

            refs = parse_reference_list(reference_list)

            for raw_ref in refs:
                chapter_key = parse_target_chapter(raw_ref)

                if chapter_key is None:
                    continue

                chapter_incoming_counts[chapter_key] += 1

    ranked_rows = []
    missing_verse_counts = []

    for (book_key, chapter), reference_count in chapter_incoming_counts.items():
        verse_count = verse_counts.get((book_key, chapter))

        if verse_count is None:
            missing_verse_counts.append(make_chapter_reference(book_key, chapter))
            continue

        references_per_verse = reference_count / verse_count

        ranked_rows.append({
            "chapter": make_chapter_reference(book_key, chapter),
            "reference_count": reference_count,
            "verse_count": verse_count,
            "references_per_verse": references_per_verse,
        })

    ranked_rows.sort(
        key=lambda row: row["references_per_verse"],
        reverse=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(ranked_rows, f, ensure_ascii=False, indent=2)

    print("Done.")
    print(f"Chapters ranked: {len(ranked_rows)}")
    print(f"Missing verse counts: {len(missing_verse_counts)}")
    print(f"Saved to: {OUTPUT_PATH}")

    if missing_verse_counts:
        print("\nMissing verse count chapters:")
        for chapter in missing_verse_counts[:50]:
            print(f"  - {chapter}")


if __name__ == "__main__":
    main()