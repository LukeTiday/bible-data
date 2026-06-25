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
# Set to an int like 10 while testing.
TEST_LIMIT = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

QUEUE_PATH = REPO_ROOT / "ReferenceDatasets" / "proverbsProverbs.json"

OUTPUT_PATH = SCRIPT_DIR / "proverbs_speech_and_tongue_references.json"
LOG_PATH = SCRIPT_DIR / "proverbs_speech_and_tongue_run_log.jsonl"
UNCLEAR_PATH = SCRIPT_DIR / "proverbs_speech_and_tongue_unclear.json"

VERSEFETCH_DIR = REPO_ROOT / "WorldEnglishBible"
sys.path.insert(0, str(VERSEFETCH_DIR))

from VerseFetch import iter_verses  # noqa: E402


ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


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
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


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

        # The queue currently has a few duplicate references.
        # We dedupe so one proverb is only classified once.
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
# Output state
# ============================================================

def load_completed_references():
    """
    Reads prior log entries so rerunning the script can skip completed YES/NO items.
    UNCLEAR items are intentionally not skipped, so they can be retried.
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

            if reference and answer in ["YES", "NO"]:
                completed.add(reference)

    return completed


def load_yes_references_from_log():
    refs = []

    if not LOG_PATH.exists():
        return refs

    seen = set()

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

You are classifying individual proverbs from the book of Proverbs by theme.

Theme:
Speech and the Tongue

Classify ONLY this exact proverb reference or proverb range.

Question:
Is this proverb mainly about speech, words, the mouth, lips, tongue, lying, truth-telling, gossip, slander, flattery, rebuke, answering, silence, quarrels caused by words, or the moral power of what people say?

YES if the proverb is substantially about:
- speech, words, sayings, answers, counsel, rebuke, teaching, or verbal instruction
- the mouth, lips, tongue, lying lips, truthful lips, false witness, gossip, slander, flattery, whispering, boasting, or silence
- speech causing life, death, healing, harm, conflict, peace, wisdom, or folly
- verbal integrity, truthful testimony, deceitful testimony, or perverse speech

NO if:
- speech is not a main point
- the proverb is mainly about money, work, laziness, family, kingship, poverty, sexuality, justice, violence, pride, or general wisdom without a speech focus
- the proverb only has a word like "instruction" but the point is broader moral formation rather than speech itself

For multi-verse ranges:
- Answer YES if the range as a whole is clearly about Speech and the Tongue.
- Answer YES if at least one verse in the range is strongly about speech and the range is intended as one proverb unit.
- Answer NO if the speech connection is weak or incidental.

Think briefly.
Use no more than 2 short reasoning sentences.
End with exactly one final line.

Required format:
Reasoning: one or two short sentences.
FINAL: YES

or

Reasoning: one or two short sentences.
FINAL: NO

Examples:
Proverbs 10:19 = FINAL: YES
Proverbs 12:18 = FINAL: YES
Proverbs 15:1 = FINAL: YES
Proverbs 16:24 = FINAL: YES
Proverbs 6:6-8 = FINAL: NO
Proverbs 10:4 = FINAL: NO
Proverbs 13:11 = FINAL: NO

Proverb:
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
    queue = load_proverb_queue()

    if TEST_LIMIT is not None:
        queue = queue[:TEST_LIMIT]

    completed = load_completed_references()
    existing_yes_refs = rebuild_output_from_log()

    print(f"Loaded {len(queue)} proverb units.")
    print(f"Using model: {MODEL_NAME}")
    print(f"Queue path: {QUEUE_PATH}")
    print(f"Output path: {OUTPUT_PATH}")
    print(f"Log path: {LOG_PATH}")
    print(f"Unclear path: {UNCLEAR_PATH}")
    print(f"Already completed YES/NO: {len(completed)}")
    print(f"Existing YES refs in output: {len(existing_yes_refs)}")
    print()

    yes_count = 0
    no_count = 0
    unclear_count = 0
    skipped_count = 0
    error_count = 0

    total = len(queue)

    for index, reference in enumerate(queue, start=1):
        if reference in completed:
            skipped_count += 1
            print(f"[{index}/{total}] SKIP {reference}")
            continue

        print(f"[{index}/{total}] Checking {reference}...")

        try:
            text = get_reference_text(reference)
            final_answer, response = ask_ollama_quiet(reference, text)

        except Exception as e:
            error_count += 1

            record = {
                "index": index,
                "reference": reference,
                "text": None,
                "answer": "ERROR",
                "is_speech_and_tongue": False,
                "model": MODEL_NAME,
                "error": str(e),
            }

            append_log(record)
            add_unclear_record(record)

            print(f"Result: ERROR")
            print(f"Error: {e}")
            print("-" * 80)
            continue

        is_speech_and_tongue = final_answer == "YES"

        record = {
            "index": index,
            "reference": reference,
            "text": text,
            "answer": final_answer,
            "is_speech_and_tongue": is_speech_and_tongue,
            "model": MODEL_NAME,
            "response": response,
        }

        if is_speech_and_tongue:
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
        print(
            f"Totals this run: "
            f"YES={yes_count}, NO={no_count}, "
            f"UNCLEAR={unclear_count}, ERROR={error_count}, SKIPPED={skipped_count}"
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
    print(f"Total matching references in output: {len(final_refs)}")
    print(f"Output written to: {OUTPUT_PATH}")
    print(f"Log written to: {LOG_PATH}")
    print(f"Unclear records written to: {UNCLEAR_PATH}")


if __name__ == "__main__":
    main()