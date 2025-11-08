"""
raga_markov_gui.py
Simple desktop GUI for Mohanam-based Markov generation
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random, time, requests
from raga_utils import (
    build_transition_matrix,
    generate_sequence_from_matrix,
    save_midi_from_notes,
    save_wav_from_notes,
    play_notes
)

class MohanamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎵 Raga Mohanam Generator")
        self.geometry("700x400")
        ttk.Label(self, text="Raga: Mohanam", font=('Helvetica', 14, 'bold')).pack(pady=12)

        ttk.Button(self, text="Generate Melody", command=self.generate_music).pack(pady=10)
        ttk.Button(self, text="View Experiment Results (Localhost)", command=self.open_plot).pack(pady=10)

        self.log = tk.Text(self, height=12)
        self.log.pack(fill='both', expand=True, padx=10, pady=10)

    def log_msg(self, s):
        self.log.insert('end', f"{time.strftime('%H:%M:%S')} - {s}\n")
        self.log.see('end')

    def generate_music(self):
        try:
            self.log_msg("Generating melody using Raga Mohanam ...")
            import pandas as pd
            raga_matrix = pd.read_csv("raga_mohanam_transition.csv", index_col=0)
            states = list(raga_matrix.columns)
            seq = generate_sequence_from_matrix(raga_matrix, start=states[0], steps=32)
            midi_name = f"mohanam_{int(time.time())}.mid"
            wav_name = midi_name.replace('.mid','.wav')
            save_midi_from_notes(seq, midi_name)
            save_wav_from_notes(seq, wav_name)
            play_notes(seq)
            self.log_msg(f"✅ Generated & played: {wav_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log_msg(f"❌ Error: {e}")

    def open_plot(self):
        try:
            import webbrowser
            webbrowser.open("http://127.0.0.1:5000/run")
            self.log_msg("Opened experiment plot on localhost.")
        except Exception as e:
            messagebox.showerror("Plot Error", str(e))

if __name__ == "__main__":
    app = MohanamApp()
    app.mainloop()
