#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "gTTS",
#   "pygame",
# ]
# ///

"""
Text-to-Speech Desktop App
Usage: uv run tts_app.py
"""

import os
import sys
import threading
import tempfile
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

from gtts import gTTS
import pygame


# ---------------------------------------------------------------------------
# Language options: display name -> gTTS language code
# ---------------------------------------------------------------------------
LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Mandarin)": "zh-CN",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Greek": "el",
    "Czech": "cs",
    "Romanian": "ro",
    "Hungarian": "hu",
    "Ukrainian": "uk",
    "Vietnamese": "vi",
    "Thai": "th",
    "Indonesian": "id",
}


class TTSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Text-to-Speech Converter")
        self.resizable(False, False)
        self._center_window(580, 420)

        # State
        self._file_path = tk.StringVar(value="No file selected")
        self._lang_var = tk.StringVar(value="English")
        self._status_var = tk.StringVar(value="Ready.")
        self._temp_mp3 = None
        self._playing = False

        pygame.mixer.init()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 18, "pady": 8}

        # ── Title ──────────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg="#2c3e50")
        title_frame.pack(fill="x")
        tk.Label(
            title_frame,
            text="🔊  Text-to-Speech Converter",
            font=("Helvetica", 17, "bold"),
            bg="#2c3e50",
            fg="white",
            pady=14,
        ).pack()

        # ── File selection ─────────────────────────────────────────────
        file_frame = tk.LabelFrame(self, text=" 1.  Select a text file ", font=("Helvetica", 11, "bold"), **pad)
        file_frame.pack(fill="x", **pad)

        inner = tk.Frame(file_frame)
        inner.pack(fill="x", padx=8, pady=6)

        tk.Label(inner, textvariable=self._file_path, anchor="w",
                 width=48, relief="sunken", bg="#f0f0f0").pack(side="left", padx=(0, 8))
        tk.Button(inner, text="Browse…", command=self._browse_file,
                  bg="#3498db", fg="white", relief="flat",
                  padx=10, cursor="hand2").pack(side="left")

        # ── Language selection ─────────────────────────────────────────
        lang_frame = tk.LabelFrame(self, text=" 2.  Choose language ", font=("Helvetica", 11, "bold"), **pad)
        lang_frame.pack(fill="x", **pad)

        combo = ttk.Combobox(
            lang_frame,
            textvariable=self._lang_var,
            values=sorted(LANGUAGES.keys()),
            state="readonly",
            width=30,
            font=("Helvetica", 11),
        )
        combo.pack(anchor="w", padx=8, pady=8)

        # ── Action buttons ─────────────────────────────────────────────
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        self._speak_btn = tk.Button(
            btn_frame, text="▶  Speak", width=14, font=("Helvetica", 12, "bold"),
            bg="#27ae60", fg="white", relief="flat", cursor="hand2",
            command=self._on_speak,
        )
        self._speak_btn.grid(row=0, column=0, padx=8)

        self._save_btn = tk.Button(
            btn_frame, text="💾  Save MP3", width=14, font=("Helvetica", 12, "bold"),
            bg="#8e44ad", fg="white", relief="flat", cursor="hand2",
            command=self._on_save,
        )
        self._save_btn.grid(row=0, column=1, padx=8)

        self._stop_btn = tk.Button(
            btn_frame, text="⏹  Stop", width=14, font=("Helvetica", 12, "bold"),
            bg="#e74c3c", fg="white", relief="flat", cursor="hand2",
            command=self._on_stop, state="disabled",
        )
        self._stop_btn.grid(row=0, column=2, padx=8)

        # ── Progress bar ───────────────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.pack(pady=(0, 6))

        # ── Status bar ────────────────────────────────────────────────
        tk.Label(self, textvariable=self._status_var, anchor="w",
                 relief="sunken", bg="#ecf0f1", font=("Helvetica", 10)).pack(
            fill="x", padx=18, pady=(0, 12)
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _set_status(self, msg: str):
        self._status_var.set(msg)
        self.update_idletasks()

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self._speak_btn.config(state=state)
        self._save_btn.config(state=state)
        self._stop_btn.config(state="normal" if busy else "disabled")
        if busy:
            self._progress.start(10)
        else:
            self._progress.stop()

    # ------------------------------------------------------------------
    # File browsing
    # ------------------------------------------------------------------
    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._file_path.set(path)
            self._set_status(f"File loaded: {os.path.basename(path)}")

    # ------------------------------------------------------------------
    # Core TTS
    # ------------------------------------------------------------------
    def _read_file(self) -> str | None:
        path = self._file_path.get()
        if path == "No file selected" or not os.path.isfile(path):
            messagebox.showerror("No file", "Please select a valid text file first.")
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
        if not text:
            messagebox.showerror("Empty file", "The selected file is empty.")
            return None
        return text

    def _generate_mp3(self, text: str) -> str:
        lang_code = LANGUAGES[self._lang_var.get()]
        tts = gTTS(text=text, lang=lang_code)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.close()
        tts.save(tmp.name)
        return tmp.name

    # ------------------------------------------------------------------
    # Speak
    # ------------------------------------------------------------------
    def _on_speak(self):
        text = self._read_file()
        if text is None:
            return
        self._set_busy(True)
        self._set_status("Generating speech… (requires internet)")
        threading.Thread(target=self._speak_worker, args=(text,), daemon=True).start()

    def _speak_worker(self, text: str):
        try:
            mp3_path = self._generate_mp3(text)
            self._temp_mp3 = mp3_path
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play()
            self._playing = True
            self.after(0, lambda: self._set_status("Playing…"))
            # Poll until playback finishes
            while pygame.mixer.music.get_busy() and self._playing:
                pygame.time.Clock().tick(10)
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Error", str(exc)))
        finally:
            self._playing = False
            self.after(0, lambda: self._set_busy(False))
            self.after(0, lambda: self._set_status("Done."))

    # ------------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------------
    def _on_stop(self):
        self._playing = False
        pygame.mixer.music.stop()
        self._set_status("Stopped.")
        self._set_busy(False)

    # ------------------------------------------------------------------
    # Save MP3
    # ------------------------------------------------------------------
    def _on_save(self):
        text = self._read_file()
        if text is None:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 audio", "*.mp3")],
            title="Save MP3 as…",
        )
        if not save_path:
            return
        self._set_busy(True)
        self._set_status("Generating and saving… (requires internet)")
        threading.Thread(target=self._save_worker, args=(text, save_path), daemon=True).start()

    def _save_worker(self, text: str, save_path: str):
        try:
            lang_code = LANGUAGES[self._lang_var.get()]
            tts = gTTS(text=text, lang=lang_code)
            tts.save(save_path)
            self.after(0, lambda: messagebox.showinfo("Saved", f"MP3 saved to:\n{save_path}"))
            self.after(0, lambda: self._set_status(f"Saved: {os.path.basename(save_path)}"))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Error", str(exc)))
            self.after(0, lambda: self._set_status("Error saving file."))
        finally:
            self.after(0, lambda: self._set_busy(False))


def main():
    app = TTSApp()
    app.mainloop()


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
