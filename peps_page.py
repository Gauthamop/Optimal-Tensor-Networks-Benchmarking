"""PEPS / VQE dashboard page (rendered from app.py)."""
import re
import time
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

OUT = Path(__file__).parent / 'out'

# Simple-update benchmark (run_benchmark.py output, Heisenberg, open boundary).
SU = pd.DataFrame(
    [
        (2, 2, 1, -0.250000, 5.00e-01, 1.37, 0.0), (2, 2, 2, -0.459558, 8.09e-02, 1.78, 0.0),
        (2, 2, 3, -0.493354, 1.33e-02, 1.93, 0.1), (2, 2, 4, -0.499924, 1.52e-04, 1.88, 0.2),
        (2, 2, 6, -0.498878, 2.24e-03, 2.09, 0.3),
        (3, 3, 1, -0.333333, 3.68e-01, 5.91, 0.0), (3, 3, 2, -0.505040, 4.29e-02, 5.92, 0.0),
        (3, 3, 3, -0.517087, 2.01e-02, 3.00, 0.4), (3, 3, 4, -0.525566, 4.05e-03, 3.81, 0.4),
        (3, 3, 6, -0.527199, 9.55e-04, 14.84, 0.5),
        (4, 4, 1, -0.375000, 3.47e-01, 6.47, 2.0), (4, 4, 2, -0.544103, 5.26e-02, 5.21, 2.0),
        (4, 4, 3, -0.554001, 3.54e-02, 6.70, 2.0), (4, 4, 4, -0.562840, 2.00e-02, 9.64, 2.6),
    ],
    columns=['Lr', 'Lc', 'D', 'E/N', 'rel_err', 'time_s', 'peak_MB'],
)
SU['lattice'] = SU.Lr.astype(str) + 'x' + SU.Lc.astype(str)
ED_PER_SITE = {'2x2': -0.5, '2x3': -0.521564, '3x3': -0.527703, '4x4': -0.574325}


def parse_exact(path):
    """vqe_*.txt -> (seeds table, truncation-at-optimum table)."""
    seeds, trunc = [], []
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()
    for line in path.read_text().splitlines():
        m = re.search(r'seed (\d+): E/N = ([-+.\d]+)\s+rel\.err = ([\d.e+-]+)\s+\(([\d.]+)s\)', line)
        if m:
            seeds.append(dict(seed=int(m[1]), E_N=float(m[2]), rel_err=float(m[3]), time_s=float(m[4])))
        m = re.search(r'D=(\d+): E/N = ([-+.\d]+)\s+\|E_peps-E_vqe\|/\|E0\| = ([\d.e+-]+)\s+\(([\d.]+)s\)', line)
        if m:
            trunc.append(dict(D=int(m[1]), E_N=float(m[2]), gap=float(m[3]), time_s=float(m[4])))
    return pd.DataFrame(seeds), pd.DataFrame(trunc)


def parse_opt(path):
    """opt_*.txt -> (per-D summary, Adam trace)."""
    rows, trace, pending = [], [], []
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()
    for line in path.read_text().splitlines():
        m = re.search(r'step (\d+): E = ([-+.\d]+), best = ([-+.\d]+)', line)
        if m:
            pending.append((int(m[1]), float(m[2]), float(m[3])))
        m = re.search(r'D=(\d+): truncation-only err ([\d.e+-]+) -> PEPS-aware err ([\d.e+-]+)\s+\(E/N = ([-+.\d]+), (\d+) steps, (\d+)s\)', line)
        if m:
            D = int(m[1])
            rows.append(dict(D=D, err_before=float(m[2]), err_after=float(m[3]), E_N=float(m[4]), steps=int(m[5]), time_s=int(m[6])))
            trace += [dict(D=D, step=s, E=e, best=b) for s, e, b in pending]
            pending = []
    return pd.DataFrame(rows), pd.DataFrame(trace)


