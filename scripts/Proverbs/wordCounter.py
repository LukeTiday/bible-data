import json
import re
import sys
from pathlib import Path
from collections import Counter


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

# If VerseFetch.py is in a different folder, update this path.
# Example:
VERSE_FETCH_DIR = Path(r"C:\git_repos\bible-data\WorldEnglishBible")

OUTPUT_PATH = SCRIPT_DIR / "proverbs_word_counts.json"

# Optional debug output showing every verse used.
DEBUG_VERSES_PATH = SCRIPT_DIR / "proverbs_verses_used.json"


# ------------------------------------------------------------
# Import VerseFetch
# ------------------------------------------------------------

if str(VERSE_FETCH_DIR) not in sys.path:
    sys.path.insert(0, str(VERSE_FETCH_DIR))

try:
    from VerseFetch import iter_verses
except ImportError as e:
    raise ImportError(
        "Could not import VerseFetch.py.\n"
        "Make sure VerseFetch.py is in the same folder as wordCounter.py, "
        "or update VERSE_FETCH_DIR near the top of this script."
    ) from e


# ------------------------------------------------------------
# Word parsing
# ------------------------------------------------------------

# Keeps normal words and simple contractions:
#   wisdom
#   father's
#   don't
#
# Does not include numbers.
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def normalize_word(word):
    """
    Basic normalization only.

    This intentionally does not combine:
      proverb / proverbs
      answer / answers / answered
      wise / wiser / wisdom

    Those can be aggregated later.
    """

    return word.lower()


def extract_words(text):
    return [
        normalize_word(match.group(0))
        for match in WORD_RE.finditer(text)
    ]


# ------------------------------------------------------------
# Main logic
# ------------------------------------------------------------

def count_words_in_proverbs():
    counter = Counter()
    verse_records = []

    # VerseFetch supports chapter references like "Psalm 1".
    # For full Proverbs, using 1:1-31:31 is explicit and safe.
    reference = "Proverbs 1:1-31:31"

    for verse in iter_verses(reference):
        verse_records.append({
            "reference": f'{verse["book"]} {verse["chapter"]}:{verse["verse"]}',
            "text": verse["text"],
        })

        words = extract_words(verse["text"])
        counter.update(words)

    return counter, verse_records


def sort_counts(counter):
    """
    Sort by:
      1. Highest count first
      2. Alphabetical order for ties
    """

    return dict(
        sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0])
        )
    )


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    print("Counting words in Proverbs...")
    print(f"Output path: {OUTPUT_PATH}")
    print()

    counter, verse_records = count_words_in_proverbs()
    sorted_counts = sort_counts(counter)

    save_json(OUTPUT_PATH, sorted_counts)
    save_json(DEBUG_VERSES_PATH, verse_records)

    print("Done.")
    print(f"Verses counted: {len(verse_records)}")
    print(f"Unique words counted: {len(sorted_counts)}")
    print(f"Total word instances: {sum(sorted_counts.values())}")
    print(f"Word counts written to: {OUTPUT_PATH}")
    print(f"Debug verses written to: {DEBUG_VERSES_PATH}")

    print()
    print("Top 25 words:")
    for word, count in list(sorted_counts.items())[:25]:
        print(f"{word}: {count}")


if __name__ == "__main__":
    main()