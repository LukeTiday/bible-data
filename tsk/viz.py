from pathlib import Path
import json
import matplotlib.pyplot as plt

# -----------------------------
# Config
# -----------------------------

INPUT_PATH = Path("chapter_incoming_reference_counts_normalized.json")
OUTPUT_PATH = Path("chapter_reference_falloff.png")

TITLE = "Chapter Incoming Cross-Reference Falloff"
SHOW_TOP_N_LABELS = 20


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Could not find input file: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    data = load_json(INPUT_PATH)

    if not isinstance(data, list):
        raise ValueError("Expected JSON root to be a list.")

    if not data:
        raise ValueError("JSON file is empty.")

    # Sort just in case the JSON is not already ranked
    data = sorted(
        data,
        key=lambda row: row["references_per_verse"],
        reverse=True,
    )

    ranks = list(range(1, len(data) + 1))
    counts = [row["references_per_verse"] for row in data]

    plt.figure(figsize=(16, 9))

    # Line shows the overall falloff shape
    plt.plot(
        ranks,
        counts,
        linewidth=1,
        alpha=0.85,
    )

    # Tiny points help reveal density without making the chart too noisy
    plt.scatter(
        ranks,
        counts,
        s=6,
        alpha=0.45,
    )

    plt.title(TITLE)
    plt.xlabel("Chapter rank")
    plt.ylabel("Incoming references per verse")

    plt.grid(True, alpha=0.25)

    # Label only the top N so the graph does not become unreadable
    for i, row in enumerate(data[:SHOW_TOP_N_LABELS]):
        rank = i + 1
        count = row["references_per_verse"]
        chapter = row["chapter"]

        plt.annotate(
            chapter,
            xy=(rank, count),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=8,
            va="center",
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=200)
    plt.show()

    print("Done.")
    print(f"Chapters graphed: {len(data)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()