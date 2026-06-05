import json
import re
from pathlib import Path


ROOT = Path(__file__).parent

TOP_REFS_PATH = ROOT / "01_verses_counted_and_sorted.json"
VERSES_PER_CHAPTER_PATH = ROOT / "verses_per_chapter.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_book_from_verse_ref(verse_ref):
    """
    Expected examples:
      "John 1_1"
      "1 Corinthians 13_4"
      "Song of Solomon 2_1"

    Returns:
      "John"
      "1 Corinthians"
      "Song of Solomon"
    """

    # Match everything before the final chapter_verse pattern
    match = re.match(r"^(.+?)\s+\d+_\d+$", verse_ref)

    if not match:
        raise ValueError(f"Could not parse verse reference: {verse_ref}")

    return match.group(1).strip()


def main():
    top_refs = load_json(TOP_REFS_PATH)
    verses_per_chapter = load_json(VERSES_PER_CHAPTER_PATH)

    books_in_top_refs = set()
    books_in_verses_file = set()

    # Books from top20000.json
    for item in top_refs:
        verse_ref = item["verse"]
        book = extract_book_from_verse_ref(verse_ref)
        books_in_top_refs.add(book)

    # Books from verses_per_chapter.json
    for book_data in verses_per_chapter:
        books_in_verses_file.add(book_data["book"].strip())

    only_in_top_refs = sorted(books_in_top_refs - books_in_verses_file)
    only_in_verses_file = sorted(books_in_verses_file - books_in_top_refs)

    print("Books found in top20000.json:")
    print(len(books_in_top_refs))
    print()

    print("Books found in verses_per_chapter.json:")
    print(len(books_in_verses_file))
    print()

    print("Books in top20000.json but NOT in verses_per_chapter.json:")
    if only_in_top_refs:
        for book in only_in_top_refs:
            print(f"  - {book}")
    else:
        print("  None")
    print()

    print("Books in verses_per_chapter.json but NOT in top20000.json:")
    if only_in_verses_file:
        for book in only_in_verses_file:
            print(f"  - {book}")
    else:
        print("  None")


if __name__ == "__main__":
    main()