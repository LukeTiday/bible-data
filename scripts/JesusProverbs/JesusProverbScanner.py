import json
import re
import subprocess
import sys
from pathlib import Path


# ============================================================
# Config
# ============================================================

MODEL_NAME = "qwen3:14b"

# Keep as None for full run.
# Set to an int like 20 while testing.
TEST_LIMIT = None

# Optional cheap prefilter.
# Recommended: keep False for first full run.
SKIP_LOW_HINT_VERSES = False

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

REDLETTER_PATH = REPO_ROOT / "ReferenceDatasets" / "redletter.json"

OUTPUT_PATH = SCRIPT_DIR / "jesus_one_liner_proverb_references.json"
LOG_PATH = SCRIPT_DIR / "jesus_one_liner_proverb_run_log.jsonl"
UNCLEAR_PATH = SCRIPT_DIR / "jesus_one_liner_proverb_unclear.json"

VERSEFETCH_DIR = REPO_ROOT / "WorldEnglishBible"
sys.path.insert(0, str(VERSEFETCH_DIR))

from VerseFetch import iter_verses  # noqa: E402


ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


# Canonical order for likely red-letter books.
# Add more books if your redletter.json includes them.
BOOK_ORDER = {
    "Matthew": 40,
    "Mark": 41,
    "Luke": 42,
    "John": 43,
    "Acts": 44,
    "1 Corinthians": 46,
    "2 Corinthians": 47,
    "Revelation": 66,
}


BOOK_ALIASES = {
    "Matt": "Matthew",
    "Mt": "Matthew",
    "Mrk": "Mark",
    "Mk": "Mark",
    "Luk": "Luke",
    "Lk": "Luke",
    "Jn": "John",
    "Rev": "Revelation",
}


# Loose hint regex. Used for logging and optional prefiltering.
# Do not trust this as the classifier.
PROVERB_HINT_RE = re.compile(
    r"\b("
    r"whoever|everyone who|no one|nothing|where|for where|"
    r"blessed are|woe to|first|last|"
    r"prophet|blind|fruit|tree|harvest|laborers|"
    r"ears to hear|serve two masters|treasure|heart|"
    r"lamp|salt|light|measure|wisdom|"
    r"greater than|least in|kingdom of heaven|kingdom of god|"
    r"mouth speaks|good tree|bad tree|rock|sand|"
    r"humbled|exalted|lose his life|save his life|"
    r"cannot serve|known by|little faith|faithful|"
    r"many are called|few are chosen"
    r")\b",
    flags=re.IGNORECASE,
)


# ============================================================
# Basic file helpers
# ============================================================

def clean_ansi(text):
    return ANSI_RE.sub("", text)


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


# ============================================================
# Reference parsing
# ============================================================

SINGLE_REF_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z]+)\s+(\d+):(\d+)$"
)

SIMPLE_RANGE_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z]+)\s+(\d+):(\d+)-(\d+)$"
)


def normalize_book_name(book):
    book = book.strip()
    return BOOK_ALIASES.get(book, book)


def parse_single_verse_ref(reference):
    """
    Supports:
      Matthew 5:13
      Mark 4:9
      Luke 6:39
      John 3:16

    This intentionally does not parse ranges.
    Ranges are expanded before classification.
    """

    reference = reference.strip()

    match = SINGLE_REF_RE.match(reference)

    if not match:
        raise ValueError(f"Unsupported single-verse reference format: {reference}")

    book = normalize_book_name(match.group(1))
    chapter = int(match.group(2))
    verse = int(match.group(3))

    return book, chapter, verse


def reference_sort_key(reference):
    book, chapter, verse = parse_single_verse_ref(reference)
    return (BOOK_ORDER.get(book, 999), chapter, verse)


