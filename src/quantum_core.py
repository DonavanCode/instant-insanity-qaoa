"""Compact full-puzzle QAOA; no solution strings enter the optimizer."""
import itertools
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import StatePreparation
from qiskit_aer import AerSimulator


def decode(bits, n=4):
    """Qiskit key: qubit zero is the rightmost bit. Invalid codes return None."""
    value = int(bits.replace(' ', ''), 2)
    choices = []
    for c in range(n):
        fb = (value >> (3*c)) & 3
        select = (value >> (3*c+2)) & 1
        if fb == 3:
            return None
        lr = [p for p in range(3) if p != fb][select]
        choices.append((fb, lr))
    return choices


def encode(choice):
    value = 0
    for c, (fb, lr) in enumerate(choice):
        value |= fb << (3*c)
        value |= [p for p in range(3) if p != fb].index(lr) << (3*c+2)
    return format(value, f'0{3*len(choice)}b')


def compact_energies(cubes, classical_cost):
    """Use starter cost, plus 20 per forbidden three-bit code.

    For a forbidden fb=3 code, score its fb=0 surrogate and add 20.
    This local extension keeps the Hamiltonian sparse and strictly positive
    on forbidden strings. All permitted strings use the starter cost exactly.
    """
    n = len(cubes)
    values = np.empty(2**(3*n))
    for value in range(len(values)):
        x, y, invalid = [], [], 0
        for c in range(n):
            fb = (value >> (3*c)) & 3
            select = (value >> (3*c+2)) & 1
            invalid += fb == 3
            fb = fb if fb < 3 else 0
            lr = [p for p in range(3) if p != fb][select]
            x.append([int(p == fb) for p in range(3)])
            y.append([int(p == lr) for p in range(3)])
        values[value] = classical_cost(cubes, x, y) + 20*invalid
    return values


def walsh_terms(values):
    """Exact diagonal Hamiltonian as coefficients of products of Z."""
    coeff = np.array(values, dtype=float).copy()
    size = 1
    while size < len(coeff):
        blocks = coeff.reshape(-1, 2*size)
        a, b = blocks[:, :size].copy(), blocks[:, size:].copy()
        blocks[:, :size], blocks[:, size:] = a+b, a-b
        size *= 2
    coeff /= len(coeff)
    return [(mask, float(v)) for mask, v in enumerate(coeff) if abs(v) > 1e-10]


def evolve(angles, values):
    """Exact QAOA with uniform-six start and per-cube projection mixer."""
    n = int(np.log2(len(values)))
    p = len(angles)//2
    local = np.array([1,1,1,0,1,1,1,0], complex)/np.sqrt(6)
    state = local.copy()
    for _ in range(n//3-1):
        state = np.kron(local, state)
    for gamma, beta in zip(angles[:p], angles[p:]):
        state *= np.exp(-1j*gamma*values)
        for c in range(n//3):
            blocks = state.reshape(-1, 8, 8**c)
            projection = np.einsum('j,ajk->ak', local.conj(), blocks)
            blocks += (np.exp(-2j*beta)-1)*local[None,:,None]*projection[:,None,:]
    return state


def optimize(values, seed=7):
    rng = np.random.default_rng(seed)
    history, trials = [], []
    def objective(a):
        score = float(np.abs(evolve(a, values))**2 @ values)
        history.append(score)
        return score
    # Fixed effort, selected solely on mean energy, never on known answers.
    for _ in range(10):
        start = np.r_[rng.uniform(0, np.pi, 2), rng.uniform(0, np.pi/2, 2)]
        r = minimize(objective, start, method='COBYLA', options={'maxiter':250, 'tol':1e-5})
        trials.append(r)
    best = min(trials, key=lambda r:r.fun)
    # Grow from p=2 to p=3 by adding a small nonzero round.
    start = np.r_[best.x[:2], 0.2, best.x[2:], 0.2]
    r = minimize(objective, start, method='COBYLA', options={'maxiter':400, 'tol':1e-5})
    return (r.x if r.fun < best.fun else best.x), history


def circuit(angles, terms, n=12):
    qc = QuantumCircuit(n)
    local = np.array([1,1,1,0,1,1,1,0], complex)/np.sqrt(6)
    prep = StatePreparation(local)
    for c in range(n//3):
        qc.append(prep, [3*c,3*c+1,3*c+2])
    p = len(angles)//2
    for gamma, beta in zip(angles[:p], angles[p:]):
        for mask, coefficient in terms:
            if not mask:  # identity changes only an unobservable global phase
                continue
            qubits = [q for q in range(n) if (mask >> q) & 1]
            target = qubits[-1]
            for q in qubits[:-1]:
                qc.cx(q, target)
            qc.rz(2*gamma*coefficient, target)
            for q in reversed(qubits[:-1]):
                qc.cx(q, target)
        for c in range(n//3):
            q = [3*c,3*c+1,3*c+2]
            qc.append(prep.inverse(), q)
            qc.x(q)
            qc.mcp(-2*beta, q[:2], q[2])
            qc.x(q)
            qc.append(prep, q)
    return qc


def checked_counts(counts, cubes, is_two_factor, tower_from, solves):
    """All shots stay in denominator. Check every distinct measured candidate."""
    good, invalid, examples = 0, 0, []
    for key, count in counts.items():
        choice = decode(key, len(cubes))
        if choice is None:
            invalid += count
            continue
        fb, lr = zip(*choice)
        # A non-2-factor cannot be oriented into a solved tower.
        if not (is_two_factor(cubes, fb) and is_two_factor(cubes, lr)):
            continue
        tower = tower_from(cubes, choice)
        assert solves(tower)
        good += count
        examples.append({'bits':key, 'count':int(count), 'tower':tower})
    return {'shots':int(sum(counts.values())), 'good':int(good),
            'invalid':int(invalid), 'success':good/sum(counts.values()), 'examples':examples}


def objective_and_gradient(angles,values):
    """Adjoint gradient of minus zero-cost probability; exact local simulation."""
    p=len(angles)//2;n=int(np.log2(len(values)))
    local=np.array([1,1,1,0,1,1,1,0],complex)/np.sqrt(6)
    state=local.copy()
    for _ in range(n//3-1):state=np.kron(local,state)
    def project(vector,c):
        blocks=vector.reshape(-1,8,8**c)
        amplitude=np.einsum('j,ajk->ak',local.conj(),blocks)
        return (local[None,:,None]*amplitude[:,None,:]).reshape(-1)
    history=[]
    for k in range(p):
        state=state*np.exp(-1j*angles[k]*values)
        history.append(('cost',k,state.copy()))
        for c in range(n//3):
            state=state+(np.exp(-2j*angles[p+k])-1)*project(state,c)
            history.append((c,k,state.copy()))
    good=values==0
    objective=-float(np.abs(state[good])@np.abs(state[good]))
    adjoint=-(good*state);gradient=np.zeros(2*p)
    for gate,k,after in reversed(history):
        if gate=='cost':
            gradient[k]+=2*np.vdot(adjoint,-1j*values*after).real
            adjoint=adjoint*np.exp(1j*angles[k]*values)
        else:
            gradient[p+k]+=2*np.vdot(adjoint,-2j*project(after,gate)).real
            adjoint=adjoint+(np.exp(2j*angles[p+k])-1)*project(adjoint,gate)
    return objective,gradient
