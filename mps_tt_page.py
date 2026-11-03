"""MPS (Deutsch-Jozsa) and TT (Shor modular exponentiation) results page.

Data: data/mps_tt_benchmark_results.csv, produced by arushi/benchmark_mps_tt.py (quimb).
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

CSV = Path(__file__).parent / 'data' / 'mps_tt_benchmark_results.csv'
ERR_FLOOR = 1e-16  # exact zeros cannot be drawn on a log axis


def load():
    df = pd.read_csv(CSV)
    df['error_plot'] = df.error_metric.clip(lower=ERR_FLOOR)
    df['warmup'] = ~df.duplicated('algorithm')  # first run of each algorithm includes import / JIT cost
    return df


def lines(df, x, y, color, title, ytitle, log=True, height=300):
    return (
        alt.Chart(df, title=title)
        .mark_line(point=True)
        .encode(
            x=alt.X(x, axis=alt.Axis(tickMinStep=1), scale=alt.Scale(zero=False)),
            y=alt.Y(y, title=ytitle, scale=alt.Scale(type='log' if log else 'linear')),
            color=alt.Color(color, title=None),
            tooltip=list(df.columns),
        )
        .properties(height=height)
    )


def render():
    df = load()
    dj = df[df.algorithm == 'Deutsch-Jozsa']
    sh = df[df.algorithm == 'Shor_ModExp']

    st.title('MPS and Tensor-Train benchmarks')
    st.caption('Deutsch-Jozsa on an MPS and the Shor modular-exponentiation kernel on a tensor train, simulated with quimb (CircuitMPS).')

    hide_warm = st.checkbox('Hide first-run timing outliers (import / warm-up cost)', value=True)
    dj_t = dj[~dj.warmup] if hide_warm else dj
    sh_t = sh[~sh.warmup] if hide_warm else sh

    c = st.columns(4)
    c[0].metric('DJ qubits simulated', f'{dj.system_size.max()}', 'MPS, bond dim 4-32', delta_color='off')
    c[1].metric('DJ error / rank', f'{dj.error_metric.max():.0f} / {dj.measured_rank.max()}', 'exact at every size', delta_color='off')
    exact = sh[sh.error_metric < 1e-10].groupby('system_size').bond_dimension.min()
    c[2].metric('Shor qubits simulated', f'{sh.system_size.max()}', 'TT, bond dim 4-32', delta_color='off')
    c[3].metric('Shor min exact bond dim', ', '.join(f'{k}q: {v}' for k, v in exact.items()), 'error < 1e-10', delta_color='off')

    tab_dj, tab_sh, tab_raw = st.tabs(['Deutsch-Jozsa (MPS)', 'Shor mod-exp (TT)', 'Raw data'])

    with tab_dj:
        st.markdown('The balanced oracle keeps the MPS at **bond rank 1** for every size and cap, so the error (probability of the wrong outcome) is exactly 0 and cost grows only with qubit count.')
        c1, c2 = st.columns(2)
        c1.altair_chart(lines(dj_t.assign(chi=dj_t.bond_dimension.astype(str)), 'system_size:Q', 'wall_time_sec:Q', 'chi:N', 'Wall time vs qubits (by bond cap)', 'seconds', log=False), use_container_width=True)
        c2.altair_chart(lines(dj.assign(chi=dj.bond_dimension.astype(str)), 'system_size:Q', 'measured_rank:Q', 'chi:N', 'Measured bond rank vs qubits', 'max bond rank', log=False), use_container_width=True)
        st.caption('Time is ~linear in qubit count and independent of the bond cap, since the state never needs more than rank 1.')

    with tab_sh:
        st.markdown('Modular exponentiation entangles the registers, so the tensor train needs enough bond dimension: error falls from order 1 at chi=4 to machine precision once the cap exceeds the true rank, after which the **measured rank saturates**.')
        sh2 = sh.assign(size=sh.system_size.astype(str) + ' qubits')
        sh2_t = sh_t.assign(size=sh_t.system_size.astype(str) + ' qubits')
        c1, c2 = st.columns(2)
        c1.altair_chart(lines(sh2, 'bond_dimension:Q', 'error_plot:Q', 'size:N', 'Truncation error |1 - norm^2| vs bond cap', 'error (floor 1e-16)'), use_container_width=True)
        c2.altair_chart(lines(sh2, 'bond_dimension:Q', 'measured_rank:Q', 'size:N', 'Measured rank vs bond cap', 'max bond rank', log=False), use_container_width=True)
        c3, c4 = st.columns(2)
        c3.altair_chart(lines(sh2_t, 'bond_dimension:Q', 'wall_time_sec:Q', 'size:N', 'Wall time vs bond cap', 'seconds'), use_container_width=True)
        c4.altair_chart(lines(sh2, 'bond_dimension:Q', 'peak_mem_mb:Q', 'size:N', 'Memory delta vs bond cap', 'MB (RSS delta)', log=False), use_container_width=True)
        piv = sh.pivot(index='system_size', columns='bond_dimension', values='error_metric')
        st.markdown('**Error by size (rows) and bond cap (columns)**')
        st.dataframe(piv.style.format('{:.2e}'), use_container_width=True)

    with tab_raw:
        st.dataframe(df.drop(columns=['error_plot', 'warmup']), use_container_width=True, hide_index=True)
        st.download_button('Download CSV', CSV.read_bytes(), 'mps_tt_benchmark_results.csv', 'text/csv')
        st.caption(
            'Caveats: peak_mem_mb is the change in process RSS around each trial, so it reads 0.0 for most small runs and is not a true peak. '
            'Error metrics differ per algorithm: DJ = probability of the wrong outcome, Shor = |1 - norm^2| after truncation.'
        )