def expand_reference_if_needed(reference):
    """
    redletter.json should ideally contain one verse per string.

    But if it contains simple same-chapter ranges like:
      Matthew 5:13-16

    this expands them to:
      Matthew 5:13
      Matthew 5:14
      Matthew 5:15
      Matthew 5:16

    More complex ranges are expanded with VerseFetch as a fallback.
    """

    reference = reference.strip()

    # Already a single verse.
    if SINGLE_REF_RE.match(reference):
        return [reference]

    # Simple same-chapter range.
    match = SIMPLE_RANGE_RE.match(reference)

    if match:
        book = normalize_book_name(match.group(1))
        chapter = int(match.group(2))
        start_verse = int(match.group(3))
        end_verse = int(match.group(4))

        if end_verse < start_verse:
            raise ValueError(f"Invalid verse range: {reference}")

        return [
            f"{book} {chapter}:{verse}"
            for verse in range(start_verse, end_verse + 1)
        ]

    # Fallback: use VerseFetch if it knows how to expand it.
    verses = list(iter_verses(reference))

    expanded = []

    for verse in verses:
        verse_ref = verse.get("reference")

        if verse_ref:
            expanded.append(verse_ref.strip())

    if expanded:
        return expanded

    raise ValueError(f"Could not expand reference: {reference}")


# ============================================================
# Queue + Bible text
# ============================================================

def load_redletter_refs():
    """
    Loads red-letter refs and normalizes them to single-verse references.
    """

    queue = load_json_list(REDLETTER_PATH)

    cleaned = []
    seen = set()

    for raw_ref in queue:
        if not isinstance(raw_ref, str):
            continue

        raw_ref = raw_ref.strip()

        if not raw_ref:
            continue

        expanded_refs = expand_reference_if_needed(raw_ref)

        for ref in expanded_refs:
            ref = ref.strip()

            if not ref:
                continue

            book, chapter, verse = parse_single_verse_ref(ref)
            normalized_ref = f"{book} {chapter}:{verse}"

            if normalized_ref in seen:
                continue

            seen.add(normalized_ref)
            cleaned.append(normalized_ref)

    cleaned.sort(key=reference_sort_key)

    return cleaned


def build_verse_queue():
    """
    One classification job per red-letter verse.
    """

    refs = load_redletter_refs()

    return [
        {
            "reference": ref,
            "source_references": [ref],
        }
        for ref in refs
    ]


def get_reference_text(reference):
    """
    Uses your WorldEnglishBible VerseFetch.iter_verses helper.

    Works for:
      Matthew 5:13
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
# Output state
# ============================================================

def load_completed_references():
    """
    Reads prior log entries so rerunning the script can skip completed YES/NO items.

    UNCLEAR and ERROR items are intentionally not skipped, so they can be retried.
    """

    completed = set()

    if not LOG_PATH.exists():
        return completed

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            reference = record.get("reference")
            answer = record.get("answer")

            if reference and answer in ["YES", "NO", "SKIPPED_LOW_HINT"]:
                completed.add(reference)

    return completed


def load_yes_references_from_log():
    refs = []
    seen = set()

    if not LOG_PATH.exists():
        return refs

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("answer") == "YES":
                reference = record.get("reference")

                if reference and reference not in seen:
                    seen.add(reference)
                    refs.append(reference)

    return refs


def add_matching_reference(reference):
    refs = load_json_list(OUTPUT_PATH)

    if reference not in refs:
        refs.append(reference)

    save_json_list(OUTPUT_PATH, refs)


def add_unclear_record(record):
    items = load_json_list(UNCLEAR_PATH)

    existing_refs = {
        item.get("reference")
        for item in items
        if isinstance(item, dict)
    }

    if record["reference"] not in existing_refs:
        items.append(record)

    save_json_list(UNCLEAR_PATH, items)


def rebuild_output_from_log():
    """
    Keeps the final output JSON in sync with prior successful YES classifications.
    Useful if the script is stopped and restarted.
    """

    refs = load_yes_references_from_log()
    save_json_list(OUTPUT_PATH, refs)
    return refs


# ============================================================
# Model response parsing
# ============================================================

def extract_final_yes_no(response_text):
    """
    Preferred format:
      FINAL: YES
      FINAL: NO

    Fallback:
      Use the last standalone YES or NO in the response.
    """

    cleaned = clean_ansi(response_text).strip()
    upper = cleaned.upper()

    final_matches = re.findall(r"FINAL:\s*(YES|NO)\b", upper)

    if final_matches:
        return final_matches[-1]

    loose_matches = re.findall(r"\b(YES|NO)\b", upper)

    if loose_matches:
        return loose_matches[-1]

    return None


def build_prompt(reference, text):
    return f"""
