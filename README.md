# Instant Insanity with compact QAOA

**CORE completed. Best SV1 result: 4,073/4,096 correct towers (99.4385%).** Team names: still to be supplied. [Seven-slide presentation](slides.pdf).

Four cubes must show all four colours once on every tower side. Three qubits per cube encode a front/back opposite pair and a different left/right pair. Uniform six-choice initial states and constraint-preserving reflection mixers keep cube choices legal. Full-puzzle cost gates change phases, and repeated mixing concentrates probability on solutions. No known tower is inserted into the circuit.

The initial three-layer experiment minimized average cost with COBYLA. After local parameter sweeps, success-focused BFGS training and layer growth produced the 32-layer circuit. The objective is the probability of zero rule-derived cost, evaluated by exact local simulation. Saved optimized angles reproduce both experiments.

## Run and verify

Open [solution.ipynb](solution.ipynb) using qBraid's **Python 3 [UConn 2026]** kernel and run all cells from this repository root. Keep `src/`, `resources/` and `results/` beside it. Dependencies are in [requirements.txt](requirements.txt). The notebook has saved outputs and runs local Aer only; cloud evidence is loaded without resubmitting jobs. Aer/transpilation seed: 7; success-training seeds: 29 and 30. The only code module and the original helper module are included.

## Actual measured results

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|
| 4 | Compact constrained QAOA p=3 | Local Aer | 13 | 1763 | 2130 | 4096 | 3.1982% | 0.048828% | Not applicable |
| 4 | Compact constrained QAOA p=3 | aws:aws:sim:sv1 | 13 | 1763 | 2130 | 4096 | 3.0273% | 0.048828% | aws:aws:sim:sv1-4305-qjob-6ad3a0af38127b44c71b9f10 |
| 4 | Compact constrained QAOA p=32 | Local Aer | 12 | 18757 | 22288 | 4096 | 99.5117% | 0.048828% | Not applicable |
| 4 | Compact constrained QAOA p=32 | aws:aws:sim:sv1 | 12 | 18757 | 22288 | 4096 | 99.4385% | 0.048828% | aws:aws:sim:sv1-4305-qjob-6ad3a9d138127b44c71b9f9d |

Depth includes terminal measurements. The original p=3 job used 12 puzzle qubits plus a fixed marker; p=32 used exactly 12. Exact statevector success is 3.2529% and 99.5380%, respectively. Uniform legal choices give the stronger baseline **2/1296 = 0.154321%**; the required uniform-bit baseline is **2/4096**. Failed shots stay in the denominator.

**Actual SV1 charges:** 0.375 credits per job, **0.750 credits total**, from completed job metadata. Two jobs were separately approved; no paid retries ran. [Consolidated evidence](results/experiments.json) contains actual local/cloud counts, parameters, metrics, job IDs and billing metadata. The two exact submitted circuits are archived in `results/`. Classical brute force took **0.116501 s** in the recorded reference execution. This is not a quantum speedup claim.

## Checks, limitations and AI disclosure

All 4,096 encoding strings were checked against the classical cost and Hamiltonian. Qiskit independently verifies reconstructed and archived circuits. Every measured candidate is accepted or rejected using the puzzle rules; accepted towers also pass the original checker and physical-orientation reference. The success gradient was checked against finite differences. No candidate is repaired with classical search.

The deeper circuit trades more gates for higher ideal success. We have no global-optimality certificate or QPU/noise results. Exact classical simulation was used for training; hardware training would need extra measurement effort. Next: reduce cost-layer gates and compare mixers at equal training budgets.

**AI use:** Codex generated the compact encoding, mixers, optimizers, tests, experiment analysis and submission materials, reusing the qBraid starter's puzzle/cost/checking functions and unchanged Apache-2.0 helpers. Independent enumeration, circuit checks and measured-tower validation checked its work. Corrected development issues and verification details are recorded in the notebook.

Before handing in, add all team members, review the code, rehearse the five-minute presentation, and submit this public repository link through the organizers' channel by **3 PM ET, October 17, 2026**.
