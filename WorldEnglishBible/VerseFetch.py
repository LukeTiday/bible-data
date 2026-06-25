import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any


WEB_JSON_PATH = Path(r"C:\git_repos\bible-data\WorldEnglishBible\web_plaintext.json")


BOOK_ALIASES = {
    "gen": "Genesis",
    "ge": "Genesis",
    "ex": "Exodus",
    "exo": "Exodus",
    "lev": "Leviticus",
    "num": "Numbers",
    "deut": "Deuteronomy",
    "dt": "Deuteronomy",

    "josh": "Joshua",
    "judg": "Judges",
    "rut": "Ruth",

    "1 sam": "1 Samuel",
    "1sam": "1 Samuel",
    "1 samuel": "1 Samuel",
    "i samuel": "1 Samuel",

    "2 sam": "2 Samuel",
    "2sam": "2 Samuel",
    "2 samuel": "2 Samuel",
    "ii samuel": "2 Samuel",

    "1 kings": "1 Kings",
    "1kgs": "1 Kings",
    "1 kgs": "1 Kings",
    "i kings": "1 Kings",

    "2 kings": "2 Kings",
    "2kgs": "2 Kings",
    "2 kgs": "2 Kings",
    "ii kings": "2 Kings",

    "1 chron": "1 Chronicles",
    "1chron": "1 Chronicles",
    "1 chronicles": "1 Chronicles",
    "i chronicles": "1 Chronicles",

    "2 chron": "2 Chronicles",
    "2chron": "2 Chronicles",
    "2 chronicles": "2 Chronicles",
    "ii chronicles": "2 Chronicles",

    "ezra": "Ezra",
    "neh": "Nehemiah",
    "esth": "Esther",

    "job": "Job",
    "ps": "Psalms",
    "psalm": "Psalms",
    "psalms": "Psalms",
    "prov": "Proverbs",
    "eccl": "Ecclesiastes",
    "ecc": "Ecclesiastes",
    "song": "Song of Solomon",
    "song of songs": "Song of Solomon",
    "sos": "Song of Solomon",

    "isa": "Isaiah",
    "jer": "Jeremiah",
    "lam": "Lamentations",
    "ezek": "Ezekiel",
    "eze": "Ezekiel",
    "dan": "Daniel",

    "hos": "Hosea",
    "obad": "Obadiah",
    "jon": "Jonah",
    "mic": "Micah",
    "nah": "Nahum",
    "hab": "Habakkuk",
    "zeph": "Zephaniah",
    "hag": "Haggai",
    "zech": "Zechariah",
    "mal": "Malachi",

    "matt": "Matthew",
    "mt": "Matthew",
    "mk": "Mark",
    "mrk": "Mark",
    "lk": "Luke",
    "jn": "John",
    "jhn": "John",

    "acts": "Acts",
    "rom": "Romans",

    "1 cor": "1 Corinthians",
    "1cor": "1 Corinthians",
    "1 corinthians": "1 Corinthians",
    "i corinthians": "1 Corinthians",

    "2 cor": "2 Corinthians",
    "2cor": "2 Corinthians",
    "2 corinthians": "2 Corinthians",
    "ii corinthians": "2 Corinthians",

    "gal": "Galatians",
    "eph": "Ephesians",
    "phil": "Philippians",
    "php": "Philippians",
    "col": "Colossians",

    "1 thess": "1 Thessalonians",
    "1thess": "1 Thessalonians",
    "1 thessalonians": "1 Thessalonians",
    "i thessalonians": "1 Thessalonians",

    "2 thess": "2 Thessalonians",
    "2thess": "2 Thessalonians",
    "2 thessalonians": "2 Thessalonians",
    "ii thessalonians": "2 Thessalonians",

    "1 tim": "1 Timothy",
    "1tim": "1 Timothy",
    "1 timothy": "1 Timothy",
    "i timothy": "1 Timothy",

    "2 tim": "2 Timothy",
    "2tim": "2 Timothy",
    "2 timothy": "2 Timothy",
    "ii timothy": "2 Timothy",

    "tit": "Titus",
    "philem": "Philemon",
    "phm": "Philemon",
    "heb": "Hebrews",
    "jas": "James",
    "jam": "James",

    "1 pet": "1 Peter",
    "1pet": "1 Peter",
    "1 peter": "1 Peter",
    "i peter": "1 Peter",

    "2 pet": "2 Peter",
    "2pet": "2 Peter",
    "2 peter": "2 Peter",
    "ii peter": "2 Peter",

    "1 jn": "1 John",
    "1jn": "1 John",
    "1 john": "1 John",
    "i john": "1 John",

    "2 jn": "2 John",
    "2jn": "2 John",
    "2 john": "2 John",
    "ii john": "2 John",

    "3 jn": "3 John",
    "3jn": "3 John",
    "3 john": "3 John",
    "iii john": "3 John",

    "jude": "Jude",
    "rev": "Revelation",
    "re": "Revelation",
}


_bible_cache = None


def load_bible(path=WEB_JSON_PATH):
    global _bible_cache

    if _bible_cache is None:
        with open(path, "r", encoding="utf-8") as f:
            _bible_cache = json.load(f)

    return _bible_cache


