import json
import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


# ============================================================
# Config
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

INPUT_JSON_PATH = SCRIPT_DIR / "jesus_one_liner_proverb_references.json"
BACKUP_JSON_PATH = SCRIPT_DIR / "jesus_one_liner_proverb_references.backup.json"

VERSEFETCH_DIR = REPO_ROOT / "WorldEnglishBible"
sys.path.insert(0, str(VERSEFETCH_DIR))

from VerseFetch import iter_verses  # noqa: E402


# ============================================================
# Data helpers
# ============================================================

def load_json_list(path):
    if not path.exists():
        raise FileNotFoundError(f"Could not find JSON file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in: {path}")

    cleaned = []

    for item in data:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())

    return cleaned


def save_json_list(path, items):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def make_backup_once():
    if INPUT_JSON_PATH.exists() and not BACKUP_JSON_PATH.exists():
        shutil.copy2(INPUT_JSON_PATH, BACKUP_JSON_PATH)


def get_reference_text(reference):
    """
    Fetches only the first verse returned by VerseFetch.

    This is intentional because this review app is only for one-liner
    single-verse references like Matthew 5:5.

    Some VerseFetch behavior may return Matthew 5:5 through the end
    of the chapter for a single-verse lookup, so we defensively keep
    only the first returned verse.
    """

    verses = list(iter_verses(reference))

    if not verses:
        return f"{reference} [No verse text found.]"

    first_verse = verses[0]
    verse_text = first_verse.get("text", "").strip()

    if not verse_text:
        return f"{reference} [No verse text found.]"

    return f"{reference} {verse_text}"


# ============================================================
# UI app
# ============================================================

class VerseReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jesus One-Liner Proverb Review")
        self.root.geometry("780x420")
        self.root.minsize(600, 320)

        make_backup_once()

        self.references = load_json_list(INPUT_JSON_PATH)
        self.index = 0
        self.rejected_count = 0
        self.accepted_count = 0

        self.build_ui()
        self.bind_keys()
        self.show_current()

    def build_ui(self):
        self.root.configure(bg="#f4f4f4")

        self.main_frame = tk.Frame(self.root, bg="#f4f4f4", padx=24, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        self.progress_label = tk.Label(
            self.main_frame,
            text="",
            font=("Segoe UI", 10),
            bg="#f4f4f4",
            fg="#555555",
            anchor="w",
        )
        self.progress_label.pack(fill="x", pady=(0, 12))

        self.reference_label = tk.Label(
            self.main_frame,
            text="",
            font=("Segoe UI", 22, "bold"),
            bg="#f4f4f4",
            fg="#111111",
            anchor="w",
        )
        self.reference_label.pack(fill="x", pady=(0, 16))

        self.verse_text = tk.Text(
            self.main_frame,
            wrap="word",
            height=8,
            font=("Segoe UI", 15),
            bg="white",
            fg="#111111",
            relief="flat",
            padx=18,
            pady=18,
        )
        self.verse_text.pack(fill="both", expand=True)
        self.verse_text.configure(state="disabled")

        self.button_frame = tk.Frame(self.main_frame, bg="#f4f4f4")
        self.button_frame.pack(fill="x", pady=(18, 0))

        self.reject_button = tk.Button(
            self.button_frame,
            text="Reject / Remove",
            command=self.reject_current,
            font=("Segoe UI", 12),
            padx=18,
            pady=8,
            bg="#e8e8e8",
        )
        self.reject_button.pack(side="left")

        self.accept_button = tk.Button(
            self.button_frame,
            text="Accept / Keep",
            command=self.accept_current,
            font=("Segoe UI", 12),
            padx=18,
            pady=8,
            bg="#e8e8e8",
        )
        self.accept_button.pack(side="right")

        self.help_label = tk.Label(
            self.main_frame,
            text="Keyboard: A = accept, R = reject, Left = previous, Esc = quit",
            font=("Segoe UI", 9),
            bg="#f4f4f4",
            fg="#777777",
            anchor="center",
        )
        self.help_label.pack(fill="x", pady=(12, 0))

    def bind_keys(self):
        self.root.bind("a", lambda event: self.accept_current())
        self.root.bind("A", lambda event: self.accept_current())
        self.root.bind("r", lambda event: self.reject_current())
        self.root.bind("R", lambda event: self.reject_current())
        self.root.bind("<Left>", lambda event: self.previous())
        self.root.bind("<Escape>", lambda event: self.root.quit())

    def show_current(self):
        total = len(self.references)

        if total == 0:
            self.progress_label.configure(
                text=f"Done. Accepted this session: {self.accepted_count}. Rejected this session: {self.rejected_count}."
            )
            self.reference_label.configure(text="No references left.")
            self.set_verse_text("All candidate references have been reviewed or removed.")
            self.accept_button.configure(state="disabled")
            self.reject_button.configure(state="disabled")
            return

        if self.index >= total:
            self.index = total - 1

        if self.index < 0:
            self.index = 0

        reference = self.references[self.index]
        text = get_reference_text(reference)

        self.progress_label.configure(
            text=(
                f"{self.index + 1} of {total}  "
                f"| Accepted this session: {self.accepted_count}  "
                f"| Rejected this session: {self.rejected_count}"
            )
        )

        self.reference_label.configure(text=reference)
        self.set_verse_text(text)

        self.accept_button.configure(state="normal")
        self.reject_button.configure(state="normal")

    def set_verse_text(self, text):
        self.verse_text.configure(state="normal")
        self.verse_text.delete("1.0", "end")
        self.verse_text.insert("1.0", text)
        self.verse_text.configure(state="disabled")

    def accept_current(self):
        if not self.references:
            return

        self.accepted_count += 1
        self.index += 1

        if self.index >= len(self.references):
            self.finish_if_at_end()
        else:
            self.show_current()

    def reject_current(self):
        if not self.references:
            return

        reference = self.references[self.index]

        self.references.pop(self.index)
        self.rejected_count += 1

        save_json_list(INPUT_JSON_PATH, self.references)

        print(f"Rejected and removed: {reference}")

        if self.index >= len(self.references):
            self.index = len(self.references) - 1

        self.show_current()

    def previous(self):
        if not self.references:
            return

        self.index -= 1

        if self.index < 0:
            self.index = 0

        self.show_current()

    def finish_if_at_end(self):
        if self.index >= len(self.references):
            self.progress_label.configure(
                text=(
                    f"End reached. Total remaining in JSON: {len(self.references)}. "
                    f"Accepted this session: {self.accepted_count}. "
                    f"Rejected this session: {self.rejected_count}."
                )
            )
            self.reference_label.configure(text="Review complete.")
            self.set_verse_text(
                "You reached the end of the current list.\n\n"
                "Accepted items stayed in the JSON.\n"
                "Rejected items were removed immediately."
            )
            self.accept_button.configure(state="disabled")
            self.reject_button.configure(state="disabled")
        else:
            self.show_current()


# ============================================================
# Main
# ============================================================

def main():
    try:
        root = tk.Tk()
        app = VerseReviewApp(root)
        root.mainloop()

    except Exception as e:
        messagebox.showerror("Review App Error", str(e))
        raise


if __name__ == "__main__":
    main()