import json
import os
from collections import Counter


VALID_BOOKS = {
    "1 Chronicles", "1 Corinthians", "1 John", "1 Kings", "1 Peter", "1 Samuel",
    "1 Thessalonians", "1 Timothy", "2 Chronicles", "2 Corinthians", "2 John",
    "2 Kings", "2 Peter", "2 Samuel", "2 Thessalonians", "2 Timothy", "3 John",
    "Acts", "Amos", "Colossians", "Daniel", "Deuteronomy", "Ecclesiastes",
    "Ephesians", "Esther", "Exodus", "Ezekiel", "Ezra", "Galatians", "Genesis",
    "Habakkuk", "Haggai", "Hebrews", "Hosea", "Isaiah", "James", "Jeremiah",
    "Job", "Joel", "John", "Jonah", "Joshua", "Jude", "Judges", "Lamentations",
    "Leviticus", "Luke", "Malachi", "Mark", "Matthew", "Micah", "Nahum",
    "Nehemiah", "Numbers", "Obadiah", "Philemon", "Philippians", "Proverbs",
    "Psalms", "Revelation", "Romans", "Ruth", "Song of Solomon", "Titus",
    "Zechariah", "Zephaniah"
}


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file does not exist: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def extract_file_names(source_data):
    file_names = []

    for entry in source_data:
        if not isinstance(entry, dict):
            continue

        file_name = entry.get("file_name")

        if not file_name:
            continue

        if file_name.endswith(".toml"):
            file_name = file_name[:-5]

        file_names.append(file_name)

    return file_names


def normalize_psalms(file_names):
    return [
        file_name.replace("Psalm ", "Psalms ")
        for file_name in file_names
    ]


def get_book_name(reference):
    """
    Converts:
        John 3_16 -> John
        John 3_16-18 -> John
        1 Corinthians 13_4 -> 1 Corinthians
        Song of Solomon 2_4 -> Song of Solomon
    """
    chapter_part = reference.split("_", 1)[0]
    return " ".join(chapter_part.split(" ")[:-1])


def get_chapter_reference(reference):
    """
    Converts:
        John 3_16 -> John 3
        John 3_16-18 -> John 3
        Psalms 23_1 -> Psalms 23
    """
    return reference.split("_", 1)[0]


def remove_non_canonical_books(file_names):
    valid_books_lower = {book.lower() for book in VALID_BOOKS}

    filtered = []

    for file_name in file_names:
        book_name = get_book_name(file_name)

        if book_name.lower() in valid_books_lower:
            filtered.append(file_name)

    return filtered


def expand_verse_ranges(file_names):
    expanded = []

    for file_name in file_names:
        if "_" not in file_name:
            expanded.append(file_name)
            continue

        base_name, verse_part = file_name.rsplit("_", 1)

        if "-" not in verse_part:
            expanded.append(file_name)
            continue

        try:
            start_verse, end_verse = map(int, verse_part.split("-")[:2])
        except ValueError:
            print(f"Skipping invalid verse range: {file_name}")
            continue

        if end_verse < start_verse:
            print(f"Skipping reversed verse range: {file_name}")
            continue

        for verse in range(start_verse, end_verse + 1):
            expanded.append(f"{base_name}_{verse}")

    return expanded


def count_and_sort_verses(file_names):
    counts = Counter(file_names)

    return [
        {
            "verse": verse,
            "count": count
        }
        for verse, count in counts.most_common()
    ]


def count_and_sort_chapters(file_names):
    """
    Counts chapter references.

    Important:
    This function should receive the cleaned, non-expanded file names.

    That means:
        John 3_16-18 counts once for John 3
        John 3_16 counts once for John 3
        John 3_17 counts once for John 3
    """
    chapter_refs = [
        get_chapter_reference(file_name)
        for file_name in file_names
    ]

    counts = Counter(chapter_refs)

    return [
        {
            "chapter": chapter,
            "count": count
        }
        for chapter, count in counts.most_common()
    ]


def generate_sorted_counts(input_json_path, verse_output_json_path, chapter_output_json_path):
    print("Loading source JSON...")
    source_data = load_json(input_json_path)

    print("Extracting file names...")
    file_names = extract_file_names(source_data)

    print("Normalizing Psalms references...")
    file_names = normalize_psalms(file_names)

    print("Removing non-canonical books...")
    cleaned_file_names = remove_non_canonical_books(file_names)

    print("Counting and sorting chapters...")
    ranked_chapters = count_and_sort_chapters(cleaned_file_names)

    print("Expanding verse ranges...")
    expanded_file_names = expand_verse_ranges(cleaned_file_names)

    print("Counting and sorting verses...")
    ranked_verses = count_and_sort_verses(expanded_file_names)

    print("Saving verse output...")
    save_json(ranked_verses, verse_output_json_path)

    print("Saving chapter output...")
    save_json(ranked_chapters, chapter_output_json_path)

    print("Done.")
    print(f"Saved {len(ranked_verses)} counted verse entries to:")
    print(verse_output_json_path)
    print(f"Saved {len(ranked_chapters)} counted chapter entries to:")
    print(chapter_output_json_path)


if __name__ == "__main__":
    input_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\00_historical_christian_commentary.json"

    verse_output_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\verses_counted_and_sorted.json"

    chapter_output_json_path = r"C:\GitRepos\bible_data\ChristianCommentary\chapters_counted_and_sorted.json"

    generate_sorted_counts(
        input_json_path=input_json_path,
        verse_output_json_path=verse_output_json_path,
        chapter_output_json_path=chapter_output_json_path
    )