def normalize_book_name(book_raw, bible):
    cleaned = re.sub(r"\s+", " ", book_raw.strip()).lower()

    if cleaned in BOOK_ALIASES:
        return BOOK_ALIASES[cleaned]

    for book in bible["books"].keys():
        if cleaned == book.lower():
            return book

    compact = cleaned.replace(" ", "")
    for book in bible["books"].keys():
        if compact == book.lower().replace(" ", ""):
            return book

    raise ValueError("Unknown book name: {}".format(book_raw))


def parse_reference(reference, bible):
    """
    Supports:
      John 3
      John 3:16
      John 3:16-18
      John 3:16-4:2
      John 3:16-John 4:2
    """

    ref = re.sub(r"\s+", " ", reference.strip())

    pattern = re.compile(
        r"^(?P<book>[1-3]?\s?[A-Za-z ]+?)\s+"
        r"(?P<start_chapter>\d+)"
        r"(?::(?P<start_verse>\d+))?"
        r"(?:\s*-\s*"
        r"(?:(?P<end_book>[1-3]?\s?[A-Za-z ]+?)\s+)?"
        r"(?:(?P<end_chapter>\d+):)?"
        r"(?P<end_verse>\d+)?"
        r")?$"
    )

    match = pattern.match(ref)

    if not match:
        raise ValueError("Could not parse reference: {}".format(reference))

    parts = match.groupdict()

    start_book = normalize_book_name(parts["book"], bible)
    end_book = normalize_book_name(parts["end_book"], bible) if parts["end_book"] else start_book

    start_chapter = int(parts["start_chapter"])
    start_verse = int(parts["start_verse"]) if parts["start_verse"] else None

    if parts["end_chapter"]:
        end_chapter = int(parts["end_chapter"])
    else:
        end_chapter = start_chapter

    end_verse = int(parts["end_verse"]) if parts["end_verse"] else None

    return {
        "start_book": start_book,
        "start_chapter": start_chapter,
        "start_verse": start_verse,
        "end_book": end_book,
        "end_chapter": end_chapter,
        "end_verse": end_verse,
    }


def get_book_index(book, bible):
    return bible["book_order"].index(book)


def iter_verses(reference, bible=None):
    bible = bible or load_bible()
    parsed = parse_reference(reference, bible)

    start_book = parsed["start_book"]
    end_book = parsed["end_book"]

    start_book_index = get_book_index(start_book, bible)
    end_book_index = get_book_index(end_book, bible)

    if end_book_index < start_book_index:
        raise ValueError("End book comes before start book: {}".format(reference))

    for book_index in range(start_book_index, end_book_index + 1):
        book_name = bible["book_order"][book_index]

        if book_name not in bible["books"]:
            continue

        book_data = bible["books"][book_name]

        chapter_nums = sorted(
            [int(ch) for ch in book_data["chapters"].keys()]
        )

        for chapter_num in chapter_nums:
            if book_name == start_book and chapter_num < parsed["start_chapter"]:
                continue

            if book_name == end_book and chapter_num > parsed["end_chapter"]:
                continue

            chapter_key = str(chapter_num)
            chapter_data = book_data["chapters"][chapter_key]

            verse_nums = sorted(
                [int(v) for v in chapter_data["verses"].keys()]
            )

            for verse_num in verse_nums:
                if (
                    book_name == start_book
                    and chapter_num == parsed["start_chapter"]
                    and parsed["start_verse"] is not None
                    and verse_num < parsed["start_verse"]
                ):
                    continue

                if (
                    book_name == end_book
                    and chapter_num == parsed["end_chapter"]
                    and parsed["end_verse"] is not None
                    and verse_num > parsed["end_verse"]
                ):
                    continue

                verse_key = str(verse_num)

                yield {
                    "book": book_name,
                    "chapter": chapter_num,
                    "verse": verse_num,
                    "text": chapter_data["verses"][verse_key],
                }


def get_passage(reference, include_reference=True, include_verse_numbers=True, bible=None):
    verses = list(iter_verses(reference, bible=bible))

    if not verses:
        raise ValueError("No verses found for reference: {}".format(reference))

    chunks = []

    if include_reference:
        chunks.append(reference.strip())

    current_book = None
    current_chapter = None
    line_parts = []

    for item in verses:
        book = item["book"]
        chapter = item["chapter"]
        verse = item["verse"]
        text = item["text"]

        if book != current_book or chapter != current_chapter:
            if line_parts:
                chunks.append(" ".join(line_parts))
                line_parts = []

            current_book = book
            current_chapter = chapter

            if include_reference:
                chunks.append("\n{} {}".format(book, chapter))

        if include_verse_numbers:
            line_parts.append("{} {}".format(verse, text))
        else:
            line_parts.append(text)

    if line_parts:
        chunks.append(" ".join(line_parts))

    return "\n".join(chunks).strip()


def get_passage_records(reference, bible=None):
    """
    Useful when you want structured verse data instead of plaintext.
    """
    return list(iter_verses(reference, bible=bible))


if __name__ == "__main__":
    print(get_passage("John 3:16-18"))
    print()
    print(get_passage("Psalm 1"))
    print()
    print(get_passage("John 3:16-4:2"))