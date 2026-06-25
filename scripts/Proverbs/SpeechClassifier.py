import json
import re
import sys
from pathlib import Path


# ============================================================
# Config
# ============================================================

# Keep as None for full run.
# Set to an int like 10 while testing.
TEST_LIMIT = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

QUEUE_PATH = REPO_ROOT / "ReferenceDatasets" / "proverbsProverbs.json"

OUTPUT_PATH = SCRIPT_DIR / "proverbs_speech_and_tongue_references.json"
LOG_PATH = SCRIPT_DIR / "proverbs_speech_and_tongue_keyword_log.jsonl"

VERSEFETCH_DIR = REPO_ROOT / "WorldEnglishBible"
sys.path.insert(0, str(VERSEFETCH_DIR))

from VerseFetch import iter_verses  # noqa: E402


# ============================================================
# Speech / Tongue keyword config
# ============================================================

# These are intentionally direct text keywords.
# The classifier matches actual words/phrases in the proverb text.
#
# Examples matched:
# - mouth, lips, tongue
# - words, answer, rebuke, counsel
# - gossip, slander, whisperer, false witness
# - lie, lying, truth, truthful
# - silence, speak, speech
#
# This does NOT use semantic guessing.
# If none of these appear in the text, the proverb is not included.

SPEECH_KEYWORD_PATTERNS = [
    # Direct speech organs
    r"\bmouth\b",
    r"\bmouths\b",
    r"\blip\b",
    r"\blips\b",
    r"\btongue\b",
    r"\btongues\b",

    # Words / speaking
    r"\bword\b",
    r"\bwords\b",
    r"\bspeech\b",
    r"\bspeak\b",
    r"\bspeaks\b",
    r"\bspeaker\b",
    r"\bspeaking\b",
    r"\bsaid\b",
    r"\bsay\b",
    r"\bsays\b",
    r"\bsaying\b",
    r"\btalk\b",
    r"\btalks\b",
    r"\btalking\b",
    r"\bvoice\b",
    r"\bvoices\b",
    r"\banswer\b",
    r"\banswers\b",
    r"\banswered\b",
    r"\banswering\b",
    r"\breply\b",
    r"\breplies\b",
    r"\breplied\b",

    # Teaching / verbal instruction / counsel
    r"\bteach\b",
    r"\bteaches\b",
    r"\bteacher\b",
    r"\binstruct\b",
    r"\binstructs\b",
    r"\bcounsel\b",
    r"\bcounsels\b",
    r"\bcounselor\b",
    r"\bcounsellor\b",
    r"\badvice\b",
    r"\badmonish\b",
    r"\badmonishes\b",
    r"\brebuke\b",
    r"\brebukes\b",
    r"\brebuked\b",
    r"\breproof\b",
    r"\bcorrect\b",
    r"\bcorrection\b",

    # Truth / lies / witness
    r"\btruth\b",
    r"\btrue\b",
    r"\btruthful\b",
    r"\bfalse\b",
    r"\bfalsehood\b",
    r"\blie\b",
    r"\blies\b",
    r"\bliar\b",
    r"\bliars\b",
    r"\blying\b",
    r"\bdeceit\b",
    r"\bdeceitful\b",
    r"\bdeceive\b",
    r"\bdeceives\b",
    r"\bdeceiver\b",
    r"\bwitness\b",
    r"\bwitnesses\b",
    r"\btestimony\b",

    # Harmful speech
    r"\bgossip\b",
    r"\bgossips\b",
    r"\bwhisper\b",
    r"\bwhispers\b",
    r"\bwhisperer\b",
    r"\bslander\b",
    r"\bslanders\b",
    r"\bslanderer\b",
    r"\btalebearer\b",
    r"\bbackbite\b",
    r"\bbackbiting\b",
    r"\bflatter\b",
    r"\bflatters\b",
    r"\bflattery\b",
    r"\bboast\b",
    r"\bboasts\b",
    r"\bboasting\b",
    r"\bchatter\b",
    r"\bchattering\b",
    r"\bwitness\b",
    r"\bsound\b",
    r"\bdeceitful\b",
    r"\bdeceit\b",
    r"\blying\b",
    r"\bvoice\b",
    r"\bmock\b",
    r"\bmocker\b",
    r"\bmocking\b",
    r"\bcurse\b",
    r"\bcurses\b",
    r"\bcursing\b",
    r"\bloud\b",
    r"\btruth\b",
    r"\btruthful\b",
    r"\baloud\b",
    r"\bcry\b",
    r"\bcries\b",
    r"\bcried\b",
    r"\bquarrel\b",
    r"\bquarreling\b",
    r"\bslander\b",
    r"\bguide\b",
    r"\bplea\b",
    r"\bpleads\b",
    r"\bpleas\b",
    r"\brespond\b",
    r"\briddles\b",
    r"\bsecrets\b",
    r"\bsecret\b",
    r"\btestifies\b",
    r"\btestify\b",
    r"\btestimony\b",
    r"\bteachers\b",
    r"\bteaches\b",
    r"\bteach\b",
    r"\bzeal\b",
    

    # Silence / restraint
    r"\bsilent\b",
    r"\bsilence\b",
    r"\bquiet\b",
    r"\brestrain\b",
    r"\brestrains\b",
    r"\bholds his peace\b",
    r"\bhold his peace\b",
    r"\bkeeps his mouth\b",
    r"\bguard his mouth\b",
    r"\bguards his mouth\b",

    # Common WEB phrasing in Proverbs
    r"\bexcellent speech\b",
    r"\blying lips\b",
    r"\btruthful lips\b",
    r"\bfalse witness\b",
    r"\bfaithful witness\b",
    r"\brash words\b",
    r"\bharsh word\b",
    r"\bgentle answer\b",
    r"\bsoft answer\b",
    r"\bpleasant words\b",
    r"\bchoice morsels\b",
]


