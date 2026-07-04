import json
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


# ============================================================
# Config
# ============================================================

# Set to an int like 5 while testing. Set to None for full run.
TEST_LIMIT = None

MODEL_NAME = "qwen3:14b"

PLAN_TITLE = "The Prophets' Future Hope"
PLAN_SLUG = "prophets-hope"
PLAN_DESCRIPTION = "a collection of passages that explore the future hopes of the major and minor prophets"
PLAN_IMAGE_URL = ""

# Short timeout keeps a bad Ollama call from hanging the whole run.
OLLAMA_TIMEOUT_SECONDS = 90

# Debug printing. Keep these on while testing parser/model behavior.
PRINT_RAW_OLLAMA_OUTPUT = True
PRINT_CLEANED_OLLAMA_OUTPUT = True
PRINT_PROMPT_SENT_TO_OLLAMA = False
MAX_DEBUG_CHARS = None  # Set to an int like 4000 if output is too noisy.

SCRIPT_DIR = Path(__file__).resolve().parent

POSSIBLE_REPO_ROOTS = [
    Path(r"C:\git_repos\bible-data"),
    Path(r"C:\git_repos\bible_data"),
    SCRIPT_DIR.parents[1] if len(SCRIPT_DIR.parents) > 1 else SCRIPT_DIR.parent,
]

REPO_ROOT = None
VERSEFETCH_DIR = None

for root in POSSIBLE_REPO_ROOTS:
    candidate = root / "WorldEnglishBible"
    if (candidate / "VerseFetch.py").exists():
        REPO_ROOT = root
        VERSEFETCH_DIR = candidate
        break

if VERSEFETCH_DIR is None:
    raise FileNotFoundError(
        "Could not find WorldEnglishBible/VerseFetch.py. Checked:\n"
        + "\n".join(str(root / "WorldEnglishBible") for root in POSSIBLE_REPO_ROOTS)
    )

sys.path.insert(0, str(VERSEFETCH_DIR))

import VerseFetch  # noqa: E402
from VerseFetch import iter_verses  # noqa: E402


# ============================================================
# Basic file helpers
# ============================================================

