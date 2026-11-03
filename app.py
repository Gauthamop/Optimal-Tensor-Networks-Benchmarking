"""Combined dashboard: MPS/TT benchmarks (Arushi), PEPS 2D-lattice VQE, MERA (Devang).  Run: streamlit run app.py"""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import mera_page
import mps_tt_page
import peps_page

st.set_page_config(page_title='Tensor network benchmarks', layout='wide')
OUT = Path(__file__).parent / 'out'

page = st.sidebar.radio('Section', ['Combined overview', 'MPS & TT (Arushi)', 'PEPS 2D lattice / VQE', 'MERA critical Ising (Devang)'])
st.sidebar.caption('Optimal tensor networks benchmarking framework: MPS, TT, PEPS and MERA results in one place.')

if page == 'MPS & TT (Arushi)':
    mps_tt_page.render()
elif page == 'PEPS 2D lattice / VQE':
    peps_page.render()
elif page == 'MERA critical Ising (Devang)':
    mera_page.render()
else:
    mt = mps_tt_page.load()
    dj, sh = mt[mt.algorithm == 'Deutsch-Jozsa'], mt[mt.algorithm == 'Shor_ModExp']
    su = peps_page.SU
    opt = {L: peps_page.parse_opt(OUT / f'opt_{L}.txt')[0] for L in ('3x3', '4x4')}

    mera = mera_page.load()
    mfin = mera['final']

    st.title('Tensor network benchmarks: MPS, TT, PEPS and MERA')
    st.caption('Independent benchmark suites on one page. Metrics differ per algorithm, see the notes at the bottom before comparing numbers across them.')

    c = st.columns(5)
    c[0].metric('DJ (MPS) qubits', f'{dj.system_size.max()}', 'rank 1, error 0', delta_color='off')
    exact = sh[sh.error_metric < 1e-10].groupby('system_size').bond_dimension.min()
    c[1].metric('Shor (TT) qubits', f'{sh.system_size.max()}', f'exact at bond dim {exact.min()}-{exact.max()}', delta_color='off')
    best33 = opt['3x3'].err_after.min() if not opt['3x3'].empty else float('nan')
    c[2].metric('PEPS 3x3 VQE error', f'{best33:.1e}', 'vs ED, D=6', delta_color='off')
    best44 = opt['4x4'].err_after.min() if not opt['4x4'].empty else float('nan')
    c[3].metric('PEPS 4x4 VQE error', f'{best44:.1e}', 'vs ED, D=4', delta_color='off')
    if not mfin.empty:
        c[4].metric('MERA L=16 error', f'{mfin.rel_err.min():.1e}', f'chi={int(mfin.sort_values("rel_err").iloc[0].chi)}, vs exact', delta_color='off')

    st.subheader('Where each part of the plan stands')
    st.dataframe(
        pd.DataFrame(
            [
                ('Deutsch-Jozsa', 'MPS', 'Done', '10-30 qubits, bond dim 4-32: rank 1, error 0'),
                ('QFT', 'MPS', 'No results yet', ''),
                ('Shor modular exponentiation', 'TT', 'Done', '8-13 qubits: error ~1e-15 once bond dim reaches the true rank (8-16)'),
                ('2D lattice / VQE (Heisenberg)', 'PEPS', 'Done', '3x3: 3e-3 (D=6), 4x4: 1.1e-2 (D=4) after PEPS-aware optimization'),
                ('2D lattice / VQE (Hubbard)', 'PEPS', 'Not built', 'needs fermionic signs'),
                ('Critical systems (critical Ising)', 'MERA', 'Partial', 'L=16: 1e-3 rel. energy error at chi=4; validated vs state vector and finite differences; Stage 4 benchmark grid not yet run'),
                ('QAE', 'MERA / TTNS', 'No results yet', ''),
                ('Image recognition', 'TT', 'No results yet', ''),
            ],
            columns=['Algorithm / domain', 'Tensor network', 'Status', 'Headline'],
        ),
        use_container_width=True,
        hide_index=True,
    )

    rows = []
    for _, r in dj.iterrows():
        rows.append(dict(method='MPS: Deutsch-Jozsa', series=f'{r.system_size} qubits', D=r.bond_dimension, error=r.error_plot, time_s=np.nan if r.warmup else r.wall_time_sec))
    for _, r in sh.iterrows():
        rows.append(dict(method='TT: Shor mod-exp', series=f'{r.system_size} qubits', D=r.bond_dimension, error=r.error_plot, time_s=np.nan if r.warmup else r.wall_time_sec))
    for _, r in su.iterrows():
        rows.append(dict(method='PEPS: simple update', series=r.lattice, D=r.D, error=r.rel_err, time_s=r.time_s))
    for L, o in opt.items():
        for _, r in o.iterrows():
            rows.append(dict(method='PEPS: VQE (truncation optimized)', series=L, D=r.D, error=r.err_after, time_s=np.nan))
    for _, r in mfin.iterrows():
        rows.append(dict(method='MERA: critical Ising (L=16)', series='L=16', D=r.chi, error=r.rel_err, time_s=r.time_s))
    allr = pd.DataFrame(rows)

    st.subheader('Error and cost against bond dimension')
    sel = st.multiselect('Methods', sorted(allr.method.unique()), default=sorted(allr.method.unique()))
    d = allr[allr.method.isin(sel)]

    def chart(y, title, ytitle):
        return (
            alt.Chart(d.dropna(subset=[y]), title=title)
            .mark_line(point=True)
            .encode(
                x=alt.X('D:Q', title='bond dimension', scale=alt.Scale(type='log', base=2), axis=alt.Axis(values=[1, 2, 3, 4, 6, 8, 16, 32])),
                y=alt.Y(f'{y}:Q', title=ytitle, scale=alt.Scale(type='log')),
                color=alt.Color('method:N', title=None),
                detail='series:N',
                tooltip=['method', 'series', 'D', alt.Tooltip(f'{y}:Q', format='.3g')],
            )
            .properties(height=340)
        )

    c1, c2 = st.columns(2)
    c1.altair_chart(chart('error', 'Error vs bond dimension', 'error (exact zeros drawn at 1e-16)'), use_container_width=True)
    c2.altair_chart(chart('time_s', 'Wall time vs bond dimension', 'seconds'), use_container_width=True)
    st.caption('One line per system size within each method. VQE rows have no time because they are multi-minute optimization runs, not single simulations.')

    st.subheader('Notes before comparing')
    st.markdown(
        '''
- **Different error metrics.** DJ: probability of the wrong measurement outcome. Shor: |1 - norm^2| after truncation. PEPS and MERA: relative energy error against the exact ground-state energy. Each is "0 = perfect", but magnitudes are not like-for-like across methods.
- **Different bond dimension meaning.** MPS/TT bond dimension is the cap on a 1D chain; PEPS D is the bond cap on a 2D lattice, where cost grows far faster (the deck lists O(D^10)).
- **Timing is indicative only.** The two suites were run separately; the PEPS timings come from a 12th-gen i5-1235U laptop (7.7 GB RAM, CPU only), and the first run of each MPS/TT algorithm (import / warm-up) is dropped from the time chart.
- **MERA** uses chi as its bond dimension; the L=16 points come from 200 optimizer iterations (120 for chi=8, not converged) and their times are for that whole optimization, not one evaluation.
- **Memory** is not compared: the MPS/TT file records a process RSS delta that reads 0.0 for most runs.
'''
    )
