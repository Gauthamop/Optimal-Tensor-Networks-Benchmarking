"""Figures for the report, drawn from the same data the dashboard uses."""
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman'], 'font.size': 7.5, 'axes.linewidth': 0.6, 'lines.linewidth': 1.1, 'lines.markersize': 3.5})
W = 3.45

# --- Fig. 1: Shor TT error and rank vs bond cap ---
df = pd.read_csv(ROOT / 'data' / 'mps_tt_benchmark_results.csv')
sh = df[df.algorithm == 'Shor_ModExp']
fig, ax = plt.subplots(1, 2, figsize=(W, 2.0))
for (n, g), m in zip(sh.groupby('system_size'), ('o', 's', '^')):
    ax[0].semilogy(g.bond_dimension, g.error_metric.clip(lower=1e-16), marker=m, label=f'{n} qubits')
    ax[1].plot(g.bond_dimension, g.measured_rank, marker=m, label=f'{n} qubits')
for a in ax:
    a.set_xscale('log', base=2); a.set_xticks([4, 8, 16, 32]); a.set_xticklabels(['4', '8', '16', '32']); a.minorticks_off()
ax[0].set_xlabel(r'bond cap $\chi$'); ax[0].set_ylabel(r'$|1-\|\psi\|^2|$')
ax[1].set_xlabel(r'bond cap $\chi$'); ax[1].set_ylabel('measured max rank')
ax[0].set_title('(a) truncation error', fontsize=7.5); ax[1].set_title('(b) measured rank', fontsize=7.5)
ax[0].legend(frameon=False, fontsize=6.5)
for a in ax:
    a.grid(alpha=0.3, lw=0.4)
fig.tight_layout(pad=0.4)
fig.savefig(HERE / 'figs' / 'fig1_shor.png', dpi=300)

# --- Fig. 2: PEPS error vs D ---
su = pd.DataFrame(
    [(3, 2, 4.29e-2), (3, 3, 2.01e-2), (3, 4, 4.05e-3), (3, 6, 9.55e-4), (4, 2, 5.26e-2), (4, 3, 3.54e-2), (4, 4, 2.00e-2)], columns=['L', 'D', 'e']
)
vq = pd.DataFrame(
    [(3, 2, 1.9e-1, 7.4e-2), (3, 3, 1.4e-1, 5.0e-2), (3, 4, 2.2e-2, 3.6e-3), (3, 6, 1.3e-2, 3.0e-3), (4, 2, 3.1e-1, 1.6e-1), (4, 3, 2.6e-1, 8.6e-2), (4, 4, 6.3e-2, 1.1e-2)],
    columns=['L', 'D', 'before', 'after'],
)
fig, ax = plt.subplots(figsize=(W, 2.4))
for L, c in ((3, 'tab:blue'), (4, 'tab:red')):
    s, v = su[su.L == L], vq[vq.L == L]
    ax.semilogy(s.D, s.e, '-o', color=c, label=f'{L}x{L} simple update')
    ax.semilogy(v.D, v.before, ':s', color=c, label=f'{L}x{L} VQE, exact angles')
    ax.semilogy(v.D, v.after, '--^', color=c, label=f'{L}x{L} VQE, PEPS-aware')
ax.set_xlabel('bond dimension $D$'); ax.set_ylabel('relative energy error')
ax.set_xticks([2, 3, 4, 6]); ax.grid(alpha=0.3, lw=0.4)
ax.legend(frameon=False, fontsize=5.8, loc='lower left', ncol=1)
fig.tight_layout(pad=0.4)
fig.savefig(HERE / 'figs' / 'fig2_peps.png', dpi=300)

# --- Fig. 3: MERA convergence ---
conv = pd.DataFrame(
    [
        (2, 0, 1.21), (2, 40, 6.12e-2), (2, 80, 1.06e-2), (2, 120, 9.63e-3), (2, 160, 9.63e-3), (2, 199, 9.63e-3),
        (4, 0, 1.25), (4, 40, 3.18e-3), (4, 80, 2.64e-3), (4, 120, 2.33e-3), (4, 160, 1.95e-3), (4, 199, 1.35e-3),
        (8, 0, 1.22), (8, 40, 2.70e-3), (8, 80, 2.19e-3), (8, 119, 1.62e-3),
    ],
    columns=['chi', 'it', 'err'],
)
fig, ax = plt.subplots(figsize=(W, 2.2))
for (chi, g), m in zip(conv.groupby('chi'), ('o', 's', '^')):
    ax.semilogy(g.it, g.err, marker=m, label=fr'$\chi={chi}$')
ax.set_xlabel('optimizer iteration'); ax.set_ylabel('energy error per site')
ax.grid(alpha=0.3, lw=0.4); ax.legend(frameon=False)
fig.tight_layout(pad=0.4)
fig.savefig(HERE / 'figs' / 'fig3_mera.png', dpi=300)
print('figures written')
