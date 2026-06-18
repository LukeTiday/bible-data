from pathlib import Path
import csv
import json
import re
from collections import defaultdict

# -----------------------------
# Config
# -----------------------------

INPUT_PATH = Path("tskxref.txt")
OUTPUT_PATH = Path("verse_incoming_reference_counts.json")

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


def make_reference(book_key: int, chapter: int, verse: int) -> str:
    return f"{BOOKS[book_key]} {chapter}:{verse}"


def parse_reference_list(reference_list: str) -> list[str]:
    if not reference_list:
        return []

    return [
        ref.strip().lower()
        for ref in reference_list.split(";")
        if ref.strip()
    ]


def parse_target_reference(ref: str):
    """
    Parses refs like:
        ge 10:6
        ge 11:1-9
        lu 3:35,36

    Expands simple same-chapter ranges.
    """

    match = re.match(r"^([1-3]?[a-z]+)\s+(\d+):(.+)$", ref.strip().lower())
    if not match:
        return []

    abbrev, chapter_raw, verse_part = match.groups()

    if abbrev not in ABBREV_TO_BOOK_KEY:
        return []

    book_key = ABBREV_TO_BOOK_KEY[abbrev]
    chapter = int(chapter_raw)

    targets = []

    for piece in verse_part.split(","):
        piece = piece.strip()

        if "-" in piece:
            start_raw, end_raw = piece.split("-", 1)

            try:
                start = int(start_raw)
                end = int(end_raw)
            except ValueError:
                continue

            if end >= start:
                for verse in range(start, end + 1):
                    targets.append((book_key, chapter, verse))

        else:
            try:
                verse = int(piece)
            except ValueError:
                continue

            targets.append((book_key, chapter, verse))

    return targets


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Could not find input file: {INPUT_PATH}")

    incoming_counts = defaultdict(int)

    with INPUT_PATH.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter="\t")

        for row in reader:
            if len(row) != 6:
                continue

            _, _, _, _, _, reference_list = row

            refs = parse_reference_list(reference_list)

            for raw_ref in refs:
                target_keys = parse_target_reference(raw_ref)

                for target_key in target_keys:
                    incoming_counts[target_key] += 1

    ranked_rows = []

    for (book_key, chapter, verse), count in incoming_counts.items():
        ranked_rows.append({
            "verse": make_reference(book_key, chapter, verse),
            "reference_count": count,
        })

    ranked_rows.sort(
        key=lambda row: row["reference_count"],
        reverse=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(ranked_rows, f, ensure_ascii=False, indent=2)

    print("Done.")
    print(f"Verses with incoming references: {len(ranked_rows)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()