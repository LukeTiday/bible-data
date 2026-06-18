import json
import os
import re
from collections import defaultdict

import matplotlib.pyplot as plt


BIBLE_BOOK_ORDER = [
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


def build_total_verses_by_book(verses_per_chapter_data):
    """
    Builds:
        {
            "Genesis": 1533,
            "Exodus": 1213,
            ...
        }
    """
    total_verses_by_book = {}

    for book_entry in verses_per_chapter_data:
        book_name = book_entry["book"]

        total_verses = sum(
            int(chapter_entry["verses"])
            for chapter_entry in book_entry["chapters"]
        )

        total_verses_by_book[book_name] = total_verses

    return total_verses_by_book


def count_book_references(chapter_counts):
    """
    Takes chapters_counted_and_sorted.json shaped like:

        [
            {"chapter": "John 3", "count": 120},
            {"chapter": "Genesis 1", "count": 80}
        ]

    Produces raw book totals:

        {
            "John": 120,
            "Genesis": 80
        }
    """
    book_counts = defaultdict(int)

    for item in chapter_counts:
        chapter_ref = item["chapter"]
        count = item["count"]

        try:
            book_name, chapter_number = parse_chapter_reference(chapter_ref)
        except ValueError:
            print(f"Skipping invalid chapter reference: {chapter_ref}")
            continue

        book_counts[book_name] += count

    return dict(book_counts)


def normalize_book_counts(book_counts, total_verses_by_book):
    normalized_books = []

    bible_order_lookup = {
        book_name: index
        for index, book_name in enumerate(BIBLE_BOOK_ORDER)
    }

    for book_name, raw_count in book_counts.items():
        if book_name not in total_verses_by_book:
            print(f"Skipping book missing from verses-per-chapter data: {book_name}")
            continue

        total_verses = total_verses_by_book[book_name]

        if total_verses <= 0:
            print(f"Skipping book with invalid total verse count: {book_name}")
            continue

        references_per_verse = raw_count / total_verses

        normalized_books.append({
            "book": book_name,
            "count": raw_count,
            "total_verses": total_verses,
            "references_per_verse": references_per_verse,
            "bible_order": bible_order_lookup.get(book_name, 999)
        })

    normalized_books.sort(
        key=lambda item: item["references_per_verse"],
        reverse=True
    )

    return normalized_books


def make_books_graph(normalized_books, output_path, top_n=None):
    """
    Creates a ranked bar chart of books normalized by total verse count.

    Set top_n to a number like 20 if you only want the top 20.
    Leave as None to chart all books.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    books_to_graph = normalized_books

    if top_n is not None:
        books_to_graph = normalized_books[:top_n]

    book_names = [item["book"] for item in books_to_graph]
    scores = [item["references_per_verse"] for item in books_to_graph]

    height = max(8, len(book_names) * 0.32)

    plt.figure(figsize=(12, height))
    plt.barh(book_names, scores)
    plt.gca().invert_yaxis()

    plt.title("Books Ranked by Commentary References per Verse")
    plt.xlabel("References per verse")
    plt.ylabel("Book")

    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"Saved graph: {output_path}")


def generate_books_counted_sorted_normalized(
    chapters_counted_json_path,
    verses_per_chapter_json_path,
    output_json_path,
    output_graph_path,
    graph_top_n=None
):
    print("Loading chapter counts...")
    chapter_counts = load_json(chapters_counted_json_path)

    print("Loading verses-per-chapter data...")
    verses_per_chapter_data = load_json(verses_per_chapter_json_path)

    print("Building total verse counts by book...")
    total_verses_by_book = build_total_verses_by_book(verses_per_chapter_data)

    print("Counting raw references by book...")
    book_counts = count_book_references(chapter_counts)

    print("Normalizing book counts by total verses...")
    normalized_books = normalize_book_counts(
        book_counts=book_counts,
        total_verses_by_book=total_verses_by_book
    )

    print("Saving normalized book JSON...")
    save_json(normalized_books, output_json_path)

    print("Creating normalized book ranking graph...")
    make_books_graph(
        normalized_books=normalized_books,
        output_path=output_graph_path,
        top_n=graph_top_n
    )

    print("Done.")
    print(f"Saved JSON to: {output_json_path}")
    print(f"Saved graph to: {output_graph_path}")


if __name__ == "__main__":
    chapters_counted_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\chapters_counted_and_sorted.json"

    verses_per_chapter_json_path = r"C:\GitRepos\bible_data\ReferenceDatasets\verses_per_chapter.json"

    output_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\books_counted_and_sorted_normalized.json"

    output_graph_path = r"C:\GitRepos\bible_data\ChristianCommentary\books_counted_and_sorted_normalized.png"

    generate_books_counted_sorted_normalized(
        chapters_counted_json_path=chapters_counted_json_path,
        verses_per_chapter_json_path=verses_per_chapter_json_path,
        output_json_path=output_json_path,
        output_graph_path=output_graph_path,
        graph_top_n=None
    )