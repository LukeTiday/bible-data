import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


# ============================================================
# Config
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

POSSIBLE_VERSEFETCH_DIRS = [
    Path(r"C:\git_repos\bible_data\WorldEnglishBible"),
    Path(r"C:\git_repos\bible-data\WorldEnglishBible"),
    SCRIPT_DIR.parent / "WorldEnglishBible",
    SCRIPT_DIR.parents[1] / "WorldEnglishBible",
]

VERSEFETCH_DIR = None

for possible_dir in POSSIBLE_VERSEFETCH_DIRS:
    if (possible_dir / "VerseFetch.py").exists():
        VERSEFETCH_DIR = possible_dir
        break

if VERSEFETCH_DIR is None:
    raise FileNotFoundError(
        "Could not find VerseFetch.py. Checked:\n"
        + "\n".join(str(p) for p in POSSIBLE_VERSEFETCH_DIRS)
    )

sys.path.insert(0, str(VERSEFETCH_DIR))

import os  # noqa: E402
os.chdir(str(VERSEFETCH_DIR))

from VerseFetch import iter_verses  # noqa: E402


APP_TITLE = "Verse JSON Review"

# ============================================================
# Theme
# ============================================================

BG = "#151515"
PANEL_BG = "#1f1f1f"
TEXT_BG = "#202124"
TEXT_FG = "#eeeeee"
MUTED_FG = "#aaaaaa"
HEADER_FG = "#ffffff"
BUTTON_BG = "#2f2f2f"
BUTTON_FG = "#eeeeee"
BUTTON_ACTIVE_BG = "#3a3a3a"
BUTTON_DISABLED_BG = "#242424"
BUTTON_DISABLED_FG = "#666666"


# ============================================================
# JSON helpers
# ============================================================

def load_json_list(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in: {path}")

    cleaned = []

    for item in data:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())

    return cleaned


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sidecar_paths(input_path):
    input_path = Path(input_path)

    state_path = input_path.with_name(f"{input_path.stem}.review_state.json")
    accepted_path = input_path.with_name(f"{input_path.stem}.reviewed.json")

    return state_path, accepted_path


def load_review_state(state_path):
    if not state_path.exists():
        return {
            "accepted": [],
            "rejected": [],
            "reviewed_sources": [],
            "history": [],
        }

    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {
            "accepted": [],
            "rejected": [],
            "reviewed_sources": [],
            "history": [],
        }

    data.setdefault("accepted", [])
    data.setdefault("rejected", [])
    data.setdefault("reviewed_sources", [])
    data.setdefault("history", [])

    # Backward compatibility for older state files that did not have reviewed_sources.
    if not data["reviewed_sources"]:
        data["reviewed_sources"] = dedupe_preserve_order(
            data.get("accepted", []) + data.get("rejected", [])
        )

    return data


def dedupe_preserve_order(items):
    seen = set()
    result = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result


# ============================================================
# Reference display + adjustment helpers
# ============================================================

SINGLE_REF_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)$"
)

SAME_CHAPTER_RANGE_RE = re.compile(
    r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)-(\d+)$"
)


def expected_refs_for_simple_reference(reference):
    """
    Returns expected verse refs for simple references.

    Supports:
      Matthew 5:5
      Jeremiah 3:12-18

    For more complex ranges, returns None and lets VerseFetch handle it normally.
    """

    reference = reference.strip()

    single_match = SINGLE_REF_RE.match(reference)
    if single_match:
        book = single_match.group(1).strip()
        chapter = int(single_match.group(2))
        verse = int(single_match.group(3))
        return [f"{book} {chapter}:{verse}"]

    range_match = SAME_CHAPTER_RANGE_RE.match(reference)
    if range_match:
        book = range_match.group(1).strip()
        chapter = int(range_match.group(2))
        start_verse = int(range_match.group(3))
        end_verse = int(range_match.group(4))

        if end_verse < start_verse:
            return None

        return [
            f"{book} {chapter}:{verse}"
            for verse in range(start_verse, end_verse + 1)
        ]

    return None


