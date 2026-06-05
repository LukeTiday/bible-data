import json
import re
from pathlib import Path
from collections import defaultdict


ROOT = Path(__file__).parent

TOP_REFS_PATH = ROOT / "01_verses_counted_and_sorted.json"
VERSES_PER_CHAPTER_PATH = ROOT / "verses_per_chapter.json"
OUTPUT_PATH = ROOT / "02_chapter_reference_rankings.json"


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


def main():
    top_refs = load_json(TOP_REFS_PATH)
    verses_per_chapter = load_json(VERSES_PER_CHAPTER_PATH)

    verse_count_lookup = build_verse_count_lookup(verses_per_chapter)

    chapter_reference_counts = defaultdict(int)

    # Sum references by chapter
    for item in top_refs:
        verse_ref = item["verse"]
        count = int(item["count"])

        book, chapter, verse = parse_verse_ref(verse_ref)

        chapter_key = (book, chapter)
        chapter_reference_counts[chapter_key] += count

    rankings = []

    for (book, chapter), total_references in chapter_reference_counts.items():
        verse_count = verse_count_lookup.get((book, chapter))

        if verse_count is None:
            raise KeyError(
                f"No verse count found for {book} {chapter}. "
                "Check book naming between the two JSON files."
            )

        references_per_verse = total_references / verse_count

        rankings.append(
            {
                "chapter": f"{book} {chapter}",
                "book": book,
                "chapter_number": chapter,
                "total_references": total_references,
                "verse_count": verse_count,
                "references_per_verse": references_per_verse,
            }
        )

    # Sort from most referenced per verse to least
    rankings.sort(
        key=lambda item: item["references_per_verse"],
        reverse=True,
    )

    # Add rank numbers after sorting
    for i, item in enumerate(rankings, start=1):
        item["rank"] = i

    save_json(OUTPUT_PATH, rankings)

    print(f"Saved ranking to: {OUTPUT_PATH}")
    print(f"Chapters ranked: {len(rankings)}")
    print()

    print("Top 20 chapters by references per verse:")
    for item in rankings[:20]:
        print(
            f"{item['rank']:>3}. "
            f"{item['chapter']:<20} "
            f"{item['references_per_verse']:.2f} refs/verse "
            f"({item['total_references']} refs / {item['verse_count']} verses)"
        )


if __name__ == "__main__":
    main()