"""MERA (critical transverse-field Ising chain) results page.

Results are parsed straight from the saved cell outputs of the MERA notebooks in mera/,
so the page always matches the notebooks. Stage 4 numbers appear once
data/mera_stage4_benchmarks.csv exists (written by the notebook's Stage 4 harness).
"""
import base64
import json
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

HERE = Path(__file__).parent
NB_DIR = HERE / 'mera'
STAGE4_CSV = HERE / 'data' / 'mera_stage4_benchmarks.csv'
NUM = r'(-?[\d.]+(?:e[+-]?\d+)?)'


def _cell_texts(path):
    """cell index -> (concatenated stream text, list of png bytes)."""
    nb = json.loads(path.read_text(encoding='utf-8'))
    out = {}
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] != 'code':
            continue
        text, pngs = '', []
        for o in c.get('outputs', []):
            if 'text' in o:
                text += ''.join(o['text'])
            png = o.get('data', {}).get('image/png')
            if png:
                pngs.append(base64.b64decode(png))
        if text or pngs:
            out[i] = (text, pngs)
    return out


def _find(texts, key):
    for _, (t, p) in texts.items():
        if key in t:
            return t, p
    return '', []


@st.cache_data
def load():
    r = {}
    n12, n123, n1234 = (_cell_texts(NB_DIR / f'mera_stage{s}.ipynb') for s in ('1_2', '1_2_3', '1_2_3_4'))
    n3 = n1234 or n123

    t, _ = _find(n12, 'exact formula')
    r['ed'] = pd.DataFrame(
        [dict(L=int(m[1]), exact=float(m[2]), ED=float(m[3]), abs_diff=float(m[4])) for m in re.finditer(rf'^\s*(\d+)\s+{NUM}\s+{NUM}\s+{NUM}\s*$', t, re.M)]
    )
    r['e0l'] = pd.DataFrame([dict(L=int(m[1]), E0_per_site=float(m[2])) for m in re.finditer(r'L=\s*(\d+)\s+E0/L = (-?[\d.]+)', t)])

    t, _ = _find(n12, 'E (coarse-grain)')
    r['valid'] = pd.DataFrame(
        [
            dict(L=int(m[1]), chi=int(m[2]), seed=int(m[3]), E_coarse=float(m[4]), E_state=float(m[5]), abs_diff=float(m[6]))
            for m in re.finditer(rf'^\s*(\d+)\s+(\d+)\s+(\d+)\s+{NUM}\s+{NUM}\s+{NUM}\s+[\d.]+\s*$', t, re.M)
        ]
    )
    t, _ = _find(n12, 'E_random/L')
    r['random'] = pd.DataFrame(
        [dict(L=int(m[1]), chi=int(m[2]), E_random_per_site=float(m[3]), E_exact_per_site=float(m[4])) for m in re.finditer(rf'^\s*(\d+)\s+(\d+)\s+{NUM}\s+{NUM}\s*$', t, re.M)]
    )
    t, _ = _find(n12, 'time (s)')
    r['cost'] = pd.DataFrame([dict(L=int(m[1]), chi=int(m[2]), time_s=float(m[3])) for m in re.finditer(r'^\s*(\d+)\s+(\d+)\s+([\d.]+)\s*$', t, re.M)])

    t, _ = _find(n3, 'finite diff')
    r['fd'] = pd.DataFrame(
        [dict(tensor=m[1], entry=m[2], finite_diff=float(m[3]), two_gamma=float(m[4])) for m in re.finditer(rf'^\s*([UW]\(\d, \d\))\s+\(([\d, ]+)\)\s+{NUM}\s+{NUM}\s*$', t, re.M)]
    )
    m = re.search(r'worst \|FD - 2\*Gamma\| = ([\d.e+-]+)', t)
    r['fd_worst'] = float(m[1]) if m else None
    m = re.search(r'worst \|E_coarse_grained - E_state_vector\| = ([\d.e+-]+)', ''.join(v[0] for v in n3.values()))
    r['sv_worst'] = float(m[1]) if m else None

    t, pngs = _find(n3, '--- chi = ')
    t = t + ''.join(v[0] for _, v in n3.items() if 'exact E/L' in v[0] and v[0] not in t)
    conv, chi = [], None
    for line in t.splitlines():
        m = re.match(r'--- chi = (\d+) ---', line.strip())
        if m:
            chi = int(m[1])
        m = re.match(rf'\s*it\s+(\d+)\s+E/L = {NUM}\s+err/site = {NUM}\s+\[(\d+)s\]', line)
        if m and chi:
            conv.append(dict(chi=chi, iteration=int(m[1]), E_per_site=float(m[2]), err_per_site=float(m[3]), elapsed_s=int(m[4])))
    r['conv'] = pd.DataFrame(conv)
    r['final'] = pd.DataFrame(
        [
            dict(chi=int(m[1]), iterations=int(m[2]), E_per_site=float(m[3]), err_per_site=float(m[4]), rel_err=float(m[5]), time_s=int(m[6]))
            for m in re.finditer(rf'^\s*(\d+)\s+(\d+)\s+{NUM}\s+{NUM}\s+{NUM}\s+(\d+)\s*$', t, re.M)
        ]
    )
    m = re.search(r'exact E/L = (-?[\d.]+)', t)
    r['exact_per_site'] = float(m[1]) if m else None
    cell3 = [v for v in n3.values() if v[1]]
    r['png'] = cell3[0][1][0] if cell3 else None
    r['stage4_in_notebook'] = bool(n1234) and any('Stage 4' in v[0] for v in n1234.values())
    return r


