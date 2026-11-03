"""Builds the IEEE-style two-column report (report/tensor_network_benchmarks_ieee.pdf)."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, FrameBreak, Image, KeepTogether, NextPageTemplate, PageTemplate, Paragraph, Spacer, Table, TableStyle

HERE = Path(__file__).parent
FONTS = Path('C:/Windows/Fonts')
for name, f in (('T', 'times.ttf'), ('T-B', 'timesbd.ttf'), ('T-I', 'timesi.ttf'), ('T-BI', 'timesbi.ttf')):
    pdfmetrics.registerFont(TTFont(name, str(FONTS / f)))
pdfmetrics.registerFontFamily('T', normal='T', bold='T-B', italic='T-I', boldItalic='T-BI')

PW, PH = 8.5 * inch, 11 * inch
ML, MR, MT, MB = 0.625 * inch, 0.625 * inch, 0.75 * inch, 0.9 * inch
GAP = 0.25 * inch
CW = (PW - ML - MR - GAP) / 2

body = ParagraphStyle('body', fontName='T', fontSize=10, leading=11.6, alignment=TA_JUSTIFY, firstLineIndent=12, spaceAfter=0)
body0 = ParagraphStyle('body0', parent=body, firstLineIndent=0)
abstract = ParagraphStyle('abs', parent=body, fontName='T-B', fontSize=9, leading=10.4, firstLineIndent=0, spaceAfter=3)
title = ParagraphStyle('title', fontName='T', fontSize=22, leading=25, alignment=TA_CENTER, spaceAfter=10)
h1 = ParagraphStyle('h1', fontName='T', fontSize=10, leading=12, alignment=TA_CENTER, spaceBefore=9, spaceAfter=4, keepWithNext=1)
h2 = ParagraphStyle('h2', fontName='T-I', fontSize=10, leading=12, spaceBefore=5, spaceAfter=2, keepWithNext=1)
cap = ParagraphStyle('cap', fontName='T', fontSize=8, leading=9.2, alignment=TA_JUSTIFY, spaceBefore=2, spaceAfter=6)
tcap = ParagraphStyle('tcap', fontName='T', fontSize=8, leading=9.2, alignment=TA_CENTER, spaceBefore=4, spaceAfter=3, keepWithNext=1)
cell = ParagraphStyle('cell', fontName='T', fontSize=8, leading=9.2, alignment=TA_CENTER)
cellh = ParagraphStyle('cellh', parent=cell, fontName='T-B')
ref = ParagraphStyle('ref', fontName='T', fontSize=8, leading=9.4, alignment=TA_JUSTIFY, leftIndent=18, firstLineIndent=-18, spaceAfter=1.5)

story = []


def H1(t): story.append(Paragraph(t.upper(), h1))
def H2(t): story.append(Paragraph(t, h2))
def P(t, first=False): story.append(Paragraph(t, body0 if first else body))


def fig(path, caption, h=None):
    img = Image(str(HERE / 'figs' / path), width=CW, height=h or CW * 0.62)
    story.append(KeepTogether([img, Paragraph(caption, cap)]))


def table(num, caption, rows, widths, align_first_left=True):
    data = [[Paragraph(str(c), cellh if r == 0 else cell) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * CW for w in widths], hAlign='CENTER')
    t.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.8, colors.black), ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black), ('LINEBELOW', (0, -1), (-1, -1), 0.8, colors.black),
                           ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5), ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(KeepTogether([Paragraph(f'TABLE {num}<br/>{caption}', tcap), t, Spacer(1, 6)]))


# ------------------------------------------------------------------ title block
story.append(Paragraph('Benchmarking Tensor-Network Ansätze for Quantum Algorithms and Many-Body Ground States: MPS/TT, PEPS and MERA', title))
story.append(FrameBreak())

# ------------------------------------------------------------------ abstract
story.append(Paragraph('<i>Abstract</i>—Tensor networks replace exponentially large quantum states by contractions of small tensors whose cost is governed by a bond dimension. '
                       'The right network depends on the entanglement structure of the problem. We report three CPU-only benchmark studies matched to that structure: '
                       'matrix product states (MPS) and tensor trains (TT) for circuit simulation (Deutsch–Jozsa and a modular-exponentiation kernel of Shor’s algorithm), '
                       'projected entangled pair states (PEPS) for variational ground states of the two-dimensional Heisenberg model, and the multiscale entanglement renormalization '
                       'ansatz (MERA) for the critical transverse-field Ising chain. For each study we measure accuracy against an exact reference as a function of bond dimension, together with run time. '
                       'The Deutsch–Jozsa MPS stays at rank 1 up to 30 qubits; the Shor TT reaches machine precision once the bond cap equals the true rank (8–16); '
                       'a layered VQE on PEPS reaches 3×10<super>−3</super> (3×3) and 1.1×10<super>−2</super> (4×4) relative energy error at bond dimensions 6 and 4 after optimizing through the truncation; '
                       'and a binary MERA reaches 1.0×10<super>−3</super> relative energy error at <i>L</i> = 16, <i>χ</i> = 4. We state the limits of each study.', abstract))
story.append(Paragraph('<i>Index Terms</i>—tensor networks, matrix product states, tensor trains, PEPS, MERA, variational quantum eigensolver, benchmarking.', abstract))

# ------------------------------------------------------------------ I. Introduction
H1('I. Introduction')
P('Simulating quantum systems classically is limited by the exponential size of the state vector. Tensor-network states trade exactness for a controllable approximation: '
  'a state on <i>N</i> sites is written as a network of tensors joined by bonds of dimension <i>χ</i>, and the cost and accuracy are set by <i>χ</i> [1]. '
  'The network geometry should match the entanglement of the target. One-dimensional chains with area-law entanglement suit MPS [2] and the equivalent TT format [3]; '
  'two-dimensional lattices suit PEPS [4]; and critical systems, whose entanglement grows logarithmically with block size, suit MERA [5].', True)
P('This report benchmarks one representative workload for each of these three families on a CPU, and compares accuracy, run time and (where recorded) memory as the bond dimension is varied. '
  'The studies are: (i) MPS/TT simulation of the Deutsch–Jozsa algorithm [6] and a controlled modular-exponentiation kernel in the style of Shor’s algorithm [7]; '
  '(ii) PEPS ground-state search for the two-dimensional Heisenberg model, both by imaginary-time evolution and by a layered variational quantum eigensolver (VQE) [10]; '
  'and (iii) a binary MERA for the critical transverse-field Ising chain. Section II describes the setups, Section III the results, and Section IV the limitations of what was measured.')

# ------------------------------------------------------------------ II. Setup
H1('II. Methods and Setup')
H2('A. Conventions')
P('The bond dimension is denoted <i>χ</i> for MPS, TT and MERA and <i>D</i> for PEPS. Accuracy is always measured against an exact reference, but the error metric depends on the study and is defined below; '
  'error values from different studies should not be compared numerically. All runs are CPU-only. The PEPS runs used a 12th-generation Intel Core i5-1235U (10 cores, 12 threads) with 7.7 GB of RAM; '
  'the hardware of the MPS/TT and MERA runs was not recorded, so run times are comparable only within a study.', True)

H2('B. Study 1: MPS and TT circuit simulation')
P('Circuits were simulated with the CircuitMPS class of quimb [8], capping the bond dimension at <i>χ</i> = 4, 8, 16 and 32 with a singular-value cutoff of 10<super>−12</super>. '
  '<b>Deutsch–Jozsa:</b> a balanced oracle (a CNOT from every input qubit to the ancilla) on <i>n</i> = 9, 15, 19 and 29 inputs plus one ancilla, i.e., 10, 16, 20 and 30 qubits. '
  'The error is the squared amplitude of the all-zeros input outcome, which must vanish for a balanced function. '
  '<b>Shor kernel:</b> a controlled-operation kernel on a tensor train with a counting register of <i>n<sub>c</sub></i> qubits and a target register of <i>n<sub>t</sub></i> qubits, '
  'for (<i>n<sub>c</sub></i>, <i>n<sub>t</sub></i>, <i>a</i>, <i>N</i>) = (4, 4, 7, 15), (6, 4, 7, 15) and (8, 5, 2, 21), i.e., 8, 10 and 13 qubits. '
  'For each counting qubit <i>k</i> the kernel applies CNOT and controlled-R<sub><i>x</i></sub> gates conditioned on the bits of <i>a</i>^(2^<i>k</i>) mod <i>N</i>; '
  'it is a simplified surrogate for modular exponentiation. Its error is the norm lost to truncation, |1 − ‖<i>ψ</i>‖<super>2</super>|. '
  'Each trial records wall time, the measured maximum bond rank, and the change in process memory (RSS).')

H2('C. Study 2: PEPS on two-dimensional lattices')
P('The model is the spin-1/2 Heisenberg Hamiltonian <i>H</i> = Σ <b>S</b><sub><i>i</i></sub>·<b>S</b><sub><i>j</i></sub> over nearest-neighbour pairs on open <i>L<sub>r</sub></i>×<i>L<sub>c</sub></i> lattices (2×2, 3×3, 4×4). '
  'Energies are evaluated by contracting the PEPS exactly to a dense state vector (feasible up to roughly 4×5 sites) and are compared with Lanczos exact diagonalization. '
  'Because the contracted state is a genuine state, its energy upper-bounds the true ground-state energy.', True)
P('<i>Simple update.</i> Starting from a Néel product state, the imaginary-time evolution exp(−<i>τH</i>) is applied bond by bond in Γ–λ form with truncation to <i>D</i> [9], '
  'using <i>τ</i> = 0.1, 0.03, 0.01 with 100 sweeps each.')
P('<i>Layered VQE on PEPS.</i> The ansatz starts from a covering of singlet dimers (a pinwheel with a free central spin on 3×3) and applies <i>P</i> layers; '
  'in each layer every bond <i>b</i> receives exp[−<i>i</i>(<i>a<sub>b</sub></i> XY<sub><i>b</i></sub> + <i>c<sub>b</sub></i> ZZ<sub><i>b</i></sub>)] with its own two angles, '
  'giving 42, 96 and 144 parameters for 2×3 (<i>P</i> = 3), 3×3 (<i>P</i> = 4) and 4×4 (<i>P</i> = 3). '
  'Without truncation the circuit is optimized on a state vector with an exact reverse-mode gradient (checked against finite differences to 10<super>−9</super>) and L-BFGS-B. '
  'The resulting angles are then applied gate by gate to a PEPS with truncation to <i>D</i>. Finally, the truncated-PEPS energy itself is minimized (“PEPS-aware” optimization), warm-started from the exact-circuit angles, '
  'using Adam [11] with a cosine-decayed step (0.03 to 0.003) and central finite-difference gradients evaluated in parallel, since the truncation has no cheap exact gradient. '
  '200 steps were used for 3×3 and 60 for 4×4. The Heisenberg model was the only Hamiltonian studied.')

H2('D. Study 3: MERA for the critical Ising chain')
P('The model is <i>H</i> = −Σ<sub><i>i</i></sub> <i>Z<sub>i</sub>Z</i><sub><i>i</i>+1</sub> − Σ<sub><i>i</i></sub> <i>X<sub>i</sub></i> with periodic boundaries and <i>L</i> = 2<super><i>n</i></super> sites. '
  'The exact ground-state energy follows from the free-fermion solution [12], <i>E</i><sub>0</sub> = −Σ<sub><i>k</i></sub> √(2 − 2cos <i>k</i>) with <i>k</i> = π(2<i>m</i> + 1)/<i>L</i>, '
  'which was checked against exact diagonalization for <i>L</i> ≤ 12 and tends to <i>E</i><sub>0</sub>/<i>L</i> → −4/π.', True)
P('The finite binary MERA places isometries on sites (2<i>j</i>, 2<i>j</i>+1) and disentanglers on (2<i>j</i>+1, 2<i>j</i>+2), with the site dimension capped at <i>χ</i>, and coarse-grains from <i>L</i> sites to two. '
  'The energy is obtained by ascending every Hamiltonian term and diagonalizing the two-site top Hamiltonian; it was validated against a brute-force state-vector evaluation. '
  'Tensors are optimized with Evenbly–Vidal updates [13]: the environment of each tensor is obtained by back-propagating through the same coarse-graining network, '
  'and the tensor is replaced by −<i>AB</i><super>T</super>, where Γ = <i>ASB</i><super>T</super> is the singular value decomposition of its environment. '
  'A step is kept only if it lowers the energy. The environments were validated against finite differences. '
  'Runs used <i>L</i> = 16 and <i>χ</i> = 2, 4 and 8 for 200, 200 and 120 iterations, one layer updated per iteration.')

# ------------------------------------------------------------------ III. Results
H1('III. Results')
H2('A. MPS and TT')
P('<i>Deutsch–Jozsa.</i> For all 16 combinations of size and bond cap the measured bond rank was 1 and the error was exactly 0, so the cap has no effect on accuracy. '
  'After discarding the first run (8.35 s, dominated by start-up cost), the wall time was 0.013–0.016 s at 10 qubits, 0.031–0.034 s at 16, 0.047–0.051 s at 20 and 0.099–0.103 s at 30 qubits: '
  'roughly linear in qubit count and independent of <i>χ</i>.', True)
P('<i>Shor kernel.</i> The kernel entangles the registers, and accuracy depends strongly on the cap (Table I, Fig. 1). The error drops from order 10<super>−1</super> at <i>χ</i> = 4 to about 10<super>−15</super> once the cap reaches '
  'the true rank, after which the measured rank saturates at 12, 16 and 8 for 8, 10 and 13 qubits. Wall times after the first run were 0.016–0.038 s.')
table('I', 'SHOR KERNEL: TRUNCATION ERROR |1 − ‖ψ‖²| VS BOND CAP χ',
      [['Qubits', 'χ = 4', 'χ = 8', 'χ = 16', 'χ = 32'],
       ['8', '4.2e−1', '5.1e−2', '2.7e−15', '2.7e−15'],
       ['10', '5.8e−1', '6.7e−2', '2.0e−15', '2.0e−15'],
       ['13', '1.4e−1', '6.7e−15', '6.7e−15', '6.7e−15']], [0.16, 0.21, 0.21, 0.21, 0.21])
fig('fig1_shor.png', 'Fig. 1. Shor kernel on a tensor train: (a) truncation error and (b) measured maximum bond rank versus the bond cap <i>χ</i>.', CW * 0.60)

H2('B. PEPS')
P('<i>Simple update.</i> Table II lists the relative energy error against exact diagonalization. The error generally falls as <i>D</i> grows: on 3×3 from 4.3×10<super>−2</super> at <i>D</i> = 2 to 9.6×10<super>−4</super> at <i>D</i> = 6. '
  'On 2×2 the error at <i>D</i> = 6 (2.2×10<super>−3</super>) is larger than at <i>D</i> = 4 (1.5×10<super>−4</super>); we did not investigate this. '
  'For 4×4, runs above <i>D</i> = 4 were not completed.', True)
table('II', 'HEISENBERG SIMPLE UPDATE: RELATIVE ENERGY ERROR VS D',
      [['Lattice', 'D = 2', 'D = 3', 'D = 4', 'D = 6'],
       ['2×2', '8.1e−2', '1.3e−2', '1.5e−4', '2.2e−3'],
       ['3×3', '4.3e−2', '2.0e−2', '4.1e−3', '9.6e−4'],
       ['4×4', '5.3e−2', '3.5e−2', '2.0e−2', '—']], [0.16, 0.21, 0.21, 0.21, 0.21])
P('<i>Variational circuit.</i> With the singlet-dimer start, the untruncated circuit reaches 10<super>−9</super> relative error on 2×3, 6×10<super>−4</super> on 3×3 (best of four seeds) and 6.8×10<super>−3</super> on 4×4 (best of two). '
  'A Néel start stalled for every seed and depth tried (13% error on 2×3 and an energy of −1.5 instead of −2.0 on 2×2); the dimer covering was essential.')
P('<i>Truncation and PEPS-aware optimization.</i> Evaluating the exact-circuit angles on a truncated PEPS loses accuracy at small <i>D</i> (Table III). '
  'Re-optimizing through the truncation reduces the error by a factor of 2 to 6 in every case, and the best results are 3.0×10<super>−3</super> on 3×3 at <i>D</i> = 6 and 1.1×10<super>−2</super> on 4×4 at <i>D</i> = 4 (Fig. 2). '
  'The 3×3 runs at <i>D</i> = 2 and 3 were still improving at 200 steps and are likely not converged; all runs used a single seed. '
  'Optimization wall time on the laptop was 346–491 s per <i>D</i> on 3×3 (200 steps) and 473 s, 1612 s and 2218 s for <i>D</i> = 2, 3, 4 on 4×4 (60 steps).')
table('III', 'VQE ON PEPS: RELATIVE ENERGY ERROR VS ED',
      [['Lattice', 'D', 'Exact angles, truncated', 'PEPS-aware'],
       ['3×3', '2', '1.9e−1', '7.4e−2'], ['3×3', '3', '1.4e−1', '5.0e−2'], ['3×3', '4', '2.2e−2', '3.6e−3'], ['3×3', '6', '1.3e−2', '3.0e−3'],
       ['4×4', '2', '3.1e−1', '1.6e−1'], ['4×4', '3', '2.6e−1', '8.6e−2'], ['4×4', '4', '6.3e−2', '1.1e−2']], [0.2, 0.14, 0.38, 0.28])
fig('fig2_peps.png', 'Fig. 2. Relative energy error versus PEPS bond dimension <i>D</i> for the simple update, the VQE angles of the exact circuit evaluated on the truncated PEPS, and the PEPS-aware VQE.', CW * 0.70)

H2('C. MERA')
P('The coarse-grained energy agreed with the state-vector energy to 1.2×10<super>−14</super> over 24 random MERAs (<i>L</i> = 4, 8, 16 and <i>χ</i> = 2, 3, 4, 6), the environments agreed with finite differences to 2.0×10<super>−9</super>, '
  'and random MERAs lay above the exact ground state as required for a variational ansatz. The optimizer lowered the energy monotonically (Fig. 3, Table IV). '
  'The exact value at <i>L</i> = 16 is <i>E</i><sub>0</sub>/<i>L</i> = −1.27528715. At <i>χ</i> = 2 the error plateaus near 9.6×10<super>−3</super> per site, which indicates a bond-limited ansatz; '
  'at <i>χ</i> = 4 the error was 1.3×10<super>−3</super> per site and still decreasing after 200 iterations. The <i>χ</i> = 8 run was stopped at 120 iterations (104 s), '
  'so its 1.6×10<super>−3</super> is not converged and should not be read as worse than <i>χ</i> = 4.', True)
table('IV', 'MERA, CRITICAL ISING, L = 16',
      [['χ', 'Iter.', 'Err./site', 'Rel. err.', 'Time (s)'],
       ['2', '200', '9.6e−3', '7.6e−3', '33'], ['4', '200', '1.3e−3', '1.0e−3', '40'], ['8', '120', '1.6e−3', '1.2e−3', '104']], [0.12, 0.18, 0.26, 0.24, 0.20])
fig('fig3_mera.png', 'Fig. 3. MERA energy error per site versus optimizer iteration for <i>L</i> = 16 (snapshots every 40 iterations).', CW * 0.66)
P('A single energy evaluation of a random, untied MERA took 0.09 s and 0.20 s at <i>L</i> = 32 and 64 for <i>χ</i> = 4, and 0.58 s and 1.54 s for <i>χ</i> = 8, showing the steep growth with <i>χ</i>.')

# ------------------------------------------------------------------ IV. Discussion
H1('IV. Discussion and Limitations')
P('The three studies illustrate the matching of network to problem. The Deutsch–Jozsa state has no entanglement growth, so rank 1 suffices at any cap and the cost is linear in size. '
  'The Shor kernel needs a bond cap at least equal to its true rank, below which truncation error is large and above which extra bond dimension buys nothing. '
  'For two-dimensional lattices, accuracy at fixed <i>D</i> is considerably worse than in one dimension, and optimizing <i>through</i> the truncation is worth a factor of 2–6 in error; '
  'for MERA, moderate <i>χ</i> already gives per-mille accuracy on a critical chain.', True)
P('The results have limits that readers should keep in mind. (1) The error metrics differ by study and are not comparable across studies. '
  '(2) The PEPS study covers the Heisenberg model on lattices up to 4×4 only; the Hubbard model, larger lattices and approximate (boundary-MPS) contraction were not studied, '
  'and the PEPS-aware results are single-seed, with 3×3 <i>D</i> = 2, 3 and 4×4 not converged. '
  '(3) The Shor kernel is a simplified surrogate, and its error measures norm loss under truncation, not the correctness of the factoring result. '
  '(4) The MPS/TT memory column is a process-memory difference that reads zero for most runs and was not used; run times come from different machines and include start-up effects in first runs. '
  '(5) For MERA, a benchmark harness with translation-tied tensors, tolerance-based stopping and a scaling-dimension diagnostic is implemented but its results were not yet available; '
  'only <i>L</i> = 16 was optimized. (6) No GPU acceleration was used or evaluated in any study.')

H1('V. Conclusion')
P('We benchmarked MPS/TT circuit simulation, PEPS variational ground states and MERA on a common error-versus-bond-dimension footing. '
  'The CPU-only results show rank-1 behavior for Deutsch–Jozsa, saturation of the Shor kernel at its true rank, a factor of 2–6 improvement from optimizing a PEPS-based VQE through its truncation, '
  'and per-mille energy accuracy for a binary MERA at modest bond dimension. Extending the PEPS study to fermionic models and larger lattices, and completing the MERA scaling campaign, are the natural next steps.', True)

# ------------------------------------------------------------------ References
H1('References')
refs = [
    'R. Orús, “A practical introduction to tensor networks: Matrix product states and projected entangled pair states,” <i>Ann. Phys.</i>, vol. 349, pp. 117–158, 2014.',
    'G. Vidal, “Efficient classical simulation of slightly entangled quantum computations,” <i>Phys. Rev. Lett.</i>, vol. 91, no. 14, Art. no. 147902, 2003.',
    'I. V. Oseledets, “Tensor-train decomposition,” <i>SIAM J. Sci. Comput.</i>, vol. 33, no. 5, pp. 2295–2317, 2011.',
    'F. Verstraete and J. I. Cirac, “Renormalization algorithms for quantum many-body systems in two and higher dimensions,” arXiv:cond-mat/0407066, 2004.',
    'G. Vidal, “Entanglement renormalization,” <i>Phys. Rev. Lett.</i>, vol. 99, no. 22, Art. no. 220405, 2007.',
    'D. Deutsch and R. Jozsa, “Rapid solution of problems by quantum computation,” <i>Proc. R. Soc. Lond. A</i>, vol. 439, pp. 553–558, 1992.',
    'P. W. Shor, “Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer,” <i>SIAM J. Comput.</i>, vol. 26, no. 5, pp. 1484–1509, 1997.',
    'J. Gray, “quimb: A python package for quantum information and many-body calculations,” <i>J. Open Source Softw.</i>, vol. 3, no. 29, Art. no. 819, 2018.',
    'H. C. Jiang, Z. Y. Weng, and T. Xiang, “Accurate determination of tensor network state of quantum lattice models in two dimensions,” <i>Phys. Rev. Lett.</i>, vol. 101, no. 9, Art. no. 090603, 2008.',
    'A. Peruzzo <i>et al.</i>, “A variational eigenvalue solver on a photonic quantum processor,” <i>Nat. Commun.</i>, vol. 5, Art. no. 4213, 2014.',
    'D. P. Kingma and J. Ba, “Adam: A method for stochastic optimization,” in <i>Proc. Int. Conf. Learn. Represent. (ICLR)</i>, 2015.',
    'P. Pfeuty, “The one-dimensional Ising model with a transverse field,” <i>Ann. Phys.</i>, vol. 57, no. 1, pp. 79–90, 1970.',
    'G. Evenbly and G. Vidal, “Algorithms for entanglement renormalization,” <i>Phys. Rev. B</i>, vol. 79, no. 14, Art. no. 144108, 2009.',
]
for i, r in enumerate(refs, 1):
    story.append(Paragraph(f'[{i}]&nbsp;&nbsp;{r}', ref))


# ------------------------------------------------------------------ page templates
def footer(canv, doc):
    canv.saveState()
    canv.setFont('T', 8)
    canv.drawCentredString(PW / 2, 0.5 * inch, str(doc.page))
    canv.restoreState()


def cols(top):
    h = PH - top - MB
    return [Frame(ML + i * (CW + GAP), MB, CW, h, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id=f'c{i}') for i in range(2)]


TITLE_H = 1.3 * inch
first = [Frame(ML, PH - MT - TITLE_H, PW - ML - MR, TITLE_H, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id='title')] + cols(MT + TITLE_H)
doc = BaseDocTemplate(str(HERE / 'tensor_network_benchmarks_ieee.pdf'), pagesize=(PW, PH), leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                      title='Benchmarking Tensor-Network Ansätze for Quantum Algorithms and Many-Body Ground States', author='')
doc.addPageTemplates([PageTemplate(id='First', frames=first, onPage=footer, autoNextPageTemplate='Later'), PageTemplate(id='Later', frames=cols(MT), onPage=footer)])
doc.build(story)
print('built')