def logchart(df, x, y, color, title, xtitle=None, ytitle=None):
    enc = dict(
        x=alt.X(x, title=xtitle or x, scale=alt.Scale(zero=False), axis=alt.Axis(tickMinStep=1)),
        y=alt.Y(y, title=ytitle or y, scale=alt.Scale(type='log')),
        tooltip=list(df.columns),
    )
    if color:
        enc['color'] = alt.Color(color, title=None)
    return alt.Chart(df, title=title).mark_line(point=True).encode(**enc).properties(height=300)


def render():
    st.title('PEPS on 2D lattices: VQE and ground-state benchmarks')
    st.caption('Heisenberg model, open boundaries, NumPy simple-update PEPS. All errors are relative to exact diagonalization (ED).')

    data = {}
    for L in ('3x3', '4x4'):
        ex, tr = parse_exact(OUT / f'vqe_{L}.txt')
        op, trace = parse_opt(OUT / f'opt_{L}.txt')
        data[L] = dict(exact=ex, trunc=tr, opt=op, trace=trace)

    tab_over, tab_su, tab_vqe, tab_aware, tab_live, tab_hw = st.tabs(
        ['Overview', 'Simple update', 'VQE (exact circuit)', 'PEPS-aware VQE', 'Live run', 'Hardware & notes']
    )

    with tab_over:
        c = st.columns(4)
        su_best = SU[SU.lattice == '3x3'].sort_values('rel_err').iloc[0]
        c[0].metric('3x3 simple update (D=6)', f'{su_best.rel_err:.1e}', 'rel. error vs ED', delta_color='off')
        ex3 = data['3x3']['exact']
        if not ex3.empty:
            c[1].metric('3x3 exact-circuit VQE', f'{ex3.rel_err.min():.1e}', 'best of seeds', delta_color='off')
        for col, L in zip(c[2:], ('3x3', '4x4')):
            op = data[L]['opt']
            if not op.empty:
                r = op.sort_values('err_after').iloc[0]
                col.metric(f'{L} PEPS-aware VQE (D={int(r.D)})', f'{r.err_after:.1e}', f'was {r.err_before:.1e} before', delta_color='inverse')
        st.subheader('Error vs bond dimension, all methods')
        frames = [SU.assign(method='simple update (imag. time)')[['lattice', 'D', 'rel_err', 'method']]]
        for L in ('3x3', '4x4'):
            op = data[L]['opt']
            if not op.empty:
                frames.append(pd.DataFrame(dict(lattice=L, D=op.D, rel_err=op.err_before, method='VQE, exact params truncated')))
                frames.append(pd.DataFrame(dict(lattice=L, D=op.D, rel_err=op.err_after, method='VQE, PEPS-aware')))
        allm = pd.concat(frames)
        lat = st.radio('Lattice', ['3x3', '4x4'], horizontal=True)
        sel = allm[allm.lattice == lat]
        st.altair_chart(logchart(sel, 'D:Q', 'rel_err:Q', 'method:N', f'{lat}: relative energy error', 'bond dimension D', 'relative error'), use_container_width=True)
        st.info('Reading it: simple update (ground-state projection) is the reference. VQE with parameters tuned for the exact circuit loses accuracy when truncated; optimizing the truncated PEPS directly recovers most of it, and the gap closes as D grows.')

    with tab_su:
        st.subheader('Simple-update imaginary-time evolution')
        st.altair_chart(logchart(SU, 'D:Q', 'rel_err:Q', 'lattice:N', 'Relative energy error vs D', 'bond dimension D', 'relative error'), use_container_width=True)
        c1, c2 = st.columns(2)
        c1.altair_chart(
            alt.Chart(SU, title='Wall time vs D').mark_line(point=True).encode(x='D:Q', y=alt.Y('time_s:Q', title='seconds'), color='lattice:N', tooltip=list(SU.columns)).properties(height=260),
            use_container_width=True,
        )
        c2.altair_chart(
            alt.Chart(SU, title='Peak traced memory vs D').mark_line(point=True).encode(x='D:Q', y=alt.Y('peak_MB:Q', title='MB'), color='lattice:N', tooltip=list(SU.columns)).properties(height=260),
            use_container_width=True,
        )
        st.dataframe(SU.drop(columns=['Lr', 'Lc']), use_container_width=True, hide_index=True)
        st.caption('The D=1 rows are the Neel product state (no entanglement). Timings include everything incl. contraction; 3x3 D=6 is slower because the contraction path was not yet optimized at the time.')

    with tab_vqe:
        st.subheader('Layered nearest-neighbour VQE, exact statevector')
        L = st.radio('Lattice ', ['3x3', '4x4'], horizontal=True, key='vqe_l')
        ex, tr = data[L]['exact'], data[L]['trunc']
        c1, c2 = st.columns(2)
        if not ex.empty:
            c1.markdown('**Per-seed optimum (adjoint gradient, L-BFGS)**')
            c1.dataframe(ex, use_container_width=True, hide_index=True)
            c1.metric('best error', f'{ex.rel_err.min():.2e}')
        if not tr.empty:
            c2.markdown('**Energy of the PEPS built from the best exact parameters (truncation only)**')
            c2.dataframe(tr.rename(columns={'gap': '|E_peps - E_vqe| / |E0|'}), use_container_width=True, hide_index=True)
            c2.altair_chart(logchart(tr, 'D:Q', 'gap:Q', None, 'Truncation error vs D', 'D', 'gap'), use_container_width=True)
        st.markdown('**Reference results (2x3, vertical dimer cover):** exact-VQE error 1e-9; PEPS-in-the-loop D=4 error 1.4e-8, D=2 1.1e-1.')

    with tab_aware:
        st.subheader('PEPS-aware optimization (truncated energy in the loop)')
        L = st.radio('Lattice  ', ['3x3', '4x4'], horizontal=True, key='aw_l')
        op, trace = data[L]['opt'], data[L]['trace']
        if op.empty:
            st.warning('No results parsed yet.')
        else:
            n = int(L[0]) * int(L[2])
            st.dataframe(op.rename(columns={'err_before': 'err (exact params truncated)', 'err_after': 'err (PEPS-aware)', 'E_N': 'E/N', 'time_s': 'seconds'}), use_container_width=True, hide_index=True)
            c1, c2 = st.columns(2)
            long = op.melt(id_vars='D', value_vars=['err_before', 'err_after'], var_name='stage', value_name='rel_err')
            long['stage'] = long.stage.map({'err_before': 'before', 'err_after': 'PEPS-aware'})
            c1.altair_chart(logchart(long, 'D:Q', 'rel_err:Q', 'stage:N', 'Error before / after', 'D', 'relative error'), use_container_width=True)
            op2 = op.assign(improvement=op.err_before / op.err_after)
            c2.altair_chart(alt.Chart(op2, title='Improvement factor').mark_bar().encode(x='D:O', y=alt.Y('improvement:Q', title='x smaller error'), tooltip=['D', 'improvement']).properties(height=300), use_container_width=True)
            if not trace.empty:
                e0 = ED_PER_SITE[L] * n
                t = trace.assign(rel_err=(trace.best - e0).abs() / abs(e0))
                st.altair_chart(
                    alt.Chart(t, title='Adam convergence (best-so-far error)').mark_line(point=True).encode(
                        x=alt.X('step:Q', title='Adam step'), y=alt.Y('rel_err:Q', scale=alt.Scale(type='log'), title='relative error'), color='D:N', tooltip=['D', 'step', 'best', 'rel_err']
                    ).properties(height=300),
                    use_container_width=True,
                )
            st.caption('Gradients are central finite differences on 10 processes; trace is logged every 20 steps.')

    with tab_live:
        st.subheader('Run something small right here')
        c = st.columns(3)
        lat = c[0].selectbox('Lattice', ['2x2', '2x3', '3x3'])
        D = c[1].slider('Bond dimension D', 1, 6, 4)
        mode = c[2].radio('Method', ['Simple update', 'VQE + PEPS truncation'])
        Lr, Lc = int(lat[0]), int(lat[2])
        if mode == 'Simple update':
            sweeps = st.slider('Sweeps per tau (3 taus: 0.1, 0.03, 0.01)', 20, 150, 60)
            if st.button('Run'):
                from peps_tn import PEPS, exact_ground_energy, heisenberg_bond

                h = heisenberg_bond()
                p = PEPS(Lr, Lc, D)
                e0 = exact_ground_energy(h, Lr, Lc)
                rows, bar, t0 = [], st.progress(0.0), time.perf_counter()
                tot = 3 * sweeps
                k = 0
                for tau in (0.1, 0.03, 0.01):
                    for s in range(sweeps):
                        p.sweep(tau, h)
                        k += 1
                        if k % 10 == 0:
                            rows.append(dict(sweep=k, rel_err=abs(p.energy(h) - e0) / abs(e0)))
                            bar.progress(k / tot)
                bar.empty()
                df = pd.DataFrame(rows)
                st.success(f'E/N = {p.energy(h) / (Lr * Lc):+.6f} (ED {e0 / (Lr * Lc):+.6f}), final error {df.rel_err.iloc[-1]:.2e}, {time.perf_counter() - t0:.1f}s')
                st.altair_chart(logchart(df, 'sweep:Q', 'rel_err:Q', None, 'Convergence', 'sweep', 'relative error'), use_container_width=True)
        else:
            layers = st.slider('Layers', 1, 4, 3)
            if st.button('Run'):
                from vqe_peps import energy_and_grad, exact_ground_energy, heisenberg_bond, optimize, peps_energy
                from vqe_peps import bonds

                h = heisenberg_bond()
                e0 = exact_ground_energy(h, Lr, Lc)
                npar = 2 * layers * len(bonds(Lr, Lc))
                x0 = np.random.default_rng(1).uniform(-0.4, 0.4, npar)
                with st.spinner('Optimizing exact circuit...'):
                    x, e, dt = optimize(lambda y: energy_and_grad(y, h, Lr, Lc, layers, 'dimer'), x0, 300, jac=True)
                ep = peps_energy(x, h, Lr, Lc, layers, D, 'dimer')
                m = st.columns(3)
                m[0].metric('exact-circuit error', f'{abs(e - e0) / abs(e0):.2e}', f'{dt:.1f}s, {npar} params', delta_color='off')
                m[1].metric(f'PEPS (D={D}) error', f'{abs(ep - e0) / abs(e0):.2e}')
                m[2].metric('truncation cost', f'{abs(ep - e) / abs(e0):.2e}')

    with tab_hw:
        st.subheader('Hardware')
        st.write('Intel Core i5-1235U (10 cores / 12 threads), 7.7 GB RAM, Windows, no GPU: CPU NumPy only.')
        st.subheader('What the numbers mean')
        st.markdown(
            '''
- **Simple update** projects onto the ground state with imaginary-time evolution; energies come from dense contraction of the PEPS (exact for the PEPS, feasible up to about 4x5).
- **VQE ansatz:** singlet-dimer start, then layers of exp(-i(a XY + b ZZ)) on every bond, one pair per bond; an exact reverse-mode gradient makes the exact circuit cheap.
- **PEPS-aware VQE:** the same circuit applied gate by gate with truncation to D, optimized on the truncated energy. The result is a real PEPS state, so it is a valid upper bound on the ground-state energy.
- **Not covered yet:** Hubbard model (needs fermionic signs), boundary-MPS contraction for larger lattices, D>=5 on 4x4.
- **Deck claims to soften:** GPU/CuPy is unavailable locally; VQE maps efficiently to PEPS only for shallow nearest-neighbour circuits.
    '''
        )
