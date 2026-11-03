"""PEPS-aware VQE: optimize the truncated-PEPS energy directly (D fixed in the loop).

Warm start = exact-circuit optimum (cached in out/). Gradients are central finite
differences, evaluated in parallel over a process pool (truncation has no cheap
exact gradient). E_peps is the energy of a genuine PEPS state, so E_peps >= E0.
Optimizer: Adam on the central-difference gradient.
Usage: python vqe_peps_opt.py Lr Lc layers [steps]
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')

import numpy as np
from vqe_peps import bonds, energy_and_grad, exact_ground_energy, heisenberg_bond, optimize, peps_energy

H = heisenberg_bond()


def adam(fg, x0, steps, lr0=0.03, lr1=0.003, b1=0.9, b2=0.999):
    """Adam with cosine-decayed step; tolerates the non-smooth truncated energy. Returns best seen."""
    x, m, v = x0.copy(), np.zeros_like(x0), np.zeros_like(x0)
    best = (x.copy(), np.inf)
    for t in range(1, steps + 1):
        e, g = fg(x)
        if e < best[1]:
            best = (x.copy(), e)
        m, v = b1 * m + (1 - b1) * g, b2 * v + (1 - b2) * g * g
        lr = lr1 + 0.5 * (lr0 - lr1) * (1 + np.cos(np.pi * t / steps))
        x = x - lr * (m / (1 - b1**t)) / (np.sqrt(v / (1 - b2**t)) + 1e-8)
        if t % 20 == 0:
            print(f'    step {t}: E = {e:+.5f}, best = {best[1]:+.5f}', flush=True)
    return best
EPS = 1e-5


def _eval(args):
    x, Lr, Lc, layers, D = args
    return peps_energy(x, H, Lr, Lc, layers, D, 'dimer')


def warm_start(Lr, Lc, layers):
    path = f'out/x_{Lr}x{Lc}_L{layers}.npy'
    if os.path.exists(path):
        return np.load(path)
    n, npar = Lr * Lc, 2 * layers * len(bonds(Lr, Lc))
    best = None
    for seed in (range(4) if n <= 9 else [1]):
        x0 = np.random.default_rng(seed).uniform(-0.4, 0.4, npar)
        x, e, _ = optimize(lambda y: energy_and_grad(y, H, Lr, Lc, layers, 'dimer'), x0, 400, jac=True)
        if best is None or e < best[1]:
            best = (x, e)
    np.save(path, best[0])
    return best[0]


if __name__ == '__main__':
    Lr, Lc, layers = (int(a) for a in sys.argv[1:4])
    maxiter = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    n = Lr * Lc
    e0 = exact_ground_energy(H, Lr, Lc)
    os.makedirs('out', exist_ok=True)
    x0 = warm_start(Lr, Lc, layers)
    ev = energy_and_grad(x0, H, Lr, Lc, layers, 'dimer')[0]
    print(f'{Lr}x{Lc}, {layers} layers, ED E/N = {e0 / n:+.6f}, exact-circuit E/N = {ev / n:+.6f} (err {abs(ev - e0) / abs(e0):.2e})', flush=True)

    with ProcessPoolExecutor(max_workers=10) as pool:
        for D in ((2, 3, 4, 6) if n <= 9 else (2, 3, 4)):
            def fg(x):
                pts = [x] + [x + s * EPS * np.eye(len(x))[k] for k in range(len(x)) for s in (1, -1)]
                es = list(pool.map(_eval, [(p, Lr, Lc, layers, D) for p in pts], chunksize=4))
                return es[0], (np.array(es[1::2]) - np.array(es[2::2])) / (2 * EPS)

            e_before = _eval((x0, Lr, Lc, layers, D))
            t0 = time.perf_counter()
            xb, eb = adam(fg, x0, maxiter)
            print(f'  D={D}: truncation-only err {abs(e_before - e0) / abs(e0):.2e} -> PEPS-aware err {abs(eb - e0) / abs(e0):.2e}'
                  f'  (E/N = {eb / n:+.6f}, {maxiter} steps, {time.perf_counter() - t0:.0f}s)', flush=True)
            np.save(f'out/x_{Lr}x{Lc}_L{layers}_D{D}.npy', xb)
