from pathlib import Path
import json
import re

import matplotlib.pyplot as plt


# -----------------------------
# Config
# -----------------------------

COMMENTARY_PATH = Path(
    r"C:\git_repos\bible-data\BibleChaptersRankedByReferences\03_chapter_reference_rankings_by_book.json"
)

BIBLICAL_PATH = Path(
    r"C:\git_repos\bible-data\tsk\chapter_incoming_reference_counts_normalized.json"
)

OUTPUT_DIR = Path("book_interest_comparison_charts")

# Set to None for all chapters in each book.
# Or set to something like 25 if charts get too crowded.
MAX_CHAPTERS_PER_BOOK = None

# Chart everything by default.
MIN_CHAPTERS_TO_CHART = 1


# -----------------------------
# Helpers
# -----------------------------

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Could not find file: {path}")

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def safe_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def parse_chapter_label(chapter: str):
    """
    Turns strings like:
        Genesis 1
        1 Peter 3
        Song of Solomon 2

    into:
        ("Genesis", 1)
        ("1 Peter", 3)
        ("Song of Solomon", 2)
    """

    match = re.match(r"^(.+?)\s+(\d+)$", chapter.strip())

    if not match:
        return None, None

    book = match.group(1)
    chapter_number = int(match.group(2))

    return book, chapter_number


def normalize_min_max(values: list[float]) -> list[float]:
    """
    Normalizes values so the lowest point is 0 and highest point is 1.
    If all values are the same, returns 0.5 for every point.
    """

    if not values:
        return []

    min_value = min(values)
    max_value = max(values)

    if max_value == min_value:
        return [0.5 for _ in values]

    return [
        (value - min_value) / (max_value - min_value)
        for value in values
    ]


def build_biblical_lookup(biblical_data: list[dict]) -> dict[tuple[str, int], dict]:
    """
    Builds lookup:
        ("Genesis", 1) -> biblical row
    """

    lookup = {}

    for row in biblical_data:
        chapter_label = row.get("chapter")
        book, chapter_number = parse_chapter_label(chapter_label)

        if book is None or chapter_number is None:
            continue

        lookup[(book, chapter_number)] = row

    return lookup


# -----------------------------
# Charting
# -----------------------------

def chart_book(book_entry: dict, biblical_lookup: dict):
    book_name = book_entry["book"]
    commentary_chapters = book_entry.get("chapters", [])

    if len(commentary_chapters) < MIN_CHAPTERS_TO_CHART:
        return

    # Use human/commentary interest order.
    commentary_chapters = sorted(
        commentary_chapters,
        key=lambda row: row.get("book_rank", 999999)
    )

    if MAX_CHAPTERS_PER_BOOK is not None:
        commentary_chapters = commentary_chapters[:MAX_CHAPTERS_PER_BOOK]

    rows = []

    for commentary_row in commentary_chapters:
        chapter_number = int(commentary_row["chapter_number"])
        biblical_row = biblical_lookup.get((book_name, chapter_number))

        # If a chapter is missing from the biblical/cross-ref dataset,
        # use 0 so the chapter still appears in human-interest order.
        biblical_value = 0

        if biblical_row is not None:
            biblical_value = float(biblical_row["references_per_verse"])

        rows.append({
            "chapter_number": chapter_number,
            "human_raw": float(commentary_row["references_per_verse"]),
            "biblical_raw": biblical_value,
        })

    if not rows:
        return

    x_values = list(range(1, len(rows) + 1))
    chapter_labels = [str(row["chapter_number"]) for row in rows]

    human_raw = [row["human_raw"] for row in rows]
    biblical_raw = [row["biblical_raw"] for row in rows]

    human_norm = normalize_min_max(human_raw)
    biblical_norm = normalize_min_max(biblical_raw)

    fig, ax_left = plt.subplots(figsize=(15, 7))
    ax_right = ax_left.twinx()

    # Left axis: human/commentary units
    human_line, = ax_left.plot(
        x_values,
        human_norm,
        marker="o",
        linewidth=2,
        color="blue",
        label="Human interest — commentary references"
    )

    # Right axis: biblical/cross-reference units
    biblical_line, = ax_right.plot(
        x_values,
        biblical_norm,
        marker="o",
        linewidth=2,
        color="red",
        label="Biblical interest — cross references"
    )

    # Label every point with chapter number.
    # Offset red labels downward a bit so they don't sit directly on blue labels.
    for x, y, label in zip(x_values, human_norm, chapter_labels):
        ax_left.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
            color="blue"
        )

    for x, y, label in zip(x_values, biblical_norm, chapter_labels):
        ax_right.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(0, -13),
            ha="center",
            fontsize=8,
            color="red"
        )

    ax_left.set_title(
        f"{book_name}: Human Interest vs Biblical Interest by Chapter"
    )

    ax_left.set_xlabel(
        "Chapter order by human/commentary interest rank"
    )

    ax_left.set_ylabel(
        "Human interest, normalized commentary references per verse",
        color="blue"
    )

    ax_right.set_ylabel(
        "Biblical interest, normalized cross references per verse",
        color="red"
    )

    ax_left.tick_params(axis="y", labelcolor="blue")
    ax_right.tick_params(axis="y", labelcolor="red")

    ax_left.set_ylim(-0.05, 1.1)
    ax_right.set_ylim(-0.05, 1.1)

    ax_left.grid(True, alpha=0.3)

    if len(x_values) <= 50:
        ax_left.set_xticks(x_values)

    # Combined legend
    lines = [human_line, biblical_line]
    labels = [line.get_label() for line in lines]
    ax_left.legend(lines, labels, loc="upper right")

    # Add raw max/min context as small caption.
    caption = (
        f"Human raw range: {min(human_raw):.2f}–{max(human_raw):.2f} refs/verse | "
        f"Biblical raw range: {min(biblical_raw):.2f}–{max(biblical_raw):.2f} refs/verse"
    )

    fig.text(
        0.5,
        0.01,
        caption,
        ha="center",
        fontsize=9
    )

    output_path = OUTPUT_DIR / f"{safe_filename(book_name)}_human_vs_biblical_interest.png"

    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.savefig(output_path, dpi=200)
    plt.close()

    print(f"Saved: {output_path}")


# -----------------------------
# Main
# -----------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    commentary_data = load_json(COMMENTARY_PATH)
    biblical_data = load_json(BIBLICAL_PATH)

    biblical_lookup = build_biblical_lookup(biblical_data)

    for book_entry in commentary_data:
        chart_book(book_entry, biblical_lookup)

    print("Done.")


if __name__ == "__main__":
    main()