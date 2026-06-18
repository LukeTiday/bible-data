import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent

INPUT_PATH = ROOT / "BibleChaptersRankedByReferences" / "03_chapter_reference_rankings_by_book.json"
OUTPUT_PATH = ROOT / "BiblePlans" / "top-60-psalms-random.md"

PLAN_TITLE = "Top 60 Psalms"
PLAN_SLUG = "top-60-psalms"
PLAN_DESCRIPTION = "A 60-day reading plan through highly referenced Psalms."

BOOK_NAME = "Psalms"
DAYS = 60
RANDOM_SEED = 42


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_book(data, book_name):
    for book_data in data:
        if book_data["book"] == book_name:
            return book_data

    raise ValueError(f"Could not find book named '{book_name}' in {INPUT_PATH}")


def psalm_reference(chapter_number):
    return f"Psalm {chapter_number}"


def main():
    data = load_json(INPUT_PATH)
    psalms_data = find_book(data, BOOK_NAME)

    chapters = sorted(
        psalms_data["chapters"],
        key=lambda item: item["references_per_verse"],
        reverse=True,
    )

    top_psalms = chapters[:DAYS]

    if len(top_psalms) < DAYS:
        raise ValueError(
            f"Only found {len(top_psalms)} Psalms, but needed {DAYS}."
        )

    psalm_1 = None
    other_psalms = []

    for chapter in top_psalms:
        if chapter["chapter_number"] == 1:
            psalm_1 = chapter
        else:
            other_psalms.append(chapter)

    if psalm_1 is None:
        raise ValueError(
            "Psalm 1 was not found in the top 60 Psalms. "
            "Either increase the source pool or manually force Psalm 1 in."
        )

    random.seed(RANDOM_SEED)
    random.shuffle(other_psalms)

    ordered_psalms = [psalm_1] + other_psalms

    lines = [
        "---",
        f"title: {PLAN_TITLE}",
        f"slug: {PLAN_SLUG}",
        f"description: {PLAN_DESCRIPTION}",
        "image_url:",
        "---",
        "",
    ]

    for day_number, chapter in enumerate(ordered_psalms, start=1):
        chapter_number = chapter["chapter_number"]
        scripture_ref = psalm_reference(chapter_number)

        lines.extend(
            [
                f"# Day {day_number}: {scripture_ref}",
                "",
                "::scripture",
                scripture_ref,
                "::",
                "",
            ]
        )

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved plan to: {OUTPUT_PATH}")
    print(f"Days written: {len(ordered_psalms)}")
    print()
    print("First 10 days:")

    for i, chapter in enumerate(ordered_psalms[:10], start=1):
        print(f"Day {i}: Psalm {chapter['chapter_number']}")


if __name__ == "__main__":
    main()