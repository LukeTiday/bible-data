import json
import os
import re
from collections import defaultdict

import matplotlib.pyplot as plt


VALID_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
]


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file does not exist: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")


def parse_chapter_reference(chapter_ref):
    """
    Converts:
        John 3 -> ("John", 3)
        1 Corinthians 13 -> ("1 Corinthians", 13)
        Song of Solomon 2 -> ("Song of Solomon", 2)
    """
    parts = chapter_ref.rsplit(" ", 1)

    if len(parts) != 2:
        raise ValueError(f"Could not parse chapter reference: {chapter_ref}")

    book_name, chapter_number = parts
    return book_name, int(chapter_number)


def build_verses_lookup(verses_per_chapter_data):
    """
    Builds lookup like:
        verses_lookup["John"][3] = 36
        verses_lookup["Psalms"][119] = 176
    """
    verses_lookup = {}

    for book_entry in verses_per_chapter_data:
        book_name = book_entry["book"]
        verses_lookup[book_name] = {}

        for chapter_entry in book_entry["chapters"]:
            chapter_number = int(chapter_entry["chapter"])
            verse_count = int(chapter_entry["verses"])

            verses_lookup[book_name][chapter_number] = verse_count

    return verses_lookup


def group_and_normalize_chapters_by_book(chapter_counts, verses_lookup):
    grouped = defaultdict(list)

    for item in chapter_counts:
        chapter_ref = item["chapter"]
        raw_count = item["count"]

        try:
            book_name, chapter_number = parse_chapter_reference(chapter_ref)
        except ValueError:
            print(f"Skipping invalid chapter reference: {chapter_ref}")
            continue

        if book_name not in verses_lookup:
            print(f"Skipping chapter with missing book in verses lookup: {chapter_ref}")
            continue

        if chapter_number not in verses_lookup[book_name]:
            print(f"Skipping chapter with missing chapter number in verses lookup: {chapter_ref}")
            continue

        verse_count = verses_lookup[book_name][chapter_number]

        if verse_count <= 0:
            print(f"Skipping chapter with invalid verse count: {chapter_ref}")
            continue

        references_per_verse = raw_count / verse_count

        grouped[book_name].append({
            "chapter": chapter_ref,
            "chapter_number": chapter_number,
            "count": raw_count,
            "verses": verse_count,
            "references_per_verse": references_per_verse
        })

    output = {}

    for book_name in VALID_BOOKS:
        chapters = grouped.get(book_name, [])

        if not chapters:
            continue

        chapters_sorted = sorted(
            chapters,
            key=lambda item: item["references_per_verse"],
            reverse=True
        )

        output[book_name] = chapters_sorted

    return output


def make_book_graph(book_name, chapters, output_dir):
    """
    Creates one graph per book.

    X-axis:
        Chapter rank within the book, ordered by normalized references per verse.

    Y-axis:
        References per verse.

    Point labels:
        Actual chapter number.
    """
    os.makedirs(output_dir, exist_ok=True)

    x_values = list(range(1, len(chapters) + 1))
    y_values = [item["references_per_verse"] for item in chapters]
    chapter_labels = [str(item["chapter_number"]) for item in chapters]

    plt.figure(figsize=(12, 6))
    plt.plot(x_values, y_values, marker="o")

    for x, y, label in zip(x_values, y_values, chapter_labels):
        plt.text(
            x,
            y,
            label,
            fontsize=8,
            ha="center",
            va="bottom"
        )

    plt.title(f"{book_name}: Chapter Interest Falloff")
    plt.xlabel("Chapter rank within book")
    plt.ylabel("References per verse")
    plt.grid(True, alpha=0.3)
    plt.xticks(x_values)
    plt.tight_layout()

    filename = f"{safe_filename(book_name)}_chapter_interest_falloff_normalized.png"
    output_path = os.path.join(output_dir, filename)

    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"Saved graph: {output_path}")


def generate_normalized_ranked_books_and_graphs(
    chapter_counts_json_path,
    verses_per_chapter_json_path,
    output_json_path,
    graphs_output_dir
):
    print("Loading chapter counts...")
    chapter_counts = load_json(chapter_counts_json_path)

    print("Loading verses-per-chapter data...")
    verses_per_chapter_data = load_json(verses_per_chapter_json_path)

    print("Building verses lookup...")
    verses_lookup = build_verses_lookup(verses_per_chapter_data)

    print("Grouping chapters by book and normalizing by verse count...")
    chapters_by_book = group_and_normalize_chapters_by_book(
        chapter_counts=chapter_counts,
        verses_lookup=verses_lookup
    )

    print("Saving normalized grouped JSON...")
    save_json(chapters_by_book, output_json_path)

    print("Generating normalized graphs...")
    for book_name, chapters in chapters_by_book.items():
        make_book_graph(book_name, chapters, graphs_output_dir)

    print("Done.")
    print(f"Saved JSON to: {output_json_path}")
    print(f"Saved graphs to: {graphs_output_dir}")


if __name__ == "__main__":
    chapter_counts_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\chapters_counted_and_sorted.json"

    verses_per_chapter_json_path = r"C:\GitRepos\bible_data\ReferenceDatasets\verses_per_chapter.json"

    output_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\chapters_ranked_by_book_normalized.json"

    graphs_output_dir = r"C:\GitRepos\bible_data\ChristianCommentary\chapter_interest_graphs_normalized"

    generate_normalized_ranked_books_and_graphs(
        chapter_counts_json_path=chapter_counts_json_path,
        verses_per_chapter_json_path=verses_per_chapter_json_path,
        output_json_path=output_json_path,
        graphs_output_dir=graphs_output_dir
    )