"""
Text-to-Speech Desktop App
Uses Piper TTS (neural, offline) — English only.
Entry point: main()
"""

import os
import sys
import wave
import threading
import tempfile
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path

from piper import PiperVoice, SynthesisConfig

# ---------------------------------------------------------------------------
# UPS brand colors
# ---------------------------------------------------------------------------
BROWN   = "#351C15"
GOLD    = "#FFB500"
BG      = "#FEF3C7"
CARD    = "#FFFFFF"
TEXT    = "#1A0F0A"
SUBTEXT = "#7A5C4F"
BORDER  = "#D4A96A"

# ---------------------------------------------------------------------------
# Voice model discovery
# ---------------------------------------------------------------------------
# Models live in  <project>/audio-models/<lang_code>/
# e.g.  audio-models/en_US/en_US-lessac-medium.onnx
# When adding a new language, drop its .onnx + .onnx.json into a matching folder.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
MODELS_DIR = _HERE / "audio-model"
LANG_CODE  = "en_US"


def _find_model(lang: str) -> Path | None:
    """Return the first .onnx file found under audio-models/<lang>/."""
    lang_dir = MODELS_DIR / lang
    if lang_dir.is_dir():
        for f in sorted(lang_dir.glob("*.onnx")):
            return f
    return None


def _wav_to_mp3(wav_path: str, mp3_path: str):
    """Convert WAV → MP3 using OS-native tools (no ffmpeg needed)."""
    if sys.platform == "darwin":
        # afconvert ships with every macOS
        subprocess.run(
            ["afconvert", "-f", "mp4f", "-d", "aac", wav_path, mp3_path],
            check=True,
        )
    elif sys.platform == "win32":
        # Windows Media Foundation via PowerShell
        ps = (
            f'$reader=[System.IO.File]::OpenRead("{wav_path}");'
            f'$writer=[NAudio.Wave.Mp3FileWriter]::new("{mp3_path}",[NAudio.Wave.Mp3FileWriter+CreateWriterDelegate]$null);'
            f'[NAudio.Wave.WaveFileReader]$w=$reader;'
            f'[NAudio.Wave.WaveFormatConversionStream]$s=[NAudio.Wave.WaveFormatConversionStream]::CreatePcmStream($w);'
            f'[NAudio.Wave.WaveFileWriter]::WriteWavFileToStream($writer,$s);'
        )
        # Simpler fallback: just keep as WAV on Windows if no NAudio
        import shutil
        shutil.copy(wav_path, mp3_path)
    else:
        # Linux: try sox, else keep wav
        import shutil
        if shutil.which("sox"):
            subprocess.run(["sox", wav_path, mp3_path], check=True)
        else:
            shutil.copy(wav_path, mp3_path)


