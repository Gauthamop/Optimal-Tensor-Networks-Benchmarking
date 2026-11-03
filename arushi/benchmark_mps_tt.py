import os
import time
import math
import psutil
import pandas as pd
import numpy as np
import quimb.tensor as qtn

OUTPUT_CSV = "mps_tt_benchmark_results.csv"

# ==========================================
# 1. DIRECT CIRCUIT SIMULATORS (MPS / TT)
# ==========================================
def simulate_deutsch_jozsa_mps(n_qubits: int, max_bond: int, balanced: bool = True):
    """
    Simulates Deutsch-Jozsa directly on an MPS with bond dimension max_bond.
    n_qubits: input qubits (total qubits = n_qubits + 1 ancilla)
    """
    total_qubits = n_qubits + 1
    ancilla = n_qubits

    # Initialize CircuitMPS
    circ = qtn.CircuitMPS(N=total_qubits)

    # Initialize ancilla to |1>
    circ.apply_gate('X', ancilla)

    # Apply Hadamard to all qubits
    for i in range(total_qubits):
        circ.apply_gate('H', i)

    # Balanced Oracle: CX from each input qubit to ancilla
    if balanced:
        for i in range(n_qubits):
            circ.apply_gate('CNOT', i, ancilla, max_bond=max_bond, cutoff=1e-12)

    # Final Hadamards on input register
    for i in range(n_qubits):
        circ.apply_gate('H', i)

    return circ.psi


def simulate_shor_modexp_tt(n_count: int, n_target: int, a: int, N: int, max_bond: int):
    """
    Simulates Controlled Modular Exponentiation kernel on a Tensor Train (MPS).
    total_qubits = n_count + n_target
    """
    total_qubits = n_count + n_target
    circ = qtn.CircuitMPS(N=total_qubits)

    # Initialize target register to |1>
    circ.apply_gate('X', n_count)

    # Hadamard on counting register
    for i in range(n_count):
        circ.apply_gate('H', i)

    # Controlled modular operations
    for k in range(n_count):
        power_val = pow(a, 2**k, N)
        for j in range(n_target - 1):
            if (power_val >> j) & 1:
                circ.apply_gate('CNOT', k, n_count + j, max_bond=max_bond, cutoff=1e-12)
                circ.apply_gate('CRX', math.pi / (j + 2), k, n_count + j + 1, max_bond=max_bond, cutoff=1e-12)

    return circ.psi

# ==========================================
# 2. BENCHMARK TRIAL WRAPPER
# ==========================================
def run_benchmark_trial(algo_type: str, params: dict, bond_dim: int):
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    start_time = time.perf_counter()

    if algo_type == "Deutsch-Jozsa":
        n_in = params["n_inputs"]
        total_qubits = n_in + 1
        mps_state = simulate_deutsch_jozsa_mps(n_in, max_bond=bond_dim, balanced=True)
        target_bitstring = "0" * n_in + "1"
        # For balanced function, target amplitude should ideally be 0.0
        fidelity_loss = abs(mps_state.amplitude(target_bitstring))**2
    else:
        n_count = params["n_count"]
        n_target = params["n_target"]
        total_qubits = n_count + n_target
        mps_state = simulate_shor_modexp_tt(n_count, n_target, params["a"], params["N"], max_bond=bond_dim)
        # Compute truncation residual norm difference from unity
        norm = abs(mps_state.norm())
        fidelity_loss = abs(1.0 - norm**2)

    wall_time = time.perf_counter() - start_time
    mem_after = process.memory_info().rss / (1024 * 1024)
    peak_mem_mb = max(mem_after - mem_before, 0.0)

    bond_sizes = mps_state.bond_sizes()
    measured_bond = max(bond_sizes) if len(bond_sizes) > 0 else 1

    return {
        "algorithm": algo_type,
        "architecture": "MPS" if algo_type == "Deutsch-Jozsa" else "TT",
        "system_size": total_qubits,
        "bond_dimension": bond_dim,
        "measured_rank": measured_bond,
        "wall_time_sec": round(wall_time, 4),
        "peak_mem_mb": round(peak_mem_mb, 2),
        "error_metric": float(f"{fidelity_loss:.6e}")
    }

# ==========================================
# 3. BENCHMARK EXECUTION
# ==========================================
def main():
    print("=" * 70)
    print("Optimal Tensor Networks Benchmarking Suite (MPS & TT)")
    print("=" * 70)

    results = []

    # 1. Deutsch-Jozsa Sweep (MPS)
    # Total sizes: 10, 16, 20, 30 qubits
    dj_sizes = [9, 15, 19, 29]
    dj_bonds = [4, 8, 16, 32]

    for n in dj_sizes:
        for chi in dj_bonds:
            res = run_benchmark_trial("Deutsch-Jozsa", {"n_inputs": n}, chi)
            results.append(res)
            print(f"[{res['algorithm']:13s}] Qubits: {res['system_size']:2d} | χ: {res['bond_dimension']:2d} | "
                  f"Time: {res['wall_time_sec']:6.4f}s | Mem: {res['peak_mem_mb']:5.2f}MB | Error: {res['error_metric']}")

    # 2. Shor's Modular Exponentiation Sweep (TT)
    # Configs: N=15 (8, 10 qubits), N=21 (13 qubits)
    shor_configs = [
        {"n_count": 4, "n_target": 4, "a": 7, "N": 15},   # 8 qubits
        {"n_count": 6, "n_target": 4, "a": 7, "N": 15},   # 10 qubits
        {"n_count": 8, "n_target": 5, "a": 2, "N": 21},   # 13 qubits
    ]
    shor_bonds = [4, 8, 16, 32]

    for cfg in shor_configs:
        for chi in shor_bonds:
            res = run_benchmark_trial("Shor_ModExp", cfg, chi)
            results.append(res)
            print(f"[{res['algorithm']:13s}] Qubits: {res['system_size']:2d} | χ: {res['bond_dimension']:2d} | "
                  f"Time: {res['wall_time_sec']:6.4f}s | Mem: {res['peak_mem_mb']:5.2f}MB | Error: {res['error_metric']}")

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print("=" * 70)
    print(f"Sweep complete! Results saved to: {OUTPUT_CSV}")
    print("=" * 70)

if __name__ == "__main__":
    main()