COMPILED_SPEECH_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in SPEECH_KEYWORD_PATTERNS
]


# ============================================================
# Basic file helpers
# ============================================================

def load_json_list(path):
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    raise ValueError(f"{path} exists but is not a JSON list.")


def save_json_list(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def append_log(record):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def reset_file(path):
    if path.exists():
        path.unlink()


# ============================================================
# Queue + Bible text
# ============================================================

def load_proverb_queue():
    queue = load_json_list(QUEUE_PATH)

    cleaned = []
    seen = set()

    for reference in queue:
        if not isinstance(reference, str):
            continue

        reference = reference.strip()

        if not reference:
            continue

        # Dedupe duplicate references in the queue.
        if reference in seen:
            continue

        seen.add(reference)
        cleaned.append(reference)

    return cleaned


def get_reference_text(reference):
    """
    Uses your WorldEnglishBible VerseFetch.iter_verses helper.

    Works for:
      Proverbs 10:19
      Proverbs 25:11-12
    """

    verses = list(iter_verses(reference))

    if not verses:
        raise ValueError(f"No verses found for reference: {reference}")

    parts = []

    for verse in verses:
        verse_ref = verse.get("reference", reference)
        verse_text = verse.get("text", "").strip()

        if verse_text:
            parts.append(f"{verse_ref} {verse_text}")

    return "\n".join(parts).strip()


# ============================================================
# Keyword classifier
# ============================================================

def normalize_text(text):
    """
    Keeps text readable but normalizes punctuation enough for matching.
    """

    text = text.replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", " ")
    text = text.replace("–", " ")
    return text


def find_speech_keyword_matches(text):
    """
    Returns a sorted list of matched keyword pattern strings.

    This is deliberately simple:
    if a speech keyword appears in the proverb text, it matches.
    """

    normalized = normalize_text(text)

    matches = []

    for raw_pattern, compiled_pattern in zip(
        SPEECH_KEYWORD_PATTERNS,
        COMPILED_SPEECH_PATTERNS
    ):
        if compiled_pattern.search(normalized):
            cleaned_pattern = (
                raw_pattern
                .replace(r"\b", "")
                .replace("\\", "")
            )
            matches.append(cleaned_pattern)

    return sorted(set(matches))


def is_speech_and_tongue(text):
    matches = find_speech_keyword_matches(text)
    return len(matches) > 0, matches


# ============================================================
# Main
# ============================================================

def main():
    queue = load_proverb_queue()

    if TEST_LIMIT is not None:
        queue = queue[:TEST_LIMIT]

    reset_file(OUTPUT_PATH)
    reset_file(LOG_PATH)

    print(f"Loaded {len(queue)} proverb units.")
    print("Classifier: keyword matching only")
    print(f"Queue path: {QUEUE_PATH}")
    print(f"Output path: {OUTPUT_PATH}")
    print(f"Log path: {LOG_PATH}")
    print()

    matching_refs = []

    yes_count = 0
    no_count = 0
    error_count = 0

    total = len(queue)

    for index, reference in enumerate(queue, start=1):
        print(f"[{index}/{total}] Checking {reference}...")

        try:
            text = get_reference_text(reference)
            matched, keyword_matches = is_speech_and_tongue(text)

            record = {
                "index": index,
                "reference": reference,
                "text": text,
                "is_speech_and_tongue": matched,
                "matched_keywords": keyword_matches,
            }

            append_log(record)

            if matched:
                matching_refs.append(reference)
                yes_count += 1
                print(f"Result: YES")
                print(f"Matched keywords: {', '.join(keyword_matches)}")
            else:
                no_count += 1
                print("Result: NO")

        except Exception as e:
            error_count += 1

            record = {
                "index": index,
                "reference": reference,
                "text": None,
                "is_speech_and_tongue": False,
                "matched_keywords": [],
                "error": str(e),
            }

            append_log(record)

            print("Result: ERROR")
            print(f"Error: {e}")

        print(
            f"Totals this run: "
            f"YES={yes_count}, NO={no_count}, ERROR={error_count}"
        )
        print("-" * 80)

    save_json_list(OUTPUT_PATH, matching_refs)

    print()
    print("Done.")
    print(f"YES this run: {yes_count}")
    print(f"NO this run: {no_count}")
    print(f"ERROR this run: {error_count}")
    print(f"Total matching references in output: {len(matching_refs)}")
    print(f"Output written to: {OUTPUT_PATH}")
    print(f"Log written to: {LOG_PATH}")


if __name__ == "__main__":
    main()