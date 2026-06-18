from pathlib import Path
import json
import re

import matplotlib.pyplot as plt


# -----------------------------
# Config
# -----------------------------

INPUT_PATH = Path("03_chapter_reference_rankings_by_book.json")
OUTPUT_DIR = Path("book_chapter_interest_charts")

# Set to None for all books, or an integer like 20 if you only want the top 20 chapters per book.
MAX_CHAPTERS_PER_BOOK = None

# Skip tiny books if desired. Leave as 1 to chart everything.
MIN_CHAPTERS_TO_CHART = 1


# -----------------------------
# Helpers
# -----------------------------

def safe_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Could not find input file: {path}")

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def ensure_output_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Charting
# -----------------------------

def chart_book(book_entry: dict):
    book_name = book_entry["book"]
    chapters = book_entry.get("chapters", [])

    if len(chapters) < MIN_CHAPTERS_TO_CHART:
        return

    # Sort by book_rank if available, otherwise by references_per_verse descending.
    chapters = sorted(
        chapters,
        key=lambda row: row.get("book_rank", 999999)
    )

    if MAX_CHAPTERS_PER_BOOK is not None:
        chapters = chapters[:MAX_CHAPTERS_PER_BOOK]

    x_values = list(range(1, len(chapters) + 1))
    y_values = [row["references_per_verse"] for row in chapters]
    labels = [str(row["chapter_number"]) for row in chapters]

    plt.figure(figsize=(14, 7))

    # Curve + points
    plt.plot(x_values, y_values, marker="o", linewidth=2)

    # Label every point with chapter number
    for x, y, label in zip(x_values, y_values, labels):
        plt.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8
        )

    plt.title(f"{book_name}: Chapter Interest Falloff")
    plt.xlabel("Chapter rank within book")
    plt.ylabel("References per verse")

    plt.grid(True, alpha=0.3)

    # Use integer rank ticks when reasonable
    if len(x_values) <= 40:
        plt.xticks(x_values)

    # Add a little vertical breathing room for labels
    if y_values:
        ymax = max(y_values)
        plt.ylim(0, ymax * 1.15 if ymax > 0 else 1)

    output_path = OUTPUT_DIR / f"{safe_filename(book_name)}_chapter_interest_falloff.png"

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

    print(f"Saved: {output_path}")


def main():
    ensure_output_dir(OUTPUT_DIR)

    data = load_json(INPUT_PATH)

    if not isinstance(data, list):
        raise ValueError("Expected top-level JSON to be a list of book entries.")

    for book_entry in data:
        chart_book(book_entry)

    print("Done.")


if __name__ == "__main__":
    main()