"""Simple-update PEPS vs exact diagonalization for the 2D Heisenberg model."""
import time
import tracemalloc

from peps_tn import PEPS, exact_ground_energy, heisenberg_bond

SCHEDULE = [(0.1, 100), (0.03, 100), (0.01, 100)]


def run(Lr, Lc, D, h):
    tracemalloc.start()
    t0 = time.perf_counter()
    p = PEPS(Lr, Lc, D)
    for tau, n in SCHEDULE:
        for _ in range(n):
            p.sweep(tau, h)
    e = p.energy(h)
    dt = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1] / 2**20
    tracemalloc.stop()
    return e, dt, peak


if __name__ == '__main__':
    h = heisenberg_bond()
    print('Lr Lc  D   E/N        rel.err    time[s]  peakMB')
    for Lr, Lc in [(2, 2), (3, 3), (4, 4)]:
        e0 = exact_ground_energy(h, Lr, Lc)
        for D in (1, 2, 3, 4, 6):
            e, dt, peak = run(Lr, Lc, D, h)
            n = Lr * Lc
            print(f'{Lr}  {Lc}  {D}  {e / n:+.6f}  {abs(e - e0) / abs(e0):.2e}  {dt:7.2f}  {peak:7.1f}   (ED E/N={e0 / n:+.6f})', flush=True)
