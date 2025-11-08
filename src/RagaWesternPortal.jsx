import React, { useState, useEffect, useRef } from 'react'
import './App.css'

export default function RagaWesternPortal() {
  const western = {
    'C major': ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'],
    'G major': ['G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F#5', 'G5']
  }
  const ragas = {
    'Yaman': ['C4', 'D4', 'E4', 'F#4', 'G4', 'A4', 'B4', 'C5'],
    'Bhairav': ['C4', 'Db4', 'E4', 'F4', 'G4', 'Ab4', 'B4', 'C5']
  }

  const [pool, setPool] = useState('Western')
  const [key, setKey] = useState(Object.keys(western)[0])
  const [order, setOrder] = useState(1)
  const [seq, setSeq] = useState([])
  const audioCtx = useRef(null)

  useEffect(() => {
    setKey(pool === 'Western' ? Object.keys(western)[0] : Object.keys(ragas)[0])
  }, [pool])

  const noteToFreq = (n) => {
    const map = { 'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11 }
    const m = n.match(/^([A-G][b#]?)(\d)$/)
    if (!m) return 440
    const [_, note, octave] = m
    const midi = (parseInt(octave) + 1) * 12 + map[note]
    return 440 * Math.pow(2, (midi - 69) / 12)
  }

  const buildMatrix = (seq, order = 1) => {
    const states = [...new Set(seq)]
    if (order === 1) {
      const n = states.length
      const M = Array.from({ length: n }, () => Array(n).fill(0))
      for (let i = 0; i < seq.length - 1; i++) {
        const a = states.indexOf(seq[i])
        const b = states.indexOf(seq[i + 1])
        M[a][b]++
      }
      for (let i = 0; i < n; i++) {
        const s = M[i].reduce((a, b) => a + b, 0)
        M[i] = s ? M[i].map(v => v / s) : Array(n).fill(1 / n)
      }
      return { M, states }
    }
    const bigrams = []
    for (let i = 0; i < seq.length - 1; i++) {
      const pair = seq[i] + '|' + seq[i + 1]
      if (!bigrams.includes(pair)) bigrams.push(pair)
    }
    const M = Array.from({ length: bigrams.length }, () => Array(states.length).fill(0))
    for (let i = 0; i < seq.length - 2; i++) {
      const r = bigrams.indexOf(seq[i] + '|' + seq[i + 1])
      const c = states.indexOf(seq[i + 2])
      if (r >= 0 && c >= 0) M[r][c]++
    }
    for (let i = 0; i < M.length; i++) {
      const s = M[i].reduce((a, b) => a + b, 0)
      M[i] = s ? M[i].map(v => v / s) : Array(states.length).fill(1 / states.length)
    }
    return { M, states, bigrams }
  }

  const sampleRow = (row) => {
    const s = row.reduce((a, b) => a + b, 0)
    const probs = row.map(v => v / s)
    const r = Math.random()
    let c = 0
    for (let i = 0; i < probs.length; i++) { c += probs[i]; if (r < c) return i }
    return probs.length - 1
  }

  const generateUnique = () => {
    const template = pool === 'Western' ? western[key] : ragas[key]
    const base = []
    let cur = template[Math.floor(Math.random() * template.length)]
    base.push(cur)
    const steps = 12 + Math.floor(Math.random() * 12)
    for (let i = 0; i < steps - 1; i++) {
      const idx = template.indexOf(cur)
      const cand = [cur]
      if (idx > 0) cand.push(template[idx - 1])
      if (idx < template.length - 1) cand.push(template[idx + 1])
      cur = cand[Math.floor(Math.random() * cand.length)]
      base.push(cur)
    }
    const { M, states, bigrams } = buildMatrix(base, order)
    const out = []
    if (order === 1) {
      let current = base[0]
      out.push(current)
      for (let i = 0; i < 32; i++) {
        const row = M[states.indexOf(current)]
        const next = states[sampleRow(row)]
        out.push(next)
        current = next
      }
    } else {
      let big = bigrams[Math.floor(Math.random() * bigrams.length)].split('|')
      out.push(big[0], big[1])
      for (let i = 2; i < 32; i++) {
        const r = bigrams.indexOf(out[i - 2] + '|' + out[i - 1])
        const row = r >= 0 ? M[r] : M[Math.floor(Math.random() * M.length)]
        const next = states[sampleRow(row)]
        out.push(next)
      }
    }
    setSeq(out)
    play(out)
  }

  const play = (notes) => {
    if (!audioCtx.current) audioCtx.current = new (window.AudioContext || window.webkitAudioContext)()
    const ctx = audioCtx.current
    const now = ctx.currentTime
    let t = 0
    notes.forEach(n => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.frequency.value = noteToFreq(n)
      osc.type = 'sine'
      gain.gain.setValueAtTime(0, now + t)
      gain.gain.linearRampToValueAtTime(0.3, now + t + 0.02)
      gain.gain.linearRampToValueAtTime(0, now + t + 0.3)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now + t)
      osc.stop(now + t + 0.3)
      t += 0.3
    })
  }

  return (
    <div className="container">
      <h1>🎵 Raga–Western Markov Portal</h1>

      <div className="controls">
        <div>
          <label>Music Pool</label>
          <select value={pool} onChange={(e) => setPool(e.target.value)}>
            <option>Western</option>
            <option>Indian</option>
          </select>
        </div>

        <div>
          <label>Scale / Raga</label>
          <select value={key} onChange={(e) => setKey(e.target.value)}>
            {(pool === 'Western' ? Object.keys(western) : Object.keys(ragas)).map(k => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </div>

        <div>
          <label>Markov Order</label>
          <select value={order} onChange={(e) => setOrder(parseInt(e.target.value))}>
            <option value={1}>Order 1</option>
            <option value={2}>Order 2</option>
          </select>
        </div>

        <div>
          <label> </label>
          <button onClick={generateUnique}>Generate & Play</button>
        </div>
      </div>

      <div className="log-box">
        {seq.length ? seq.join(' • ') : <em>No sequence generated yet.</em>}
      </div>
    </div>
  )
}