def choose_json_file():
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        title="Choose JSON list of verse references",
        filetypes=[
            ("JSON files", "*.json"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()

    if not path:
        return None

    return Path(path)


def load_json_list(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in: {path}")

    cleaned = []
    for item in data:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())

    return cleaned


def save_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def reset_file(path):
    if path.exists():
        path.unlink()


# ============================================================
# Bible text helpers
# ============================================================

def get_reference_text(reference):
    verses = list(iter_verses(reference))

    if not verses:
        raise ValueError(f"No verses found for reference: {reference}")

    parts = []

    for verse in verses:
        verse_ref = verse.get("reference", reference)
        verse_text = verse.get("text", "").strip()
        if verse_text:
            parts.append(f"{verse_ref} {verse_text}")

    text = "\n".join(parts).strip()

    if not text:
        raise ValueError(f"No verse text found for reference: {reference}")

    return text


def truncate_text(text, max_chars=6000):
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


# ============================================================
# Ollama title generation
# ============================================================


def debug_clip(text):
    if text is None:
        return ""
    text = str(text)
    if MAX_DEBUG_CHARS is not None and len(text) > MAX_DEBUG_CHARS:
        return text[:MAX_DEBUG_CHARS] + "\n... [debug output clipped]"
    return text


def print_debug_block(label, text):
    print()
    print("=" * 100)
    print(label)
    print("=" * 100)
    printable = debug_clip(text)
    if printable:
        print(printable)
    else:
        print("[EMPTY]")
    print("=" * 100)
    print()

def run_ollama(prompt):
    """
    Uses `ollama run` so Qwen can still think normally.
    We do NOT use /no_think here.
    """

    result = subprocess.run(
        ["ollama", "run", MODEL_NAME],
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }


def strip_thinking(text):
    """
    Removes Qwen/Ollama thinking while keeping the final answer.

    Handles both formats Qwen commonly emits through `ollama run`:
    - <think> ... </think> Final title
    - Thinking... ...done thinking. Final title

    Your current output uses the second format, not XML tags.
    """

    if not text:
        return ""

    cleaned = text.strip()

    # Remove complete XML-style think blocks.
    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    # If a closing XML think tag remains, keep only what follows it.
    if "</think>" in cleaned.lower():
        parts = re.split(r"</think>", cleaned, flags=re.IGNORECASE)
        cleaned = parts[-1].strip()

    # If Qwen prints CLI-style thinking, keep only what follows the marker.
    # Example:
    #   Thinking...
    #   ...reasoning...
    #   ...done thinking.
    #
    #   Vision of the Measured City
    done_thinking_match = re.search(
        r"(?:^|\n)\s*\.\.\.\s*done thinking\.\s*",
        cleaned,
        flags=re.IGNORECASE,
    )
    if done_thinking_match:
        cleaned = cleaned[done_thinking_match.end():].strip()

    # If an opening XML think tag remains without a close, drop through it.
    cleaned = re.sub(
        r"^.*?<think>",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    # Last-resort protection: if the text still starts with Thinking...,
    # use the final non-empty line instead of the first line.
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if lines and re.fullmatch(r"thinking\.\.\.?", lines[0], flags=re.IGNORECASE):
        return lines[-1].strip()

    return cleaned


def extract_title_from_final_answer(text):
    """
    Extracts a short title from the non-thinking answer.
    This accepts either plain text or simple JSON.
    """

    final = strip_thinking(text)

    if not final:
        return ""

    # Try JSON object first: {"title": "..."}
    json_match = re.search(r"\{.*\}", final, flags=re.DOTALL)
    if json_match:
        try:
            obj = json.loads(json_match.group(0))
            title = str(obj.get("title", "")).strip()
            if title:
                return clean_title(title)
        except Exception:
            pass

    # Accept common labelled output.
    label_match = re.search(
        r"(?:^|\n)\s*(?:title|passage title)\s*[:\-]\s*(.+)",
        final,
        flags=re.IGNORECASE,
    )
    if label_match:
        return clean_title(label_match.group(1))

    # Otherwise use the first non-empty line.
    for line in final.splitlines():
        line = line.strip()
        if line:
            return clean_title(line)

    return ""


def clean_title(title):
    title = title.strip()

    # Remove markdown, quotes, bullets, list numbers.
    title = re.sub(r"^#+\s*", "", title)
    title = re.sub(r"^[-*•]\s*", "", title)
    title = re.sub(r"^\d+[.)]\s*", "", title)
    title = title.strip(" \t\r\n\"'“”‘’`.,;:")

    # Remove accidental labels again.
    title = re.sub(
        r"^(title|passage title)\s*[:\-]\s*",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    # Keep it title-like and not enormous.
    words = title.split()
    if len(words) > 8:
        title = " ".join(words[:8])

    # Remove characters that would make the markdown heading ugly.
    title = title.replace("\n", " ").replace("\r", " ")
    title = re.sub(r"\s+", " ", title).strip()

    return title


def fallback_title(reference):
    book = reference.split()[0]
    if len(reference.split()) >= 2 and reference.split()[0] in {"1", "2", "3"}:
        book = " ".join(reference.split()[:2])
    return f"{book} Reading"


def generate_passage_title(reference, verse_text, raw_log_path):
    prompt = f"""
You are creating short reading-plan passage titles.

Think briefly. Use no more than 5 short sentences of reasoning.

Return only a short Title Case Bible passage title.
Do not include the reference.
Title should be reflective of the content and distinctive between other old testament prophecies of future hope
Good Examples:
Valley of Dry Bones
Parable of Josephs Twig
New Growth Metaphor for Israel's Return

Avoid titles that could go with many prophecy
Bad Examples:
Israel's Regathering
Ezekiel Prophecy
Prophecy of Hope

after thinking, give only the final title.

Rules for the final title:
- 2 to 7 words
- No quotation marks
- No markdown
- No colon
- Do not include the Bible reference
- Do not write explanation
- Do not write multiple options

Bible reference:
{reference}

Passage text:
{truncate_text(verse_text)}

Return only the passage title.
""".strip()

    if PRINT_PROMPT_SENT_TO_OLLAMA:
        print_debug_block(f"PROMPT SENT TO OLLAMA FOR {reference}", prompt)

    response = run_ollama(prompt)
    raw = response["stdout"]
    cleaned = strip_thinking(raw)
    title = extract_title_from_final_answer(raw)

    if response["stderr"].strip():
        print_debug_block(f"OLLAMA STDERR FOR {reference}", response["stderr"])

    if PRINT_RAW_OLLAMA_OUTPUT:
        print_debug_block(f"RAW OLLAMA STDOUT FOR {reference}", raw)

    if PRINT_CLEANED_OLLAMA_OUTPUT:
        print_debug_block(f"AFTER THINK STRIP FOR {reference}", cleaned)

    print(f"  Extracted title before fallback: {title or '[EMPTY]'}")

    append_jsonl(raw_log_path, {
        "reference": reference,
        "returncode": response["returncode"],
        "stderr": response["stderr"],
        "raw_stdout": raw,
        "after_think_strip": cleaned,
        "extracted_title": title,
    })

    if title:
        return title

    return fallback_title(reference)


# ============================================================
# Markdown plan builder
# ============================================================

def build_frontmatter():
    return "\n".join([
        f"title: {PLAN_TITLE}",
        f"slug: {PLAN_SLUG}",
        f"description: {PLAN_DESCRIPTION}",
        f"image_url: {PLAN_IMAGE_URL}",
        "---",
        "",
    ])


def build_day_block(day_number, reference, passage_title):
    return "\n".join([
        f"# Day {day_number}: {reference} {passage_title}",
        "",
        "::scripture",
        reference,
        "::",
        "",
    ])


def build_reading_plan(input_path):
    references = load_json_list(input_path)

    if TEST_LIMIT is not None:
        references = references[:TEST_LIMIT]

    output_md_path = input_path.with_name(f"{input_path.stem}_reading_plan.md")
    titles_json_path = input_path.with_name(f"{input_path.stem}_reading_plan_titles.json")
    raw_log_path = input_path.with_name(f"{input_path.stem}_reading_plan_raw_ollama.jsonl")
    errors_path = input_path.with_name(f"{input_path.stem}_reading_plan_errors.json")

    reset_file(raw_log_path)

    print(f"Using VerseFetch from: {VerseFetch.__file__}")
    print(f"Using Ollama model: {MODEL_NAME}")
    print(f"Loaded {len(references)} references.")
    print()

    markdown_parts = [build_frontmatter()]
    title_records = []
    errors = []

    total = len(references)

    for index, reference in enumerate(references, start=1):
        print(f"[{index}/{total}] Building Day {index}: {reference}")

        try:
            verse_text = get_reference_text(reference)
            title = generate_passage_title(reference, verse_text, raw_log_path)

            markdown_parts.append(build_day_block(index, reference, title))

            title_records.append({
                "day": index,
                "reference": reference,
                "title": title,
                "text": verse_text,
            })

            print(f"  Title: {title}")

        except Exception as e:
            errors.append({
                "day": index,
                "reference": reference,
                "error": str(e),
            })

            title = fallback_title(reference)
            markdown_parts.append(build_day_block(index, reference, title))

            print(f"  ERROR: {e}")
            print(f"  Fallback title: {title}")

        print("-" * 80)

    save_text(output_md_path, "\n".join(markdown_parts).strip() + "\n")
    save_json(titles_json_path, title_records)

    if errors:
        save_json(errors_path, errors)

    print()
    print("Done.")
    print(f"Markdown plan written to: {output_md_path}")
    print(f"Titles written to: {titles_json_path}")
    print(f"Raw Ollama log written to: {raw_log_path}")

    if errors:
        print(f"Errors written to: {errors_path}")
        print(f"Error count: {len(errors)}")

    return output_md_path, titles_json_path, raw_log_path, errors_path if errors else None


# ============================================================
# Main
# ============================================================

def main():
    input_path = choose_json_file()

    if input_path is None:
        print("No file selected.")
        return

    try:
        output_md_path, titles_json_path, raw_log_path, errors_path = build_reading_plan(input_path)

        message = (
            "Reading plan generated.\n\n"
            f"Markdown plan:\n{output_md_path}\n\n"
            f"Titles JSON:\n{titles_json_path}\n\n"
            f"Raw Ollama log:\n{raw_log_path}"
        )

        if errors_path:
            message += f"\n\nErrors:\n{errors_path}"

        messagebox.showinfo("Done", message)

    except Exception as e:
        messagebox.showerror("Error", str(e))
        raise


if __name__ == "__main__":
    main()
