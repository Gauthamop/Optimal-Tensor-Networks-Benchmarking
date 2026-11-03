"""Thesis-size figures (6 in wide) and two block diagrams."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).parent
ROOT = HERE.parent
OUT = HERE / 'thesis_figs'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman'], 'font.size': 10, 'axes.linewidth': 0.7, 'lines.linewidth': 1.4, 'lines.markersize': 5})
W = 6.0


def save(fig, name):
    fig.tight_layout(pad=0.5)
    fig.savefig(OUT / name, dpi=250)
    plt.close(fig)


# ---- 4.1 Deutsch-Jozsa time vs qubits
df = pd.read_csv(ROOT / 'data' / 'mps_tt_benchmark_results.csv')
dj = df[(df.algorithm == 'Deutsch-Jozsa')]
dj = dj[dj.wall_time_sec < 1]  # drop the first (start-up) run
fig, ax = plt.subplots(figsize=(W, 2.8))
for (chi, g), m in zip(dj.groupby('bond_dimension'), 'osv^'):
    ax.plot(g.system_size, g.wall_time_sec, marker=m, label=fr'$\chi={chi}$')
ax.set_xlabel('number of qubits'); ax.set_ylabel('wall time (s)'); ax.grid(alpha=0.3, lw=0.5); ax.legend(frameon=False, ncol=4)
save(fig, 'f41_dj.png')

# ---- 4.2 Shor error and rank
sh = df[df.algorithm == 'Shor_ModExp']
fig, ax = plt.subplots(1, 2, figsize=(W, 2.9))
for (n, g), m in zip(sh.groupby('system_size'), 'osv'):
    ax[0].semilogy(g.bond_dimension, g.error_metric.clip(lower=1e-16), marker=m, label=f'{n} qubits')
    ax[1].plot(g.bond_dimension, g.measured_rank, marker=m, label=f'{n} qubits')
for a in ax:
    a.set_xscale('log', base=2); a.set_xticks([4, 8, 16, 32]); a.set_xticklabels(['4', '8', '16', '32']); a.minorticks_off(); a.grid(alpha=0.3, lw=0.5); a.set_xlabel(r'bond cap $\chi$')
ax[0].set_ylabel(r'truncation error $|1-\|\psi\|^2|$'); ax[1].set_ylabel('measured maximum bond rank')
ax[0].set_title('(a) truncation error'); ax[1].set_title('(b) measured rank'); ax[0].legend(frameon=False, fontsize=8)
save(fig, 'f42_shor.png')

# ---- 4.3 PEPS error vs D
su = pd.DataFrame([(3, 2, 4.29e-2), (3, 3, 2.01e-2), (3, 4, 4.05e-3), (3, 6, 9.55e-4), (4, 2, 5.26e-2), (4, 3, 3.54e-2), (4, 4, 2.00e-2)], columns=['L', 'D', 'e'])
vq = pd.DataFrame([(3, 2, 1.9e-1, 7.4e-2), (3, 3, 1.4e-1, 5.0e-2), (3, 4, 2.2e-2, 3.6e-3), (3, 6, 1.3e-2, 3.0e-3), (4, 2, 3.1e-1, 1.6e-1), (4, 3, 2.6e-1, 8.6e-2), (4, 4, 6.3e-2, 1.1e-2)],
                  columns=['L', 'D', 'before', 'after'])
fig, ax = plt.subplots(1, 2, figsize=(W, 3.0), sharey=True)
for a, L in zip(ax, (3, 4)):
    s, v = su[su.L == L], vq[vq.L == L]
    a.semilogy(s.D, s.e, '-o', label='simple update')
    a.semilogy(v.D, v.before, ':s', label='VQE, exact angles truncated')
    a.semilogy(v.D, v.after, '--^', label='VQE, PEPS-aware')
    a.set_title(f'{L}x{L} lattice'); a.set_xlabel('bond dimension $D$'); a.set_xticks([2, 3, 4, 6]); a.grid(alpha=0.3, lw=0.5)
ax[0].set_ylabel('relative energy error'); ax[0].legend(frameon=False, fontsize=7.5, loc='lower left')
save(fig, 'f43_peps.png')

# ---- 4.4 PEPS-aware Adam traces (3x3)
import peps_page  # noqa: E402

op, trace = peps_page.parse_opt(ROOT / 'out' / 'opt_3x3.txt')
e0 = -0.527703 * 9
fig, ax = plt.subplots(figsize=(W, 2.9))
for (D, g), m in zip(trace.groupby('D'), 'osv^'):
    ax.semilogy(g.step, (g.best - e0).abs() / abs(e0), marker=m, label=f'$D={D}$')
ax.set_xlabel('Adam step'); ax.set_ylabel('best relative error so far'); ax.grid(alpha=0.3, lw=0.5); ax.legend(frameon=False, ncol=4)
save(fig, 'f44_adam.png')

# ---- 4.5 MERA convergence
conv = pd.DataFrame([(2, 0, 1.21), (2, 40, 6.12e-2), (2, 80, 1.06e-2), (2, 120, 9.63e-3), (2, 160, 9.63e-3), (2, 199, 9.63e-3),
                     (4, 0, 1.25), (4, 40, 3.18e-3), (4, 80, 2.64e-3), (4, 120, 2.33e-3), (4, 160, 1.95e-3), (4, 199, 1.35e-3),
                     (8, 0, 1.22), (8, 40, 2.70e-3), (8, 80, 2.19e-3), (8, 119, 1.62e-3)], columns=['chi', 'it', 'err'])
fig, ax = plt.subplots(figsize=(W, 2.9))
for (chi, g), m in zip(conv.groupby('chi'), 'osv'):
    ax.semilogy(g.it, g.err, marker=m, label=fr'$\chi={chi}$')
ax.set_xlabel('optimizer iteration'); ax.set_ylabel('energy error per site'); ax.grid(alpha=0.3, lw=0.5); ax.legend(frameon=False)
save(fig, 'f45_mera.png')


# ---- block diagrams
def box(ax, x, y, w, h, text, fc='#e8eef7', fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.03', fc=fc, ec='#34495e', lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs)


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=11, lw=1, color='#34495e'))


# 3.1 overview
fig, ax = plt.subplots(figsize=(W, 3.6)); ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(-0.3, 6)
box(ax, 3.3, 5.0, 3.4, 0.8, 'Selection matrix\n(problem structure -> tensor network)', '#fdf2d0')
cols = [(0.1, 'Study 1: MPS / TT\nDeutsch-Jozsa,\nShor kernel (quimb)'), (3.45, 'Study 2: PEPS\n2D Heisenberg:\nsimple update, VQE'), (6.8, 'Study 3: MERA\ncritical Ising chain,\nEvenbly-Vidal updates')]
for x, t in cols:
    box(ax, x, 2.9, 3.1, 1.3, t)
    arrow(ax, 5.0, 5.0, x + 1.55, 4.2)
    box(ax, x, 1.2, 3.1, 0.9, 'error vs exact reference,\nwall time, bond rank', '#e3f1e3', 8.5)
    arrow(ax, x + 1.55, 2.9, x + 1.55, 2.1)
    arrow(ax, x + 1.55, 1.2, 5.0, 0.75)
box(ax, 3.0, 0.0, 4.0, 0.75, 'Combined analysis and dashboard', '#fdf2d0')
save(fig, 'f31_overview.png')

# 3.2 PEPS pipeline
fig, ax = plt.subplots(figsize=(W, 3.4)); ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
steps = [(0.2, 4.4, 'Singlet-dimer\nstart state'), (3.6, 4.4, 'Layered XY/ZZ gates\n(per-bond angles)'), (7.0, 4.4, 'Exact-circuit VQE\n(adjoint gradient,\nL-BFGS-B)')]
for x, y, t in steps:
    box(ax, x, y, 2.8, 1.2, t)
arrow(ax, 3.0, 5.0, 3.6, 5.0); arrow(ax, 6.4, 5.0, 7.0, 5.0)
box(ax, 7.0, 2.4, 2.8, 1.2, 'Apply gates to PEPS\nwith truncation to D\n(simple update)', '#fdf2d0')
arrow(ax, 8.4, 4.4, 8.4, 3.6)
box(ax, 3.6, 2.4, 2.8, 1.2, 'Contract to state vector\nenergy vs exact\ndiagonalization', '#e3f1e3')
arrow(ax, 7.0, 3.0, 6.4, 3.0)
box(ax, 0.2, 2.4, 2.8, 1.2, 'PEPS-aware Adam:\nfinite-difference gradients\non the truncated energy', '#fdf2d0')
arrow(ax, 3.6, 3.0, 3.0, 3.0)
arrow(ax, 1.6, 2.4, 1.6, 1.5); box(ax, 0.2, 0.3, 9.6, 1.2, 'Result: relative energy error, wall time per bond dimension D  (3x3: D = 2, 3, 4, 6;  4x4: D = 2, 3, 4)', '#e8eef7')
save(fig, 'f32_pepsflow.png')
print('thesis figures written:', sorted(p.name for p in OUT.glob('*.png')))
