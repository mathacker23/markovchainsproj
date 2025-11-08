"""
experiment_runner.py

Automated experiment runner (Flask-enabled)
- Uses extracted Raga Mohanam note sequence
- Builds Raga + Western transition matrices
- Mixes/inverts/perturbs matrices to study tonal variations
- Generates melodies, serves results as an image via Flask

Run locally:
    python backend/experiment_runner.py
Then open:
    http://127.0.0.1:5000/
"""

from flask import Flask, jsonify, send_file
import numpy as np
import pandas as pd
import os, random, time
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.spatial.distance import jensenshannon
from scipy.linalg import pinv
from raga_utils import (
    build_transition_matrix,
    mix_matrices,
    generate_sequence_from_matrix,
    save_midi_from_notes,
    save_wav_from_notes
)

# -------------------------
# Flask Setup
# -------------------------
app = Flask(__name__)
OUT = Path(__file__).resolve().parent.joinpath('experiment_outputs')
OUT.mkdir(parents=True, exist_ok=True)

@app.route('/')
def home():
    return jsonify({
        "message": "🎵 Mohanam Experiment Server is running!",
        "endpoints": ["/run"]
    })

@app.route('/run')
def run_experiment():
    print("🎶 Building Raga Mohanam transition matrix from extracted sequence ...")

    # ✅ Use the real extracted Raga Mohanam note sequence
    raga_mohanam_notes = [
        'B5', 'Bb5', 'G6', 'D3', 'C#2', 'E2', 'G2',
        'A3', 'G#3', 'G3', 'F#3', 'G3', 'G#3', 'G3', 'G#3'
    ]

    # Split into short melodic phrases for transition modeling
    chunk_size = 6
    raga_corpus = [
        raga_mohanam_notes[i:i+chunk_size]
        for i in range(0, len(raga_mohanam_notes), chunk_size)
        if len(raga_mohanam_notes[i:i+chunk_size]) > 1
    ]

    # Western reference corpus
    western_corpus = [
        ['C4','D4','E4','F4','G4','A4','B4','C5'],
        ['C5','B4','A4','G4','F4','E4','D4','C4'],
        ['C4','E4','G4','A4','G4','E4','C4']
    ]

    # Create unified state set
    states = sorted(list({n for seq in (raga_corpus + western_corpus) for n in seq}))

    # Build transition matrices
    Pr = build_transition_matrix(raga_corpus, states=states, order=1, add_laplace=1e-6)
    Pw = build_transition_matrix(western_corpus, states=states, order=1, add_laplace=1e-6)

    # -------------------------
    # Sweep α values
    # -------------------------
    alphas = np.linspace(0.0, 1.0, 9)
    results = []

    for alpha in alphas:
        print(f"🌗 Mixing matrices α={alpha:.2f} ...")
        Pmix = mix_matrices(Pr, Pw, alpha=alpha)
        pinv_mat = pd.DataFrame(pinv(Pmix.values), index=Pmix.index, columns=Pmix.columns)

        # Perturb for randomness
        eps = 0.02
        noise = np.random.dirichlet(np.ones(len(states)) * eps, size=len(states))
        Ppert = Pmix.values + noise
        Ppert = Ppert / Ppert.sum(axis=1, keepdims=True)
        Ppert_df = pd.DataFrame(Ppert, index=Pmix.index, columns=Pmix.columns)

        # Generate melody
        gen = generate_sequence_from_matrix(Ppert_df, start=states[0], steps=32)
        midi_file = OUT / f"mohanam_alpha_{alpha:.2f}.mid"
        wav_file = OUT / f"mohanam_alpha_{alpha:.2f}.wav"
        save_midi_from_notes(gen, midi_file)
        save_wav_from_notes(gen, wav_file)

        # Similarity metrics
        def hist(notes, ref):
            all_notes = sorted(list(set(notes + ref)))
            h = np.array([notes.count(n) for n in all_notes], dtype=float)
            return h / np.sum(h) if np.sum(h) > 0 else np.zeros_like(h)

        raga_ref = [n for seq in raga_corpus for n in seq]
        west_ref = [n for seq in western_corpus for n in seq]
        d_r = jensenshannon(hist(gen, raga_ref), hist(raga_ref, raga_ref))
        d_w = jensenshannon(hist(gen, west_ref), hist(west_ref, west_ref))

        results.append({
            "alpha": float(alpha),
            "raga_sim": 1 - float(d_r),
            "west_sim": 1 - float(d_w)
        })

    # -------------------------
    # Save results and plot
    # -------------------------
    df = pd.DataFrame(results)
    df.to_csv(OUT / "mohanam_alpha_results.csv", index=False)

    plt.figure(figsize=(6,4))
    plt.plot(df["alpha"], df["raga_sim"], label="Raga similarity", marker="o")
    plt.plot(df["alpha"], df["west_sim"], label="Western similarity", marker="o")
    plt.xlabel("α (raga weight)")
    plt.ylabel("Similarity (1 - JSD)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plot_path = OUT / "mohanam_similarity_plot.png"
    plt.savefig(plot_path)

    print("✅ Experiment completed. Plot saved at:", plot_path)
    return send_file(plot_path, mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)

