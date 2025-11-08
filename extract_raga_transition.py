"""
extract_raga_transition.py

Purpose:
- Load a Raga audio file (e.g. raga_mohanam.mp3)
- Extract pitch (MIDI) sequence
- Quantize and convert to note names
- Build a transition matrix and save as CSV

Dependencies:
    pip install librosa music21 numpy pandas matplotlib soundfile
"""
import librosa
import numpy as np
import pandas as pd
from music21 import pitch
import sys, os

# add backend folder to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from raga_utils import build_transition_matrix



# -----------------------------
# Step 1: Load the audio file
# -----------------------------
audio_path = "raga_mohanam.mp3"
print(f"🎵 Loading {audio_path} ...")
y, sr = librosa.load(audio_path, sr=None)

# -----------------------------
# Step 2: Extract fundamental frequency (f0)
# -----------------------------
print("🔍 Extracting pitch contour using librosa.yin() ...")
f0 = librosa.yin(y, fmin=librosa.note_to_hz('C2'),
                 fmax=librosa.note_to_hz('C7'), sr=sr)
f0 = np.nan_to_num(f0, nan=0.0)

# -----------------------------
# Step 3: Convert to MIDI sequence
# -----------------------------
midi_seq = librosa.hz_to_midi(f0)
midi_seq = midi_seq[midi_seq > 0]  # remove silence
midi_seq = np.round(midi_seq).astype(int)

# Remove consecutive duplicates
compressed = [midi_seq[0]]
for m in midi_seq[1:]:
    if m != compressed[-1]:
        compressed.append(m)

print(f"Extracted {len(compressed)} distinct MIDI values.")

# -----------------------------
# Step 4: Convert MIDI → note names
# -----------------------------
note_seq = [pitch.Pitch(m).nameWithOctave for m in compressed]
print("🎼 Example extracted notes:", note_seq[:15])

# -----------------------------
# Step 5: Split into short phrases
# -----------------------------
chunk_size = 8
raga_corpus = [
    note_seq[i:i+chunk_size]
    for i in range(0, len(note_seq), chunk_size)
    if len(note_seq[i:i+chunk_size]) > 1
]

print(f"✅ Built {len(raga_corpus)} short melodic segments.")

# -----------------------------
# Step 6: Build transition matrix
# -----------------------------
states = sorted(list({n for seq in raga_corpus for n in seq}))
P_raga = build_transition_matrix(
    raga_corpus, states=states, order=1, add_laplace=1e-6)

# -----------------------------
# Step 7: Save matrix & plot
# -----------------------------
csv_file = "raga_mohanam_transition.csv"
P_raga.to_csv(csv_file)
print(f"✅ Transition matrix saved as {csv_file}")

# Optional: visualize
try:
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 6))
    plt.imshow(P_raga, cmap='viridis', interpolation='nearest')
    plt.title("Transition Matrix — Raga Mohanam")
    plt.xlabel("Next Note")
    plt.ylabel("Current Note")
    plt.xticks(ticks=np.arange(len(P_raga.columns)), labels=P_raga.columns, rotation=90)
    plt.yticks(ticks=np.arange(len(P_raga.index)), labels=P_raga.index)
    plt.colorbar(label='Transition Probability')
    plt.tight_layout()
    plt.savefig("raga_mohanam_transition_heatmap.png")
    print("📊 Saved heatmap: raga_mohanam_transition_heatmap.png")
except Exception as e:
    print(f"(Optional visualization skipped: {e})")