def get_reference_text(reference):
    """
    Fetches verse text for a reference or range.

    Defensive behavior:
    - For single verses, only displays the first returned verse.
    - For simple same-chapter ranges, displays only the expected number of verses.
    - For complex references, falls back to whatever VerseFetch returns.
    """

    try:
        verses = list(iter_verses(reference))
    except Exception as e:
        return f"[Error fetching verse text]\n\n{e}"

    if not verses:
        return "[No verse text found.]"

    expected_refs = expected_refs_for_simple_reference(reference)

    # Single verse: keep only the first returned verse.
    if expected_refs and len(expected_refs) == 1:
        first_verse = verses[0]
        text = first_verse.get("text", "").strip()

        if not text:
            return f"{reference} [No verse text found.]"

        return f"{reference} {text}"

    # Same-chapter range: keep only expected number of verses and label them ourselves.
    if expected_refs and len(expected_refs) > 1:
        verses = verses[:len(expected_refs)]

        parts = []

        for expected_ref, verse in zip(expected_refs, verses):
            text = verse.get("text", "").strip()

            if text:
                parts.append(f"{expected_ref} {text}")

        return "\n\n".join(parts).strip() or "[No verse text found.]"

    # Fallback for complex references.
    parts = []

    for verse in verses:
        verse_ref = verse.get("reference", "").strip()
        verse_text = verse.get("text", "").strip()

        if not verse_text:
            continue

        if verse_ref:
            parts.append(f"{verse_ref} {verse_text}")
        else:
            parts.append(verse_text)

    return "\n\n".join(parts).strip() or "[No verse text found.]"


def parse_simple_same_chapter_reference(reference):
    """
    Supports:
      Jeremiah 3:12
      Jeremiah 3:12-18

    Returns:
      {
        "book": "Jeremiah",
        "chapter": 3,
        "start_verse": 12,
        "end_verse": 18
      }

    Returns None for unsupported or cross-chapter references.
    """

    reference = reference.strip()

    single_match = SINGLE_REF_RE.match(reference)
    if single_match:
        verse = int(single_match.group(3))

        return {
            "book": single_match.group(1).strip(),
            "chapter": int(single_match.group(2)),
            "start_verse": verse,
            "end_verse": verse,
        }

    range_match = SAME_CHAPTER_RANGE_RE.match(reference)
    if range_match:
        start_verse = int(range_match.group(3))
        end_verse = int(range_match.group(4))

        if end_verse < start_verse:
            return None

        return {
            "book": range_match.group(1).strip(),
            "chapter": int(range_match.group(2)),
            "start_verse": start_verse,
            "end_verse": end_verse,
        }

    return None


def format_simple_reference(book, chapter, start_verse, end_verse):
    if start_verse == end_verse:
        return f"{book} {chapter}:{start_verse}"

    return f"{book} {chapter}:{start_verse}-{end_verse}"


def verse_exists(reference):
    """
    Checks whether a single exact verse exists.
    This stops adjustment at chapter boundaries without wrapping.
    """

    try:
        verses = list(iter_verses(reference))
    except Exception:
        return False

    return bool(verses)


def get_adjusted_reference(reference, action):
    """
    action values:
      add_start
      remove_start
      remove_end
      add_end

    Stops at chapter boundaries by refusing adjustments that point to nonexistent verses.
    Does not wrap across chapters.
    """

    parsed = parse_simple_same_chapter_reference(reference)

    if not parsed:
        return None, "Only simple same-chapter references can be adjusted."

    book = parsed["book"]
    chapter = parsed["chapter"]
    start_verse = parsed["start_verse"]
    end_verse = parsed["end_verse"]

    if action == "add_start":
        new_start = start_verse - 1
        new_end = end_verse

        if new_start < 1:
            return None, "Already at the beginning of the chapter."

        test_ref = format_simple_reference(book, chapter, new_start, new_start)

        if not verse_exists(test_ref):
            return None, "Previous verse does not exist."

        return format_simple_reference(book, chapter, new_start, new_end), None

    if action == "remove_start":
        if start_verse >= end_verse:
            return None, "Cannot shrink below one verse."

        new_start = start_verse + 1
        new_end = end_verse

        return format_simple_reference(book, chapter, new_start, new_end), None

    if action == "remove_end":
        if start_verse >= end_verse:
            return None, "Cannot shrink below one verse."

        new_start = start_verse
        new_end = end_verse - 1

        return format_simple_reference(book, chapter, new_start, new_end), None

    if action == "add_end":
        new_start = start_verse
        new_end = end_verse + 1

        test_ref = format_simple_reference(book, chapter, new_end, new_end)

        if not verse_exists(test_ref):
            return None, "Already at the end of the chapter."

        return format_simple_reference(book, chapter, new_start, new_end), None

    return None, f"Unknown adjustment action: {action}"


# ============================================================
# Review app
# ============================================================

class VerseReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("940x580")
        self.root.minsize(760, 450)

        self.input_path = None
        self.state_path = None
        self.accepted_path = None

        self.all_refs = []
        self.state = {
            "accepted": [],
            "rejected": [],
            "reviewed_sources": [],
            "history": [],
        }

        # current_source_ref is the original input item being reviewed.
        # current_ref is the editable reference that can be adjusted before accept.
        self.current_source_ref = None
        self.current_ref = None
        
        self.build_ui()
        self.bind_keys()

        self.open_json_file()
    def make_button(self, parent, text, command, font_size=11, padx=14, pady=8):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", font_size),
            padx=padx,
            pady=pady,
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE_BG,
            activeforeground=BUTTON_FG,
            disabledforeground=BUTTON_DISABLED_FG,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
    def build_ui(self):
        self.root.configure(bg=BG)

        self.main = tk.Frame(self.root, bg=BG, padx=24, pady=20)
        self.main.pack(fill="both", expand=True)

        self.file_label = tk.Label(
            self.main,
            text="No file loaded",
            font=("Segoe UI", 9),
            bg=BG,
            fg=MUTED_FG,
            anchor="w",
        )
        self.file_label.pack(fill="x", pady=(0, 8))

        self.progress_label = tk.Label(
            self.main,
            text="",
            font=("Segoe UI", 10),
            bg=BG,
            fg=MUTED_FG,
            anchor="w",
        )
        self.progress_label.pack(fill="x", pady=(0, 12))

        self.reference_label = tk.Label(
            self.main,
            text="",
            font=("Segoe UI", 22, "bold"),
            bg=BG,
            fg=HEADER_FG,
            anchor="w",
        )
        self.reference_label.pack(fill="x", pady=(0, 14))

        self.verse_text = tk.Text(
            self.main,
            wrap="word",
            height=12,
            font=("Segoe UI", 14),
            bg=TEXT_BG,
            fg=TEXT_FG,
            insertbackground=TEXT_FG,
            selectbackground="#444444",
            selectforeground="#ffffff",
            relief="flat",
            padx=18,
            pady=18,
        )
        self.verse_text.pack(fill="both", expand=True)
        self.verse_text.configure(state="disabled")

        self.button_frame = tk.Frame(self.main, bg=BG)
        self.button_frame.pack(fill="x", pady=(18, 0))

        self.open_button = self.make_button(
            self.button_frame,
            text="Open JSON",
            command=self.open_json_file,
            font_size=11,
            padx=14,
        )
        self.open_button.pack(side="left")

        self.undo_button = self.make_button(
            self.button_frame,
            text="Undo Last",
            command=self.undo_last,
            font_size=11,
            padx=14,
        )
        self.undo_button.pack(side="left", padx=(10, 0))

        self.adjust_frame = tk.Frame(self.button_frame, bg=BG)
        self.adjust_frame.pack(side="left", padx=(18, 0))

        self.add_start_button = self.make_button(
            self.adjust_frame,
            text="+[",
            command=lambda: self.adjust_current_reference("add_start"),
            font_size=11,
            padx=10,
        )
        self.add_start_button.pack(side="left")

        self.remove_start_button = self.make_button(
            self.adjust_frame,
            text="-[",
            command=lambda: self.adjust_current_reference("remove_start"),
            font_size=11,
            padx=10,
        )
        self.remove_start_button.pack(side="left", padx=(6, 0))

        self.remove_end_button = self.make_button(
            self.adjust_frame,
            text="]-",
            command=lambda: self.adjust_current_reference("remove_end"),
            font_size=11,
            padx=10,
        )
        self.remove_end_button.pack(side="left", padx=(6, 0))

        self.add_end_button = self.make_button(
            self.adjust_frame,
            text="]+",
            command=lambda: self.adjust_current_reference("add_end"),
            font_size=11,
            padx=10,
        )
        self.add_end_button.pack(side="left", padx=(6, 0))

        self.reject_button = self.make_button(
            self.button_frame,
            text="Reject",
            command=self.reject_current,
            font_size=12,
            padx=22,
        )
        self.reject_button.pack(side="right")

        self.accept_button = self.make_button(
            self.button_frame,
            text="Accept",
            command=self.accept_current,
            font_size=12,
            padx=22,
        )
        self.accept_button.pack(side="right", padx=(0, 10))

        self.help_label = tk.Label(
            self.main,
            text="Keyboard: A = accept, R = reject, U = undo, O = open file, Esc = quit",
            font=("Segoe UI", 9),
            bg=BG,
            fg=MUTED_FG,
            anchor="center",
        )
        self.help_label.pack(fill="x", pady=(12, 0))

    def bind_keys(self):
        self.root.bind("a", lambda event: self.accept_current())
        self.root.bind("A", lambda event: self.accept_current())

        self.root.bind("r", lambda event: self.reject_current())
        self.root.bind("R", lambda event: self.reject_current())

        self.root.bind("u", lambda event: self.undo_last())
        self.root.bind("U", lambda event: self.undo_last())

        self.root.bind("o", lambda event: self.open_json_file())
        self.root.bind("O", lambda event: self.open_json_file())

        self.root.bind("<Escape>", lambda event: self.root.quit())

    def open_json_file(self):
        path = filedialog.askopenfilename(
            title="Choose verse reference JSON",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            if self.input_path is None:
                self.set_empty_state("No file selected.")
            return

        try:
            self.input_path = Path(path)
            self.state_path, self.accepted_path = sidecar_paths(self.input_path)

            self.all_refs = load_json_list(self.input_path)
            self.state = load_review_state(self.state_path)

            self.save_all_state()

            self.file_label.configure(text=f"Input: {self.input_path}")
            self.show_next_unreviewed()

        except Exception as e:
            messagebox.showerror("Open Error", str(e))
            self.set_empty_state(f"Error loading file:\n\n{e}")

    def accepted_set(self):
        return set(self.state.get("accepted", []))

    def rejected_set(self):
        return set(self.state.get("rejected", []))

    def reviewed_source_set(self):
        return set(self.state.get("reviewed_sources", []))

    def get_next_unreviewed_ref(self):
        reviewed_sources = self.reviewed_source_set()

        for ref in self.all_refs:
            if ref not in reviewed_sources:
                return ref

        return None

    def save_all_state(self):
        if not self.state_path or not self.accepted_path:
            return

        self.state["accepted"] = dedupe_preserve_order(self.state.get("accepted", []))
        self.state["rejected"] = dedupe_preserve_order(self.state.get("rejected", []))
        self.state["reviewed_sources"] = dedupe_preserve_order(
            self.state.get("reviewed_sources", [])
        )
        self.state["history"] = self.state.get("history", [])

        save_json(self.state_path, self.state)
        save_json(self.accepted_path, self.state["accepted"])

    def show_next_unreviewed(self):
        next_ref = self.get_next_unreviewed_ref()

        if next_ref is None:
            self.current_source_ref = None
            self.current_ref = None
            self.show_complete()
            return

        self.current_source_ref = next_ref
        self.current_ref = next_ref

        self.show_current()

    def show_current(self):
        if not self.current_ref:
            self.show_next_unreviewed()
            return

        total = len(self.all_refs)
        accepted = len(self.state.get("accepted", []))
        rejected = len(self.state.get("rejected", []))
        reviewed = len(self.state.get("reviewed_sources", []))
        remaining = max(total - reviewed, 0)

        source_note = ""
        if self.current_source_ref and self.current_source_ref != self.current_ref:
            source_note = f"  |  Original: {self.current_source_ref}"

        self.progress_label.configure(
            text=(
                f"Total: {total}  |  "
                f"Accepted: {accepted}  |  "
                f"Rejected: {rejected}  |  "
                f"Remaining: {remaining}"
                f"{source_note}"
            )
        )

        self.reference_label.configure(text=self.current_ref)
        self.set_verse_text(get_reference_text(self.current_ref))

        self.accept_button.configure(state="normal")
        self.reject_button.configure(state="normal")
        self.undo_button.configure(
            state="normal" if self.state.get("history") else "disabled"
        )

        adjust_state = (
            "normal"
            if parse_simple_same_chapter_reference(self.current_ref)
            else "disabled"
        )

        self.add_start_button.configure(state=adjust_state)
        self.remove_start_button.configure(state=adjust_state)
        self.remove_end_button.configure(state=adjust_state)
        self.add_end_button.configure(state=adjust_state)

    def set_verse_text(self, text):
        self.verse_text.configure(state="normal")
        self.verse_text.delete("1.0", "end")
        self.verse_text.insert("1.0", text)
        self.verse_text.configure(state="disabled")

    def adjust_current_reference(self, action):
        if not self.current_ref:
            return

        new_ref, error = get_adjusted_reference(self.current_ref, action)

        if error:
            messagebox.showinfo("Cannot Adjust Reference", error)
            return

        if not new_ref:
            return

        old_ref = self.current_ref
        self.current_ref = new_ref

        self.state["history"].append({
            "action": "adjusted",
            "source_reference": self.current_source_ref,
            "old_reference": old_ref,
            "new_reference": new_ref,
        })

        self.save_all_state()

        print(f"Adjusted: {old_ref} -> {new_ref}")
        self.show_current()

    def accept_current(self):
        if not self.current_ref or not self.current_source_ref:
            return

        source_ref = self.current_source_ref
        final_ref = self.current_ref

        if final_ref not in self.state["accepted"]:
            self.state["accepted"].append(final_ref)

        if source_ref in self.state["rejected"]:
            self.state["rejected"].remove(source_ref)

        if source_ref not in self.state["reviewed_sources"]:
            self.state["reviewed_sources"].append(source_ref)

        self.state["history"].append({
            "action": "accepted",
            "source_reference": source_ref,
            "final_reference": final_ref,
        })

        self.save_all_state()

        print(f"Accepted: {source_ref} -> {final_ref}")
        self.show_next_unreviewed()

    def reject_current(self):
        if not self.current_ref or not self.current_source_ref:
            return

        source_ref = self.current_source_ref
        displayed_ref = self.current_ref

        if source_ref not in self.state["rejected"]:
            self.state["rejected"].append(source_ref)

        if source_ref not in self.state["reviewed_sources"]:
            self.state["reviewed_sources"].append(source_ref)

        self.state["history"].append({
            "action": "rejected",
            "source_reference": source_ref,
            "displayed_reference": displayed_ref,
        })

        self.save_all_state()

        print(f"Rejected: {source_ref}")
        self.show_next_unreviewed()

    def undo_last(self):
        history = self.state.get("history", [])

        if not history:
            return

        last = history.pop()
        action = last.get("action")

        if action == "accepted":
            source_ref = last.get("source_reference")
            final_ref = last.get("final_reference")

            if final_ref in self.state["accepted"]:
                self.state["accepted"].remove(final_ref)

            if source_ref in self.state["reviewed_sources"]:
                self.state["reviewed_sources"].remove(source_ref)

            self.current_source_ref = source_ref
            self.current_ref = final_ref or source_ref

        elif action == "rejected":
            source_ref = last.get("source_reference")
            displayed_ref = last.get("displayed_reference")

            if source_ref in self.state["rejected"]:
                self.state["rejected"].remove(source_ref)

            if source_ref in self.state["reviewed_sources"]:
                self.state["reviewed_sources"].remove(source_ref)

            self.current_source_ref = source_ref
            self.current_ref = displayed_ref or source_ref

        elif action == "adjusted":
            source_ref = last.get("source_reference")
            old_ref = last.get("old_reference")
            new_ref = last.get("new_reference")

            self.current_source_ref = source_ref or self.current_source_ref
            self.current_ref = old_ref or new_ref

        else:
            self.save_all_state()
            self.show_current()
            return

        self.save_all_state()

        print(f"Undid {action}")
        self.show_current()

    def show_complete(self):
        total = len(self.all_refs)
        accepted = len(self.state.get("accepted", []))
        rejected = len(self.state.get("rejected", []))

        self.progress_label.configure(
            text=(
                f"Review complete. Total: {total}  |  "
                f"Accepted: {accepted}  |  Rejected: {rejected}"
            )
        )

        self.reference_label.configure(text="Review complete.")
        self.set_verse_text(
            f"Accepted references were written to:\n{self.accepted_path}\n\n"
            f"Review state was written to:\n{self.state_path}"
        )

        self.accept_button.configure(state="disabled")
        self.reject_button.configure(state="disabled")
        self.undo_button.configure(
            state="normal" if self.state.get("history") else "disabled"
        )

        self.add_start_button.configure(state="disabled")
        self.remove_start_button.configure(state="disabled")
        self.remove_end_button.configure(state="disabled")
        self.add_end_button.configure(state="disabled")

    def set_empty_state(self, message):
        self.progress_label.configure(text="")
        self.reference_label.configure(text="No file loaded.")
        self.set_verse_text(message)
        self.accept_button.configure(state="disabled")
        self.reject_button.configure(state="disabled")
        self.undo_button.configure(state="disabled")

        self.add_start_button.configure(state="disabled")
        self.remove_start_button.configure(state="disabled")
        self.remove_end_button.configure(state="disabled")
        self.add_end_button.configure(state="disabled")


# ============================================================
# Main
# ============================================================

def main():
    root = tk.Tk()
    VerseReviewApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()