/think briefly

You are classifying one verse spoken by Jesus.

Question:
Is this verse itself a short proverb-like one-liner spoken by Jesus?

Answer YES if this single verse contains a compact wisdom saying, maxim, aphorism, memorable metaphor, or general principle spoken by Jesus.

A YES verse should mostly work as a stand-alone saying.

Examples of YES:
- No one can serve two masters.
- By their fruits you will know them.
- The blind lead the blind.
- The last will be first, and the first last.
- A prophet is not without honor except in his own country.
- Where your treasure is, there your heart will be also.
- Out of the abundance of the heart, the mouth speaks.
- He who has ears to hear, let him hear.
- Whoever exalts himself will be humbled.
- Many are called, but few chosen.

Answer NO if this verse is mainly:
- part of a longer story or parable
- part of a prayer
- a miracle command
- a one-time instruction
- narrative conversation
- a setup line
- a transition line
- an explanation line
- only meaningful when joined to surrounding verses

Important:
- Classify only this exact verse.
- Do not use surrounding verses.
- Do not list the proverb.
- Do not return JSON.
- If unsure, answer NO.

Required format:
Reasoning: one short sentence.
FINAL: YES

or

Reasoning: one short sentence.
FINAL: NO

Reference:
{reference}

Text:
{text}
""".strip()


def ask_ollama_quiet(reference, text):
    """
    Runs Ollama and captures the response quietly.
    It does not print streaming text.
    """

    prompt = build_prompt(reference, text)

    result = subprocess.run(
        ["ollama", "run", MODEL_NAME, prompt],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    cleaned_response = clean_ansi(result.stdout)
    final_answer = extract_final_yes_no(cleaned_response)

    if final_answer not in ["YES", "NO"]:
        final_answer = "UNCLEAR"

    return final_answer, cleaned_response


def print_short_reason(response):
    """
    Prints a small readable summary instead of the whole thinking trace.
    """

    cleaned = clean_ansi(response).strip()

    reasoning_match = re.search(
        r"Reasoning:\s*(.*?)(?:FINAL:\s*(?:YES|NO)|$)",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()
        reasoning = re.sub(r"\s+", " ", reasoning)

        if reasoning:
            print(f"Reasoning: {reasoning}")
            return

    # Fallback if the model ignored the format.
    without_thinking_markers = cleaned.replace("Thinking...", "")
    without_thinking_markers = without_thinking_markers.replace("...done thinking.", "")

    without_final = re.sub(
        r"FINAL:\s*(YES|NO)\b",
        "",
        without_thinking_markers,
        flags=re.IGNORECASE,
    ).strip()

    without_final = re.sub(r"\s+", " ", without_final)

    if len(without_final) > 220:
        without_final = without_final[:220].rstrip() + "..."

    if without_final:
        print(f"Reasoning: {without_final}")


# ============================================================
# Main
# ============================================================

def main():
    queue = build_verse_queue()

    if TEST_LIMIT is not None:
        queue = queue[:TEST_LIMIT]

    completed = load_completed_references()
    existing_yes_refs = rebuild_output_from_log()

    print(f"Loaded {len(queue)} red-letter verses.")
    print(f"Using model: {MODEL_NAME}")
    print(f"Skip low hint verses: {SKIP_LOW_HINT_VERSES}")
    print(f"Red-letter path: {REDLETTER_PATH}")
    print(f"Output path: {OUTPUT_PATH}")
    print(f"Log path: {LOG_PATH}")
    print(f"Unclear path: {UNCLEAR_PATH}")
    print(f"Already completed YES/NO/SKIPPED: {len(completed)}")
    print(f"Existing YES refs in output: {len(existing_yes_refs)}")
    print()

    yes_count = 0
    no_count = 0
    unclear_count = 0
    skipped_count = 0
    skipped_low_hint_count = 0
    error_count = 0

    total = len(queue)

    for index, item in enumerate(queue, start=1):
        reference = item["reference"]
        source_references = item["source_references"]

        if reference in completed:
            skipped_count += 1
            print(f"[{index}/{total}] SKIP {reference}")
            continue

        print(f"[{index}/{total}] Checking {reference}...")

        try:
            text = get_reference_text(reference)
            has_proverb_hint = bool(PROVERB_HINT_RE.search(text))

            if SKIP_LOW_HINT_VERSES and not has_proverb_hint:
                skipped_low_hint_count += 1

                record = {
                    "index": index,
                    "reference": reference,
                    "source_references": source_references,
                    "text": text,
                    "answer": "SKIPPED_LOW_HINT",
                    "is_one_liner_proverb_of_jesus": False,
                    "has_proverb_hint": has_proverb_hint,
                    "model": MODEL_NAME,
                }

                append_log(record)

                print("Result: SKIPPED_LOW_HINT")
                print(
                    f"Totals this run: "
                    f"YES={yes_count}, NO={no_count}, "
                    f"UNCLEAR={unclear_count}, ERROR={error_count}, "
                    f"SKIPPED={skipped_count}, SKIPPED_LOW_HINT={skipped_low_hint_count}"
                )
                print("-" * 80)
                continue

            final_answer, response = ask_ollama_quiet(reference, text)

        except Exception as e:
            error_count += 1

            record = {
                "index": index,
                "reference": reference,
                "source_references": source_references,
                "text": None,
                "answer": "ERROR",
                "is_one_liner_proverb_of_jesus": False,
                "has_proverb_hint": None,
                "model": MODEL_NAME,
                "error": str(e),
            }

            append_log(record)
            add_unclear_record(record)

            print("Result: ERROR")
            print(f"Error: {e}")
            print("-" * 80)
            continue

        is_one_liner_proverb = final_answer == "YES"

        record = {
            "index": index,
            "reference": reference,
            "source_references": source_references,
            "text": text,
            "answer": final_answer,
            "is_one_liner_proverb_of_jesus": is_one_liner_proverb,
            "has_proverb_hint": has_proverb_hint,
            "model": MODEL_NAME,
            "response": response,
        }

        if is_one_liner_proverb:
            add_matching_reference(reference)
            yes_count += 1
        elif final_answer == "NO":
            no_count += 1
        else:
            unclear_count += 1
            add_unclear_record(record)

        append_log(record)

        print(f"Result: {final_answer}")
        print_short_reason(response)
        print(f"Hint matched: {has_proverb_hint}")
        print(
            f"Totals this run: "
            f"YES={yes_count}, NO={no_count}, "
            f"UNCLEAR={unclear_count}, ERROR={error_count}, "
            f"SKIPPED={skipped_count}, SKIPPED_LOW_HINT={skipped_low_hint_count}"
        )
        print("-" * 80)

    final_refs = load_json_list(OUTPUT_PATH)

    print()
    print("Done.")
    print(f"YES this run: {yes_count}")
    print(f"NO this run: {no_count}")
    print(f"UNCLEAR this run: {unclear_count}")
    print(f"ERROR this run: {error_count}")
    print(f"SKIPPED this run: {skipped_count}")
    print(f"SKIPPED_LOW_HINT this run: {skipped_low_hint_count}")
    print(f"Total matching references in output: {len(final_refs)}")
    print(f"Output written to: {OUTPUT_PATH}")
    print(f"Log written to: {LOG_PATH}")
    print(f"Unclear records written to: {UNCLEAR_PATH}")


if __name__ == "__main__":
    main()