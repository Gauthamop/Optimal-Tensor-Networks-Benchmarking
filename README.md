# PEPS on 2D lattices (VQE / Hubbard) — my part

Hardware: i5-1235U (10C/12T), 7.7 GB RAM, Windows, no GPU/WSL -> CPU NumPy only.

## Done
- `peps_tn.py`: open-boundary L_r x L_c PEPS, simple-update imaginary-time evolution, dense contraction for small N, exact diagonalization (ED) reference.
- `run_benchmark.py`: energy error vs bond dimension D, time, peak memory (2x2, 3x3, 4x4 Heisenberg).
- First results (Heisenberg, E/N rel. error vs ED): 3x3 D=6 ~1e-3; 4x4 D=4 ~2e-2 (D=6 still running when logged).

- `vqe_peps.py`: layered XY/ZZ nearest-neighbour ansatz from the Neel state, applied to the PEPS with truncation to D (`python vqe_peps.py Lr Lc layers`). PEPS energy matches exact statevector to ~1e-7 when D is not limiting (pipeline validated).
- VQE (Heisenberg, per-bond XY/ZZ angles, singlet-dimer start, exact adjoint gradient checked vs finite differences to 1e-9; `python vqe_peps.py Lr Lc layers dimer [loop]`). Raw logs in `out/`.

  | lattice | layers | params | exact-VQE err vs ED | PEPS err at that optimum (truncation only) |
  |---|---|---|---|---|
  | 2x3 | 3 | 42 | 1e-9 | D=4: 4e-3, D=6: 3e-3 |
  | 3x3 | 4 | 96 | 6e-4 (best of 4 seeds) | D=2: 1.9e-1, D=3: 1.4e-1, D=4: 2.1e-2, D=6: 1.2e-2 |
  | 4x4 | 3 | 144 | 6.8e-3 (best of 2 seeds, ~4 min/seed) | D=2: 3.0e-1, D=3: 2.3e-1, D=4: 5.6e-2 |

  - Lessons: Neel start stalls; a singlet-dimer cover works (pinwheel + free centre spin on 3x3). Adjoint gradients cut 3x3 from ~50 s to ~10 s per seed and made 4x4 feasible.
  - The error column for PEPS is |E_peps - E_vqe|/|E0| at fixed exact-VQE parameters; PEPS-in-the-loop optimization (`loop` flag, FD gradients) is only practical up to ~2x3.
  - Open: PEPS-aware gradients for 3x3/4x4, D=5/6 on 4x4 (dense contraction memory), then Hubbard.

- PEPS-aware VQE (`vqe_peps_opt.py Lr Lc layers steps`): optimize the truncated-PEPS energy itself at fixed D, warm-started from the exact-circuit optimum. Central finite-difference gradients run in parallel on 10 processes; Adam (L-BFGS stops after 1-4 iterations because the truncated energy is non-smooth). E_peps is the energy of a real PEPS state, so it is a valid upper bound on E0. Logs: `out/opt_3x3.txt`, `out/opt_4x4.txt`.

  | lattice | D | err, exact-VQE params truncated | err, PEPS-aware |
  |---|---|---|---|
  | 3x3 (200 steps) | 2 | 1.9e-1 | 7.4e-2 |
  | 3x3 | 3 | 1.4e-1 | 5.0e-2 |
  | 3x3 | 4 | 2.2e-2 | 3.6e-3 |
  | 3x3 | 6 | 1.3e-2 | 3.0e-3 |
  | 4x4 (60 steps) | 2 | 3.1e-1 | 1.6e-1 |
  | 4x4 | 3, 4 | 2.3e-1, 5.6e-2 | still running when logged; see out/opt_4x4.txt |

  - Also replaced the einsum contraction in `peps_tn.py` by a row-major tensordot sweep (3x3 D=4: 1.2 s -> 0.01 s).
  - Caveat: 3x3 D=2/3 are probably not converged (200 steps, still moving); a single seed was used.

- MERA page (`mera_page.py`, notebooks in `mera/`): parses results from the saved notebook outputs (validation, finite-difference check, L=16 optimizer runs). Stage 4 numbers appear once `data/mera_stage4_benchmarks.csv` exists or is uploaded on the page.
- Combined dashboard: `python -m streamlit run app.py`. Sidebar sections: combined overview (plan status, error/time vs bond dimension for MPS, TT and PEPS), MPS & TT page (`mps_tt_page.py`, data `data/mps_tt_benchmark_results.csv` from `arushi/benchmark_mps_tt.py`, needs quimb+psutil only to regenerate), PEPS page (`peps_page.py`, reads `out/*.txt`). Final 4x4 PEPS-aware errors: D=2 1.6e-1, D=3 8.6e-2, D=4 1.1e-2 (60 steps).

## Next
1. Finish 4x4 D=5,6 and plot error / time / memory vs D (these are the slide-10/11 numbers, measured instead of placeholders).
2. Replace dense contraction by boundary-MPS (chi_b) contraction so lattices larger than ~4x5 work; report error vs chi_b.
3. Hubbard: local dim 4; fermionic signs (fermionic swap gates or JW-snake) are required, validate on 2x2/2x3 against ED (4^N states).
4. VQE: parameterized circuit on lattice sites; PEPS gate application with truncation, energy via contraction, optimizer loop. Compare to simple-update ground state.
5. Report O(D^10) scaling empirically (fit time vs D).

## Deck claims to soften
- "GPU/CuPy": not available locally; state scope as CPU-only (or use Colab).
- "VQE circuit maps to PEPS efficiently": true only for shallow circuits with nearest-neighbour gates on the lattice; say so.
