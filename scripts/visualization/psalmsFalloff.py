import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(r"C:\git_repos\bible-data")

INPUT_PATH = ROOT / "BibleChaptersRankedByReferences" / "03_chapter_reference_rankings_by_book.json"
OUTPUT_PATH = ROOT / "scripts" / "visualization" / "psalms_reference_falloff.png"

BOOK_NAME = "Psalms"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    data = load_json(INPUT_PATH)

    psalms_data = None

    for book_data in data:
        if book_data["book"] == BOOK_NAME:
            psalms_data = book_data
            break

    if psalms_data is None:
        raise ValueError(f"Could not find book named '{BOOK_NAME}' in {INPUT_PATH}")

    chapters = psalms_data["chapters"]

    # Sort again just to be safe
    chapters = sorted(
        chapters,
        key=lambda item: item["references_per_verse"],
        reverse=True,
    )

    ranks = list(range(1, len(chapters) + 1))
    scores = [chapter["references_per_verse"] for chapter in chapters]
    labels = [chapter["chapter"] for chapter in chapters]

    plt.figure(figsize=(14, 7))

    plt.plot(ranks, scores, marker="o", linewidth=2, markersize=4)

    plt.title("Psalms Reference Falloff")
    plt.xlabel("Ranked Psalm chapters, most referenced to least")
    plt.ylabel("References per verse")

    plt.grid(True, alpha=0.3)

    # Label the top 10 points so the graph is actually useful
    top_label_count = min(10, len(chapters))

    for i in range(top_label_count):
        plt.annotate(
            labels[i],
            (ranks[i], scores[i]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=300)
    plt.show()

    print(f"Saved graph to: {OUTPUT_PATH}")
    print()
    print("Top 20 Psalms by references per verse:")

    for chapter in chapters[:20]:
        print(
            f"{chapter['book_rank']:>3}. "
            f"{chapter['chapter']:<12} "
            f"{chapter['references_per_verse']:.2f} refs/verse "
            f"({chapter['total_references']} refs / {chapter['verse_count']} verses)"
        )


if __name__ == "__main__":
    main()