import json
import re
from pathlib import Path
from collections import defaultdict


ROOT = Path(__file__).parent

TOP_REFS_PATH = ROOT / "01_verses_counted_and_sorted.json"
VERSES_PER_CHAPTER_PATH = ROOT / "verses_per_chapter.json"
OUTPUT_PATH = ROOT / "03_chapter_reference_rankings_by_book.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def parse_verse_ref(verse_ref):
    """
    Expected examples:
      "John 1_1"
      "1 Corinthians 13_4"
      "Song of Solomon 2_1"

    Returns:
      book, chapter, verse
    """

    match = re.match(r"^(.+?)\s+(\d+)_(\d+)$", verse_ref)

    if not match:
        raise ValueError(f"Could not parse verse reference: {verse_ref}")

    book = match.group(1).strip()
    chapter = int(match.group(2))
    verse = int(match.group(3))

    return book, chapter, verse


def build_verse_count_lookup(verses_per_chapter):
    """
    Builds lookup like:
      {
        ("John", 1): 51,
        ("Genesis", 1): 31
      }
    """

    lookup = {}

    for book_data in verses_per_chapter:
        book = book_data["book"].strip()

        for chapter_data in book_data["chapters"]:
            chapter = int(chapter_data["chapter"])
            verses = int(chapter_data["verses"])

            lookup[(book, chapter)] = verses

    return lookup


def build_book_order_lookup(verses_per_chapter):
    """
    Preserves canonical book order from verses_per_chapter.json.
    """

    return {
        book_data["book"].strip(): index
        for index, book_data in enumerate(verses_per_chapter)
    }


def main():
    top_refs = load_json(TOP_REFS_PATH)
    verses_per_chapter = load_json(VERSES_PER_CHAPTER_PATH)

    verse_count_lookup = build_verse_count_lookup(verses_per_chapter)
    book_order_lookup = build_book_order_lookup(verses_per_chapter)

    chapter_reference_counts = defaultdict(int)

    # Sum references by chapter
    for item in top_refs:
        verse_ref = item["verse"]
        count = int(item["count"])

        book, chapter, verse = parse_verse_ref(verse_ref)

        chapter_key = (book, chapter)
        chapter_reference_counts[chapter_key] += count

    grouped_by_book = defaultdict(list)

    for (book, chapter), total_references in chapter_reference_counts.items():
        verse_count = verse_count_lookup.get((book, chapter))

        if verse_count is None:
            raise KeyError(
                f"No verse count found for {book} {chapter}. "
                "Check book naming between the two JSON files."
            )

        references_per_verse = total_references / verse_count

        grouped_by_book[book].append(
            {
                "chapter": f"{book} {chapter}",
                "book": book,
                "chapter_number": chapter,
                "total_references": total_references,
                "verse_count": verse_count,
                "references_per_verse": references_per_verse,
            }
        )

    output = []

    # Sort books in canonical order from verses_per_chapter.json
    sorted_books = sorted(
        grouped_by_book.keys(),
        key=lambda book: book_order_lookup.get(book, 9999),
    )

    for book in sorted_books:
        chapters = grouped_by_book[book]

        # Rank chapters within each book
        chapters.sort(
            key=lambda item: item["references_per_verse"],
            reverse=True,
        )

        for rank, chapter_data in enumerate(chapters, start=1):
            chapter_data["book_rank"] = rank

        book_total_references = sum(
            chapter["total_references"] for chapter in chapters
        )

        book_total_verses_represented = sum(
            chapter["verse_count"] for chapter in chapters
        )

        output.append(
            {
                "book": book,
                "total_references": book_total_references,
                "chapters_represented": len(chapters),
                "verses_in_represented_chapters": book_total_verses_represented,
                "chapters": chapters,
            }
        )

    save_json(OUTPUT_PATH, output)

    print(f"Saved grouped ranking to: {OUTPUT_PATH}")
    print(f"Books represented: {len(output)}")
    print()

    print("Top chapter in each book:")
    for book_data in output:
        top_chapter = book_data["chapters"][0]

        print(
            f"{book_data['book']:<20} "
            f"{top_chapter['chapter']:<20} "
            f"{top_chapter['references_per_verse']:.2f} refs/verse "
            f"({top_chapter['total_references']} refs / "
            f"{top_chapter['verse_count']} verses)"
        )


if __name__ == "__main__":
    main()