def stage4_rows():
    return pd.read_csv(STAGE4_CSV) if STAGE4_CSV.exists() else pd.DataFrame()


def logline(df, x, y, color, title, xt, yt, log_x=False):
    return (
        alt.Chart(df, title=title)
        .mark_line(point=True)
        .encode(
            x=alt.X(x, title=xt, scale=alt.Scale(type='log' if log_x else 'linear', zero=False)),
            y=alt.Y(y, title=yt, scale=alt.Scale(type='log')),
            color=alt.Color(color, title=None),
            tooltip=list(df.columns),
        )
        .properties(height=300)
    )


def render():
    r = load()
    st.title('MERA benchmark: critical transverse-field Ising chain')
    st.caption('H = -sum Z_i Z_{i+1} - sum X_i, periodic, L = 2^n sites. Binary MERA on CPU (NumPy + opt_einsum). Reference energy from the exact free-fermion formula, checked against exact diagonalization.')

    fin = r['final']
    c = st.columns(4)
    c[0].metric('MERA vs state vector', f"{r['sv_worst']:.1e}" if r['sv_worst'] else 'n/a', 'worst |E diff|', delta_color='off')
    c[1].metric('Gradients vs finite diff', f"{r['fd_worst']:.1e}" if r['fd_worst'] else 'n/a', 'worst |FD - 2Gamma|', delta_color='off')
    if not fin.empty:
        b = fin.sort_values('rel_err').iloc[0]
        c[2].metric(f'Best energy error (L=16, chi={int(b.chi)})', f'{b.rel_err:.1e}', 'relative, vs exact', delta_color='off')
        c[3].metric('Energy error per site', f'{b.err_per_site:.1e}', f'{int(b.iterations)} iterations', delta_color='off')

    tab_val, tab_opt, tab_cost, tab_s4 = st.tabs(['Validation (Stages 1-2)', 'Optimizer (Stage 3)', 'Cost of one evaluation', 'Stage 4 harness'])

    with tab_val:
        st.markdown('**Stage 1: exact reference.** The free-fermion formula matches brute-force exact diagonalization, and E0/L tends to -4/pi = -1.27324.')
        c1, c2 = st.columns(2)
        c1.dataframe(r['ed'].style.format({'exact': '{:.10f}', 'ED': '{:.10f}', 'abs_diff': '{:.1e}'}), use_container_width=True, hide_index=True)
        c2.dataframe(r['e0l'].style.format({'E0_per_site': '{:.8f}'}), use_container_width=True, hide_index=True)
        st.markdown('**Stage 2: coarse-grained MERA energy vs full state-vector energy** (random tensors, 24 cases over L, chi, seed).')
        v = r['valid']
        if not v.empty:
            v = v.assign(case=v.L.astype(str) + ' / chi ' + v.chi.astype(str), abs_diff_plot=v.abs_diff.clip(lower=1e-17))
            st.altair_chart(
                alt.Chart(v, title='|E coarse-grained - E state vector| (all at round-off)').mark_circle(size=70).encode(
                    x=alt.X('chi:O', title='chi'), y=alt.Y('abs_diff_plot:Q', scale=alt.Scale(type='log', domain=[1e-17, 1e-8]), title='abs difference'),
                    color=alt.Color('L:N', title='L'), tooltip=['L', 'chi', 'seed', 'E_coarse', 'E_state', 'abs_diff'],
                ).properties(height=260),
                use_container_width=True,
            )
        st.markdown('**Variational sanity check:** random MERAs sit above the exact ground state, as they must.')
        rd = r['random']
        st.dataframe(rd.style.format({'E_random_per_site': '{:.6f}', 'E_exact_per_site': '{:.6f}'}), use_container_width=True, hide_index=True)

    with tab_opt:
        st.markdown('Evenbly-Vidal updates: environments come from the same network as the energy (manual back-propagation), then SVD polar steps. The energy never increases.')
        if fin.empty:
            st.warning('No Stage 3 results found in the notebooks.')
        else:
            if not r['conv'].empty:
                cv = r['conv'].assign(chi=r['conv'].chi.astype(str))
                st.altair_chart(logline(cv, 'iteration:Q', 'err_per_site:Q', 'chi:N', 'Energy error per site vs iteration (L=16, snapshots every 40 iterations)', 'iteration', 'error per site'), use_container_width=True)
            st.markdown('**Final results (L = 16)**')
            st.dataframe(fin.style.format({'E_per_site': '{:.8f}', 'err_per_site': '{:.2e}', 'rel_err': '{:.2e}'}), use_container_width=True, hide_index=True)
            if r['exact_per_site']:
                st.caption(f"Exact E/L = {r['exact_per_site']:.8f}. chi=2 plateaus at 9.6e-3 (bond-limited). chi=4 was still improving at 200 iterations. chi=8 was only run for 120 iterations (104 s), so it is not converged and not directly comparable.")
            st.altair_chart(
                alt.Chart(fin, title='Relative energy error vs chi').mark_line(point=True).encode(
                    x=alt.X('chi:Q', scale=alt.Scale(type='log', base=2), axis=alt.Axis(values=[2, 4, 8])), y=alt.Y('rel_err:Q', scale=alt.Scale(type='log'), title='relative error'), tooltip=list(fin.columns)
                ).properties(height=260),
                use_container_width=True,
            )
        if r['png']:
            with st.expander("Convergence plot from Devang's notebook"):
                st.image(r['png'])
        st.markdown('**Gradient check: environments vs finite differences** (L=8, chi=4)')
        st.dataframe(r['fd'].style.format({'finite_diff': '{:.8f}', 'two_gamma': '{:.8f}'}), use_container_width=True, hide_index=True)

    with tab_cost:
        st.markdown('Time for one energy evaluation of a random MERA (no translation tying), CPU.')
        cost = r['cost']
        if not cost.empty:
            cc = cost.assign(chi=cost.chi.astype(str))
            c1, c2 = st.columns(2)
            c1.dataframe(cost, use_container_width=True, hide_index=True)
            c2.altair_chart(
                alt.Chart(cc, title='Evaluation time').mark_line(point=True).encode(x=alt.X('L:Q', scale=alt.Scale(type='log', base=2)), y=alt.Y('time_s:Q', title='seconds'), color='chi:N', tooltip=list(cc.columns)).properties(height=260),
                use_container_width=True,
            )
            st.caption('Cost grows steeply with chi (the notebook estimates about chi^9 per iteration) and with L until tensors are tied across sites.')

    with tab_s4:
        st.markdown(
            'Stage 4 adds translation-tied sweeps (one u and one w per layer), tolerance stopping, CSV export with peak-memory timing, and a scaling-dimension diagnostic '
            '(identity must give Delta = 0; critical Ising has Delta_sigma = 1/8, Delta_epsilon = 1).'
        )
        s4 = stage4_rows()
        up = st.file_uploader('Upload mera_stage4_benchmarks.csv', type='csv')
        if up is not None:
            s4 = pd.read_csv(up)
        if s4.empty:
            st.info('No Stage 4 results yet: the saved notebook defines the harness but has no run outputs, and mera_stage4_benchmarks.csv has not been exported. Run the Stage 4 cells (suggested grid L = 8, 16, 32 and chi = 2, 4, 8), then upload the CSV here or save it to data/mera_stage4_benchmarks.csv.')
        else:
            st.dataframe(s4, use_container_width=True, hide_index=True)
            s4p = s4.assign(chi=s4.chi.astype(str), L=s4.L.astype(str))
            c1, c2 = st.columns(2)
            c1.altair_chart(logline(s4p.assign(chi=s4.chi), 'chi:Q', 'energy_err:Q', 'L:N', 'Energy error per site vs chi', 'chi', 'error per site'), use_container_width=True)
            c2.altair_chart(logline(s4p.assign(chi=s4.chi), 'chi:Q', 'time_s:Q', 'L:N', 'Wall time vs chi', 'chi', 'seconds'), use_container_width=True)
