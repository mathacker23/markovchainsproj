# raga_utils.py
"""
Utility functions for Markov matrix creation, sampling, audio/MIDI saving, mixing and inversion.
Import this module from other backend scripts.
"""

import numpy as np
import pandas as pd
from music21 import note, stream, midi
from scipy.linalg import pinv
from scipy.io.wavfile import write
import sounddevice as sd
from pathlib import Path
import random


def preserve_order_unique(seq):
    return list(dict.fromkeys(seq))

def freq_from_note_name(name):
    return note.Note(name).pitch.frequency

def notes_to_audio(notes, sr=22050, duration=0.35):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    waves = []
    for n in notes:
        f = freq_from_note_name(n)
        env_len = max(1, int(0.05 * sr))
        env = np.linspace(0, 1, env_len)
        sig = np.sin(2 * np.pi * f * t)
        sig[:env_len] *= env
        sig[-env_len:] *= env[::-1]
        waves.append(0.5 * sig)
    audio = np.concatenate(waves) if waves else np.zeros(1)
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))
    return audio.astype(np.float32)


# Transition matrices

def quantize_matrix(matrix, levels):
    Mq = np.copy(matrix)
    levels_arr = np.array(levels)
    for i in range(Mq.shape[0]):
        row = Mq[i]
        if np.all(row == 0):
            continue
        choices = levels_arr[np.abs(row[:, None] - levels_arr[None, :]).argmin(axis=1)]
        if np.sum(choices) == 0:
            maxidx = np.argmax(row)
            choices = np.zeros_like(choices)
            choices[maxidx] = 1.0
        else:
            choices = choices / np.sum(choices)
        Mq[i] = choices
    return Mq

def build_transition_matrix(sequences, states=None, order=1, quantize_levels=None, add_laplace=0.0):
    """
    sequences: list of sequences (each sequence is a list of note strings) OR a single sequence.
    order: 1 or 2
    Returns: pandas.DataFrame
    """
    if not sequences:
        return pd.DataFrame()
    # normalize input
    if isinstance(sequences[0], str) or not hasattr(sequences[0], '__iter__'):
        sequences = [sequences]
    if states is None:
        states = []
        for seq in sequences:
            states.extend(list(seq))
        states = preserve_order_unique(states)
    if order == 1:
        n = len(states)
        idx = {s: i for i, s in enumerate(states)}
        M = np.zeros((n, n), dtype=float)
        for seq in sequences:
            for i in range(len(seq) - 1):
                a = seq[i]; b = seq[i + 1]
                if a in idx and b in idx:
                    M[idx[a], idx[b]] += 1.0
        if add_laplace > 0:
            M += add_laplace
        row_sums = M.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        P = M / row_sums
        if quantize_levels:
            P = quantize_matrix(P, quantize_levels)
        return pd.DataFrame(P, index=states, columns=states)
    elif order == 2:
        bigrams = []
        for seq in sequences:
            for i in range(len(seq) - 1):
                bigrams.append((seq[i], seq[i + 1]))
        bigrams = preserve_order_unique(bigrams)
        idx_bi = {b: i for i, b in enumerate(bigrams)}
        idx_un = {u: i for i, u in enumerate(states)}
        P = np.zeros((len(bigrams), len(states)), dtype=float)
        for seq in sequences:
            for i in range(len(seq) - 2):
                b = (seq[i], seq[i + 1]); nxt = seq[i + 2]
                if b in idx_bi and nxt in idx_un:
                    P[idx_bi[b], idx_un[nxt]] += 1.0
        if add_laplace > 0:
            P += add_laplace
        row_sums = P.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        P = P / row_sums
        idx_labels = ['{}|{}'.format(x, y) for x, y in bigrams]
        if quantize_levels:
            P = quantize_matrix(P, quantize_levels)
        return pd.DataFrame(P, index=idx_labels, columns=states)
    else:
        raise ValueError("order must be 1 or 2")


def pseudo_inverse_matrix(mat):
    try:
        inv = np.linalg.inv(mat)
        return inv
    except np.linalg.LinAlgError:
        return pinv(mat)

def mix_matrices(A_df, B_df, alpha=0.5):
    # align shape
    A = A_df.reindex(index=A_df.index, columns=A_df.columns).fillna(0).values
    B = B_df.reindex(index=A_df.index, columns=A_df.columns).fillna(0).values
    M = alpha * A + (1 - alpha) * B
    row_sums = M.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    M = M / row_sums
    return pd.DataFrame(M, index=A_df.index, columns=A_df.columns)


def sample_next(state_index, matrix):
    row = matrix[state_index]
    s = np.sum(row)
    if s == 0:
        probs = np.ones_like(row) / len(row)
    else:
        probs = row / s
    return np.random.choice(len(row), p=probs)

def generate_sequence_from_matrix(matrix_df, start=None, steps=32, order=1):
    if matrix_df is None or matrix_df.empty:
        return []
    states = list(matrix_df.columns)
    if start is None:
        start = states[0]
    seq = []
    if order == 1:
        current = start
        seq.append(current)
        mat = matrix_df.values
        for _ in range(steps - 1):
            idx = states.index(current)
            nxt_idx = sample_next(idx, mat)
            current = states[nxt_idx]
            seq.append(current)
    else:
        rows = list(matrix_df.index)
        mat = matrix_df.values
        candidates = [r for r in rows if r.startswith(start + '|') or r.split('|')[0] == start]
        big = random.choice(candidates) if candidates else random.choice(rows)
        a, b = big.split('|')
        seq = [a, b]
        for _ in range(steps - 2):
            row_key = f"{seq[-2]}|{seq[-1]}"
            row_idx = rows.index(row_key) if row_key in rows else random.randrange(len(rows))
            nxt_idx = sample_next(row_idx, mat)
            seq.append(matrix_df.columns[nxt_idx])
    return seq


# MIDI / audio saving

def save_midi_from_notes(notes, filename='output.mid', quarter_length=0.5):
    s = stream.Stream()
    for nstr in notes:
        nobj = note.Note(nstr)
        nobj.quarterLength = quarter_length
        s.append(nobj)
    mf = midi.translate.streamToMidiFile(s)
    mf.open(filename, 'wb')
    mf.write()
    mf.close()

def save_wav_from_notes(notes, path='output.wav', sr=22050):
    audio = notes_to_audio(notes, sr=sr)
    write(str(path), sr, (audio * 32767).astype('int16'))
    return path

def play_notes(notes, sr=22050):
    audio = notes_to_audio(notes, sr=sr)
    sd.play(audio, sr)
    sd.wait()
