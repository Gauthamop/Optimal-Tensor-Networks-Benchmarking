"""VQE on a 2D lattice: layered nearest-neighbour ansatz applied to a PEPS.

Start state: a singlet-dimer cover (horizontal, or vertical when only Lr is even;
any unpaired site follows the Neel pattern), or the Neel state. Then P layers; layer l applies
exp(-i(a_b XY_b + b_b ZZ_b)) on every bond b with its own (a_b, b_b).
Gates on the PEPS are applied by simple-update bond truncation to dimension D.
"""
import sys
import time

import numpy as np
from scipy.optimize import minimize

from peps_tn import D_, L, PEPS, R, U, apply_h, bonds, exact_ground_energy, heisenberg_bond

SX = np.array([[0, 1], [1, 0]]) / 2
SY = np.array([[0, -1j], [1j, 0]]) / 2
SZ = np.array([[1, 0], [0, -1]]) / 2
H_XY = np.real(np.kron(SX, SX) + np.kron(SY, SY))
H_ZZ = np.kron(SZ, SZ)


def gate(a, b, d=2):
    w, v = np.linalg.eigh(a * H_XY + b * H_ZZ)
    return ((v * np.exp(-1j * w)) @ v.T).reshape(d, d, d, d)


def dimer_pairs(Lr, Lc):
    """Singlet-dimer cover by backtracking (right, then down). For odd Lr*Lc the
    centre site is left free, which gives a pinwheel on 3x3."""
    free = {(Lr // 2, Lc // 2)} if (Lr * Lc) % 2 else set()
    taken, pairs = set(free), []

    def fill(k):
        if k == Lr * Lc:
            return True
        r, c = divmod(k, Lc)
        if (r, c) in taken:
            return fill(k + 1)
        for r2, c2 in ((r, c + 1), (r + 1, c)):
            if r2 < Lr and c2 < Lc and (r2, c2) not in taken:
                taken.update({(r, c), (r2, c2)})
                pairs.append(((r, c), (r2, c2)))
                if fill(k + 1):
                    return True
                pairs.pop()
                taken.difference_update({(r, c), (r2, c2)})
        return False

    return pairs if fill(0) else []


def initial_state(Lr, Lc, init):
    if init == 'neel':
        psi = np.zeros((2,) * (Lr * Lc), dtype=complex)
        psi[tuple((r + c) % 2 for r in range(Lr) for c in range(Lc))] = 1.0
        return psi
    singlet = np.array([[0, 1], [-1, 0]]) / np.sqrt(2)
    first = dict(dimer_pairs(Lr, Lc))
    second = set(first.values())
    sites = [(r, c) for r in range(Lr) for c in range(Lc)]
    pieces, order = [], []
    for s in sites:
        if s in first:
            pieces.append(singlet)
            order += [s, first[s]]
        elif s not in second:
            pieces.append(np.eye(2)[(s[0] + s[1]) % 2])
            order.append(s)
    state = pieces[0]
    for p in pieces[1:]:
        state = np.multiply.outer(state, p)
    perm = [order.index(s) for s in sites]
    return np.transpose(state, perm).astype(complex)


def initial_peps(Lr, Lc, D, init):
    p = PEPS(Lr, Lc, D, dtype=complex)
    if init == 'neel':
        return p
    for (r, c), (r2, c2) in dimer_pairs(Lr, Lc):
        horiz = r == r2
        la, lb = (R, L) if horiz else (D_, U)
        sa, sb = [2, 1, 1, 1, 1], [2, 1, 1, 1, 1]
        sa[la], sb[lb] = 2, 2
        a, b = np.zeros(sa, dtype=complex), np.zeros(sb, dtype=complex)
        for k in range(2):
            ia, ib = [0] * 5, [0] * 5
            ia[0], ia[la] = k, k
            ib[0], ib[lb] = 1 - k, k
            a[tuple(ia)] = 1.0
            b[tuple(ib)] = 1.0 if k == 0 else -1.0
        p.T[(r, c)], p.T[(r2, c2)] = a, b
        p.lam[('h' if horiz else 'v', r, c)] = np.ones(2) / np.sqrt(2)
    paired = {s for pr in dimer_pairs(Lr, Lc) for s in pr}
    for r in range(Lr):
        for c in range(Lc):
            if (r, c) not in paired:
                t = np.zeros((2, 1, 1, 1, 1), dtype=complex)
                t[(r + c) % 2, 0, 0, 0, 0] = 1.0
                p.T[(r, c)] = t
    return p


def statevector_energy(params, h, Lr, Lc, layers, init):
    psi = initial_state(Lr, Lc, init)
    nb = len(bonds(Lr, Lc))
    for l in range(layers):
        for k, ((r, c), (r2, c2), _, _, _) in enumerate(bonds(Lr, Lc)):
            g = gate(params[2 * (l * nb + k)], params[2 * (l * nb + k) + 1])
            i, j = r * Lc + c, r2 * Lc + c2
            psi = np.moveaxis(np.tensordot(g, psi, axes=([2, 3], [i, j])), [0, 1], [i, j])
    return float(np.real(np.vdot(psi, apply_h(psi, h, Lr, Lc)) / np.vdot(psi, psi)))


def apply_bond(op4, psi, i, j):
    return np.moveaxis(np.tensordot(op4, psi, axes=([2, 3], [i, j])), [0, 1], [i, j])


def energy_and_grad(params, h, Lr, Lc, layers, init):
    """Exact dE/dparams by reverse-mode: undo the gates one at a time."""
    bl = bonds(Lr, Lc)
    nb = len(bl)
    psi = initial_state(Lr, Lc, init)
    seq = []
    for l in range(layers):
        for k, ((r, c), (r2, c2), _, _, _) in enumerate(bl):
            idx = l * nb + k
            g = gate(params[2 * idx], params[2 * idx + 1])
            i, j = r * Lc + c, r2 * Lc + c2
            psi = apply_bond(g, psi, i, j)
            seq.append((idx, i, j, g))
    lam = apply_h(psi, h, Lr, Lc)
    e = float(np.real(np.vdot(psi, lam)))
    xy4, zz4 = H_XY.reshape(2, 2, 2, 2), H_ZZ.reshape(2, 2, 2, 2)
    grad = np.zeros_like(params)
    for idx, i, j, g in reversed(seq):
        grad[2 * idx] = 2 * np.real(np.vdot(lam, -1j * apply_bond(xy4, psi, i, j)))
        grad[2 * idx + 1] = 2 * np.real(np.vdot(lam, -1j * apply_bond(zz4, psi, i, j)))
        gd = np.conj(g.reshape(4, 4)).T.reshape(2, 2, 2, 2)
        psi, lam = apply_bond(gd, psi, i, j), apply_bond(gd, lam, i, j)
    return e, grad


def peps_energy(params, h, Lr, Lc, layers, D, init):
    p = initial_peps(Lr, Lc, D, init)
    nb = len(bonds(Lr, Lc))
    for l in range(layers):
        for k, (A, B, la, lb, key) in enumerate(bonds(Lr, Lc)):
            p.update_bond(A, B, la, lb, key, gate(params[2 * (l * nb + k)], params[2 * (l * nb + k) + 1]))
    return p.energy(h)


def optimize(fun, x0, maxiter, jac=False):
    t0 = time.perf_counter()
    res = minimize(fun, x0, method='L-BFGS-B', jac=jac, options={'maxiter': maxiter})
    return res.x, res.fun, time.perf_counter() - t0


if __name__ == '__main__':
    Lr, Lc, layers = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    init = sys.argv[4] if len(sys.argv) > 4 else 'dimer'
    h = heisenberg_bond()
    n = Lr * Lc
    npar = 2 * layers * len(bonds(Lr, Lc))
    e0 = exact_ground_energy(h, Lr, Lc)
    print(f'{Lr}x{Lc}, {layers} layers, {npar} params, init={init}, ED E/N = {e0 / n:+.6f}', flush=True)

    best = None
    for seed in range(4 if n <= 9 else 2):
        x0 = np.random.default_rng(seed).uniform(-0.4, 0.4, npar)
        x, e, dt = optimize(lambda y: energy_and_grad(y, h, Lr, Lc, layers, init), x0, 400, jac=True)
        print(f'exact-statevector VQE seed {seed}: E/N = {e / n:+.6f}  rel.err = {abs(e - e0) / abs(e0):.2e}  ({dt:.1f}s)', flush=True)
        if best is None or e < best[1]:
            best = (x, e)
    x, e = best

    print('PEPS energy at the best exact-VQE optimum (truncation error only):', flush=True)
    for D in ((2, 3, 4, 6) if n <= 9 else (2, 3, 4)):
        t0 = time.perf_counter()
        ep = peps_energy(x, h, Lr, Lc, layers, D, init)
        print(f'  D={D}: E/N = {ep / n:+.6f}  |E_peps-E_vqe|/|E0| = {abs(ep - e) / abs(e0):.2e}  ({time.perf_counter() - t0:.1f}s)', flush=True)

    print('PEPS-VQE (truncation in the loop, warm start):', flush=True)
    for D in (2, 4) if len(sys.argv) > 5 and sys.argv[5] == 'loop' else ():
        xp, ep, dt = optimize(lambda y: peps_energy(y, h, Lr, Lc, layers, D, init), x, 25)
        print(f'  D={D}: E/N = {ep / n:+.6f}  rel.err vs ED = {abs(ep - e0) / abs(e0):.2e}  ({dt:.1f}s)', flush=True)
