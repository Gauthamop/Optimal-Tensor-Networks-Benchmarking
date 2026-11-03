"""Open-boundary PEPS on an Lr x Lc lattice, optimized by simple update.

Tensor leg order: (phys, L, R, U, D). Bond weights live in `lam`, keyed
('h', r, c) for the bond (r,c)-(r,c+1) and ('v', r, c) for (r,c)-(r+1,c).
Boundary legs have dimension 1 and no weight.
"""
import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh

L, R, U, D_ = 1, 2, 3, 4


def heisenberg_bond():
    sx = np.array([[0, 1], [1, 0]]) / 2
    sy = np.array([[0, -1j], [1j, 0]]) / 2
    sz = np.array([[1, 0], [0, -1]]) / 2
    return np.real(np.kron(sx, sx) + np.kron(sy, sy) + np.kron(sz, sz))


def bonds(Lr, Lc):
    out = []
    for r in range(Lr):
        for c in range(Lc):
            if c + 1 < Lc:
                out.append(((r, c), (r, c + 1), R, L, ('h', r, c)))
            if r + 1 < Lr:
                out.append(((r, c), (r + 1, c), D_, U, ('v', r, c)))
    return out


def apply_h(psi, h, Lr, Lc):
    d = psi.shape[0]
    h4 = h.reshape(d, d, d, d)
    out = np.zeros_like(psi)
    for (r, c), (r2, c2), _, _, _ in bonds(Lr, Lc):
        i, j = r * Lc + c, r2 * Lc + c2
        out += np.moveaxis(np.tensordot(h4, psi, axes=([2, 3], [i, j])), [0, 1], [i, j])
    return out


def exact_ground_energy(h, Lr, Lc, d=2):
    n = Lr * Lc
    op = LinearOperator(
        (d**n, d**n),
        matvec=lambda v: apply_h(v.reshape((d,) * n), h, Lr, Lc).ravel(),
        dtype=float,
    )
    return eigsh(op, k=1, which='SA')[0][0]


class PEPS:
    def __init__(self, Lr, Lc, D, d=2, dtype=float):
        self.Lr, self.Lc, self.D, self.d = Lr, Lc, D, d
        self.lam = {}
        self.T = {}
        for r in range(Lr):
            for c in range(Lc):
                t = np.zeros((d, 1, 1, 1, 1), dtype=dtype)
                t[(r + c) % 2, 0, 0, 0, 0] = 1.0  # Neel product state
                self.T[(r, c)] = t

    def _lam(self, r, c, leg):
        key = {L: ('h', r, c - 1), R: ('h', r, c), U: ('v', r - 1, c), D_: ('v', r, c)}[leg]
        return self.lam.get(key, np.ones(1))

    def _env(self, r, c, skip):
        t = self.T[(r, c)]
        for leg in (L, R, U, D_):
            if leg != skip:
                shape = [1] * 5
                shape[leg] = -1
                t = t * self._lam(r, c, leg).reshape(shape)
        return t

    def _unenv(self, t, r, c, skip):
        for leg in (L, R, U, D_):
            if leg != skip:
                shape = [1] * 5
                shape[leg] = -1
                t = t / np.maximum(self._lam(r, c, leg), 1e-12).reshape(shape)
        return t

    @staticmethod
    def _split(t, leg):
        t = np.moveaxis(np.moveaxis(t, leg, -1), 0, -2)  # (o1,o2,o3,p,bond)
        shp = t.shape
        q, rr = np.linalg.qr(t.reshape(-1, shp[-2] * shp[-1]))
        return q, rr.reshape(-1, shp[-2], shp[-1]), shp[:3]

    def update_bond(self, A, B, legA, legB, key, gate4):
        d = self.d
        qa, ra, oa = self._split(self._env(*A, legA), legA)
        qb, rb, ob = self._split(self._env(*B, legB), legB)
        lam = self.lam.get(key, np.ones(1))
        theta = np.einsum('kpa,a,lqa->kplq', ra, lam, rb)
        theta = np.einsum('xypq,kplq->kxly', gate4, theta)
        ka, kb = theta.shape[0], theta.shape[2]
        u, s, vh = np.linalg.svd(theta.reshape(ka * d, kb * d), full_matrices=False)
        m = min(self.D, int(np.sum(s > 1e-12 * s[0])))
        u, s, vh = u[:, :m], s[:m], vh[:m]
        self.lam[key] = s / np.linalg.norm(s)
        bn = np.einsum('nl,blq->nqb', qb, vh.reshape(m, kb, d)).reshape(*ob, d, m)
        an = np.einsum('mk,kpb->mpb', qa, u.reshape(ka, d, m)).reshape(*oa, d, m)
        an = np.moveaxis(np.moveaxis(an, -2, 0), -1, legA)
        bn = np.moveaxis(np.moveaxis(bn, -2, 0), -1, legB)
        self.T[A] = self._unenv(an, *A, legA)
        self.T[B] = self._unenv(bn, *B, legB)

    def sweep(self, tau, h):
        d = self.d
        w, v = np.linalg.eigh(h)
        g = (v * np.exp(-tau * w)) @ v.T
        g4 = g.reshape(d, d, d, d)
        for A, B, la, lb, key in bonds(self.Lr, self.Lc):
            self.update_bond(A, B, la, lb, key, g4)

    def state(self):
        """Contract to a dense (d,)*N state vector (only feasible for small N)."""
        n = self.Lr * self.Lc
        sites, nxt = [], n
        bond_id = {}
        for r in range(self.Lr):
            for c in range(self.Lc):
                t = self.T[(r, c)]
                labels = [r * self.Lc + c]
                drop = []
                for leg in (L, R, U, D_):
                    shape = [1] * 5
                    shape[leg] = -1
                    t = t * np.sqrt(self._lam(r, c, leg)).reshape(shape)
                    key = {L: ('h', r, c - 1), R: ('h', r, c), U: ('v', r - 1, c), D_: ('v', r, c)}[leg]
                    if key in self.lam:
                        if key not in bond_id:
                            bond_id[key] = nxt
                            nxt += 1
                        labels.append(bond_id[key])
                    else:
                        drop.append(leg)
                t = t.reshape([s for i, s in enumerate(t.shape) if i not in drop])
                sites.append((t, labels))
        acc, acc_labels = np.ones(()), []
        for t, labels in sites:  # row-major sweep keeps the open frontier small
            common = [x for x in labels if x in acc_labels]
            acc = np.tensordot(acc, t, axes=([acc_labels.index(x) for x in common], [labels.index(x) for x in common]))
            acc_labels = [x for x in acc_labels if x not in common] + [x for x in labels if x not in common]
        return acc

    def energy(self, h):
        psi = self.state()
        return float(np.real(np.vdot(psi, apply_h(psi, h, self.Lr, self.Lc)) / np.vdot(psi, psi)))