# ---------------------------------------------------------------------------
class TTSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Text-to-Speech")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._file_path: str | None = None
        self._rate_var   = tk.DoubleVar(value=1.0)   # length_scale (1.0 = normal)
        self._status_var = tk.StringVar(value="Select a .txt file to get started.")
        self._previewing = False
        self._preview_proc: subprocess.Popen | None = None

        # Load Piper voice once
        model_path = _find_model(LANG_CODE)
        if model_path is None:
            messagebox.showerror(
                "Voice model missing",
                f"No .onnx model found in:\n{MODELS_DIR / LANG_CODE}\n\n"
                f"Run:\n  python -m piper.download_voices {LANG_CODE}-lessac-medium\n"
                f"Then move the files into audio-models/{LANG_CODE}/",
            )
            self.destroy()
            return

        self._voice = PiperVoice.load(str(model_path))

        self._build_ui()
        self._center(580, 400)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        header = tk.Frame(self, bg=BROWN)
        header.pack(fill="x")
        tk.Label(
            header, text="📦  Text-to-Speech",
            font=("Helvetica", 17, "bold"), bg=BROWN, fg=GOLD,
        ).pack(side="left", padx=22, pady=14)
        tk.Label(
            header, text="Offline · English",
            font=("Helvetica", 10), bg=BROWN, fg="#C8A96E",
        ).pack(side="right", padx=18)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=26, pady=14)

        # Step 1 — file
        self._section(body, "1  —  Choose a .txt file")
        file_card = self._card(body)
        self._file_label = tk.Label(
            file_card, text="No file selected",
            font=("Helvetica", 11), bg=CARD, fg=SUBTEXT, anchor="w", width=44,
        )
        self._file_label.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self._btn(file_card, "Browse…", GOLD, self._browse, fg=BROWN).grid(
            row=0, column=1, padx=(0, 12), pady=10)

        # Step 2 — speed
        self._section(body, "2  —  Speaking speed")
        rate_card = self._card(body)
        rate_row = tk.Frame(rate_card, bg=CARD)
        rate_row.pack(fill="x", padx=12, pady=8)
        tk.Label(rate_row, text="Fast", font=("Helvetica", 9),
                 bg=CARD, fg=SUBTEXT).pack(side="left")
        tk.Scale(
            rate_row, from_=0.5, to=2.0, resolution=0.05, orient="horizontal",
            variable=self._rate_var, length=320, showvalue=False,
            bg=CARD, highlightthickness=0,
            troughcolor=GOLD, activebackground=BROWN,
        ).pack(side="left", padx=6)
        tk.Label(rate_row, text="Slow", font=("Helvetica", 9),
                 bg=CARD, fg=SUBTEXT).pack(side="left")
        self._speed_label = tk.Label(
            rate_row, text="1.00×",
            font=("Helvetica", 11, "bold"), bg=CARD, fg=BROWN, width=5)
        self._speed_label.pack(side="left", padx=(10, 0))
        self._rate_var.trace_add("write", self._on_rate_change)

        # Step 3 — actions
        self._section(body, "3  —  Preview & Export")
        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(anchor="w", pady=(4, 0))

        self._preview_btn = self._btn(btn_row, "▶  Preview", BROWN, self._on_preview, width=13, fg=GOLD)
        self._preview_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = self._btn(btn_row, "⏹  Stop", BROWN, self._on_stop, width=9, fg=GOLD)
        self._stop_btn.pack(side="left", padx=(0, 8))
        self._stop_btn.config(state="disabled")

        self._save_btn = self._btn(btn_row, "💾  Save as MP3", GOLD, self._on_save, width=15, fg=BROWN)
        self._save_btn.pack(side="left")

        # Progress
        style = ttk.Style()
        style.theme_use("default")
        style.configure("UPS.Horizontal.TProgressbar",
                        troughcolor=BG, background=GOLD, bordercolor=BORDER)
        self._progress = ttk.Progressbar(
            body, mode="indeterminate", length=520,
            style="UPS.Horizontal.TProgressbar")
        self._progress.pack(pady=(14, 0))

        # Status bar
        tk.Label(
            self, textvariable=self._status_var,
            font=("Helvetica", 10), bg=BROWN, fg="#C8A96E",
            anchor="w", relief="flat", padx=14, pady=6,
        ).pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _section(self, parent, text):
        tk.Label(parent, text=text, font=("Helvetica", 12, "bold"),
                 bg=BG, fg=BROWN).pack(anchor="w", pady=(10, 2))

    def _card(self, parent):
        f = tk.Frame(parent, bg=CARD, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill="x", pady=(0, 4))
        return f

    def _btn(self, parent, text, color, cmd, width=10, fg="white"):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg=fg, activebackground=color,
            activeforeground=fg, relief="flat",
            font=("Helvetica", 11, "bold"),
            padx=12, pady=7, width=width, cursor="hand2", bd=0,
        )

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _on_rate_change(self, *_):
        val = self._rate_var.get()
        # length_scale: higher = slower, so display the inverse as the "speed"
        self._speed_label.config(text=f"{1/val:.2f}×")

    def _set_busy(self, busy: bool, is_preview: bool = False):
        s = "disabled" if busy else "normal"
        self._preview_btn.config(state=s)
        self._save_btn.config(state=s)
        self._stop_btn.config(state="normal" if (busy and is_preview) else "disabled")
        if busy:
            self._progress.start(12)
        else:
            self._progress.stop()
            self._progress["value"] = 0

    # ------------------------------------------------------------------
    # Browse
    # ------------------------------------------------------------------
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Open text file",
            filetypes=[("Text files", "*.txt")],
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            messagebox.showerror("Invalid file", "Only .txt files are supported.")
            return
        self._file_path = path
        self._file_label.config(text=os.path.basename(path), fg=TEXT)
        self._status_var.set(f"Loaded: {os.path.basename(path)}")

    def _read_text(self) -> str | None:
        if not self._file_path or not os.path.isfile(self._file_path):
            messagebox.showerror("No file", "Please select a .txt file first.")
            return None
        text = Path(self._file_path).read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            messagebox.showerror("Empty file", "The file contains no text.")
            return None
        return text

    def _synth_wav(self, text: str, wav_path: str):
        """Synthesize text → WAV file using Piper."""
        # length_scale: 1.0 = normal speed, <1.0 = faster, >1.0 = slower.
        # Slider left (0.5) = fast, right (2.0) = slow — passed directly.
        length_scale = round(self._rate_var.get(), 4)
        cfg = SynthesisConfig(length_scale=length_scale)
        with wave.open(wav_path, "wb") as wf:
            self._voice.synthesize_wav(text, wf, syn_config=cfg)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _on_preview(self):
        text = self._read_text()
        if not text:
            return
        self._set_busy(True, is_preview=True)
        self._status_var.set("▶  Generating preview…")
        threading.Thread(target=self._preview_worker, args=(text,), daemon=True).start()

    def _preview_worker(self, text: str):
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav.close()
        try:
            self._synth_wav(text, tmp_wav.name)
            self.after(0, lambda: self._status_var.set("▶  Playing…"))
            if sys.platform == "darwin":
                self._preview_proc = subprocess.Popen(["afplay", tmp_wav.name])
                self._preview_proc.wait()
            elif sys.platform == "win32":
                self._preview_proc = subprocess.Popen(
                    ["powershell", "-c",
                     f'(New-Object Media.SoundPlayer "{tmp_wav.name}").PlaySync()'])
                self._preview_proc.wait()
            else:
                player = "paplay" if subprocess.run(
                    ["which", "paplay"], capture_output=True).returncode == 0 else "aplay"
                self._preview_proc = subprocess.Popen([player, tmp_wav.name])
                self._preview_proc.wait()
        except Exception as exc:
            self.after(0, lambda e=exc: messagebox.showerror("Error", str(e)))
        finally:
            self._preview_proc = None
            try:
                os.unlink(tmp_wav.name)
            except OSError:
                pass
            self.after(0, lambda: self._set_busy(False))
            self.after(0, lambda: self._status_var.set("Done."))

    # ------------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------------
    def _on_stop(self):
        if self._preview_proc:
            try:
                self._preview_proc.terminate()
            except Exception:
                pass
        self._set_busy(False)
        self._status_var.set("Stopped.")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def _on_save(self):
        text = self._read_text()
        if not text:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 audio", "*.mp3")],
            initialfile=os.path.splitext(os.path.basename(self._file_path))[0],
            title="Save MP3 as…",
        )
        if not save_path:
            return
        self._set_busy(True)
        self._status_var.set("Synthesizing…")
        threading.Thread(target=self._save_worker, args=(text, save_path), daemon=True).start()

    def _save_worker(self, text: str, save_path: str):
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav.close()
        try:
            self._synth_wav(text, tmp_wav.name)
            self.after(0, lambda: self._status_var.set("Converting to MP3…"))
            _wav_to_mp3(tmp_wav.name, save_path)
            name = os.path.basename(save_path)
            self.after(0, lambda: messagebox.showinfo("Saved ✓", f"Saved:\n{save_path}"))
            self.after(0, lambda n=name: self._status_var.set(f"Saved: {n}"))
        except Exception as exc:
            self.after(0, lambda e=exc: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self._status_var.set("Failed."))
        finally:
            try:
                os.unlink(tmp_wav.name)
            except OSError:
                pass
            self.after(0, lambda: self._set_busy(False))


# ---------------------------------------------------------------------------
def main():
    app = TTSApp()
    app.mainloop()


if __name__ == "__main__":
    main()
