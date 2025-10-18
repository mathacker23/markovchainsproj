# α-Blend: Dynamic Hybrid Raga–Western Melody Generator
# Author: Saanvi Raghavendran
# Concept: Regenerate unique melodies each play
# by blending transition matrices dynamically.

use_bpm 100
use_synth :pluck

raga_yaman = [:C4, :D4, :E4, :Fs4, :G4, :A4, :B4, :C5]  # Raga Yaman
western_major = [:C4, :D4, :E4, :F4, :G4, :A4, :B4, :C5]  # C Major

# --- transition probabilities---
raga_transitions = {
  :C4 => [:D4, :E4, :G4],
  :D4 => [:E4, :Fs4, :C5],
  :E4 => [:Fs4, :G4, :A4],
  :Fs4 => [:G4, :A4, :C5],
  :G4 => [:A4, :B4, :C5],
  :A4 => [:B4, :C5, :E4],
  :B4 => [:C5, :A4, :G4],
  :C5 => [:B4, :A4, :G4]
}

western_transitions = {
  :C4 => [:E4, :G4, :F4],
  :D4 => [:F4, :A4, :B4],
  :E4 => [:G4, :C5, :D4],
  :F4 => [:A4, :C5, :G4],
  :G4 => [:B4, :D4, :E4],
  :A4 => [:C5, :E4, :F4],
  :B4 => [:D4, :G4, :A4],
  :C5 => [:E4, :G4, :A4]
}

# α parameter controls blend
alpha = 0.5  # 0.0 = pure raga, 1.0 = pure western, in-between = blended (0.5)

# --- function to blend transitions dynamically ---
define :blended_next do |note, alpha|
  r_list = raga_transitions[note] || raga_yaman
  w_list = western_transitions[note] || western_major
  
  if alpha == 0.0
    return r_list.choose #maintains pure raga classical
  elsif alpha == 1.0
    return w_list.choose #maintains pure western classical
  else
    # weighted mix: more elements from the dominant style
    r_weight = ((1 - alpha) * 10).to_i
    w_weight = (alpha * 10).to_i
    
    blended_pool = (r_list * r_weight) + (w_list * w_weight)
    return blended_pool.choose
  end
end

# --- function to generate a new melody each time ---
define :generate_melody do |length, alpha|
  notes = []
  current = :C4
  length.times do
    notes << current
    current = blended_next(current, alpha)
  end
  return notes
end

# --- live loop regenerates unique melodies each time ---
live_loop :hybrid_melody do
  melody = generate_melody(16, alpha)  # generate new melody on each loop
  melody.each do |n|
    play n, sustain: 0.3, release: 0.2
    sleep 0.5
  end
end
