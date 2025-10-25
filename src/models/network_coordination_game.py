from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import numpy as np

Array = np.ndarray


def spectral_radius(M: Array) -> float:
    """Spectral radius (max abs eigenvalue)."""
    vals = np.linalg.eigvals(M)
    return float(np.max(np.abs(vals)))


def hhi(shares: Array) -> float:
    """
    Herfindahl–Hirschman Index: sum of squared shares.
    `shares` should sum to 1 (we'll normalize defensively).
    """
    shares = np.asarray(shares, dtype=float)
    s = shares / shares.sum() if shares.sum() > 0 else shares
    return float(np.sum(s * s))


@dataclass
class ThresholdResult:
    final_actions: Array          # shape (N,), 0/1
    steps: int
    converged: bool
    adoption_rate: float          # mean(final_actions)
    seed_size: int


def threshold_cascade(
    A: Array,
    alpha: Array,
    c: Array,
    beta: float,
    seed: Iterable[int],
    *,
    fractional_thresholds: Optional[Array] = None,
    synchronous: bool = False,
    max_iters: int = 10_000,
) -> ThresholdResult:
    """
    Binary coordination dynamics (threshold rule).
    - A: (N x N) adjacency (unweighted or weighted, symmetric preferred)
    - alpha, c: shape (N,)
    - beta: coordination strength (>0)
    - seed: iterable of initially adopted node indices
    - fractional_thresholds: optional tau in [0,1], adopt if (# adopted neighbors) >= tau * deg(i).
      If provided, overrides alpha/c/beta-derived integer thresholds.
    - synchronous: if True, synchronous updates; else asynchronous (random order each round).
    """
    A = np.asarray(A, dtype=float)
    N = A.shape[0]
    alpha = np.asarray(alpha, dtype=float).reshape(-1)
    c = np.asarray(c, dtype=float).reshape(-1)

    if A.shape[0] != A.shape[1]:
        raise ValueError("A must be square.")
    if alpha.shape[0] != N or c.shape[0] != N:
        raise ValueError("alpha and c must be length N.")

    # Degree vector for absolute/fractional thresholds
    deg = A.sum(axis=1)

    if fractional_thresholds is not None:
        tau = np.clip(np.asarray(fractional_thresholds, dtype=float).reshape(-1), 0.0, 1.0)
        if tau.shape[0] != N:
            raise ValueError("fractional_thresholds must be length N.")
        # Use fractional rule: need at least ceil(tau_i * deg_i) adopted neighbors
        needed = np.ceil(tau * deg).astype(int)
    else:
        # Integer thresholds from payoff inequality:
        # adopt if alpha_i - c_i + beta * (# adopted neighbors) >= 0
        # => # adopted neighbors >= (c_i - alpha_i) / beta
        # (clip at [0, deg_i])
        raw = np.where(beta > 0, (c - alpha) / beta, np.inf)
        needed = np.ceil(np.clip(raw, 0, deg)).astype(int)

    adopted = np.zeros(N, dtype=int)
    seed = list(seed)
    adopted[seed] = 1

    def adopted_neighbors_count(x: Array) -> Array:
        # If A is weighted, this is a weighted count; round for integer threshold comparisons.
        nbr = A @ x
        # For integer thresholds, we compare ints; if A is unweighted, nbr is integer already.
        return np.asarray(np.rint(nbr), dtype=int)

    steps = 0
    changed = True

    while changed and steps < max_iters:
        steps += 1
        changed = False

        nbrs = adopted_neighbors_count(adopted)

        if synchronous:
            will_adopt = (nbrs >= needed).astype(int)
            new_state = np.maximum(adopted, will_adopt)  # monotone growth
            changed = bool(np.any(new_state != adopted))
            adopted = new_state
        else:
            # Asynchronous: update in a random order each round
            order = np.random.permutation(N)
            for i in order:
                if adopted[i] == 1:
                    continue
                if nbrs[i] >= needed[i]:
                    adopted[i] = 1
                    changed = True
                    # Update local neighborhood counts efficiently (optional micro-opt omitted)

    converged = steps < max_iters
    return ThresholdResult(
        final_actions=adopted,
        steps=steps,
        converged=converged,
        adoption_rate=float(adopted.mean()),
        seed_size=int(np.sum(adopted[seed])),
    )


@dataclass
class ContinuousResult:
    a_star: Array                 # shape (N,), clipped to [0,1]
    unique_equilibrium: bool
    spectral_condition: float     # rho(beta * Gamma^{-1} A)
    solved_via: str               # "linear_solve" or "fixed_point"
    iterations: int


def continuous_equilibrium(
    A: Array,
    alpha: Array,
    beta: float,
    gamma: Array,
    *,
    clip01: bool = True,
    max_iters: int = 50_000,
    tol: float = 1e-10,
) -> ContinuousResult:
    """
    Continuous coordination equilibrium with quadratic costs:
      u_i = alpha_i a_i + beta a_i sum_j A_ij a_j - 0.5 * gamma_i * a_i^2
    Best response: a_i = (alpha_i + beta sum_j A_ij a_j) / gamma_i
    Stack: (Gamma - beta A) a = alpha * 1   (if alpha is scalar) or alpha (vector).
    We implement the vector alpha version for generality.

    Returns a^* (clipped to [0,1] if clip01), uniqueness flag via spectral radius condition,
    and whether solved via direct linear solve or fixed-point iteration fallback.
    """
    A = np.asarray(A, dtype=float)
    N = A.shape[0]
    if A.shape[0] != A.shape[1]:
        raise ValueError("A must be square.")
    alpha = np.asarray(alpha, dtype=float).reshape(-1)
    gamma = np.asarray(gamma, dtype=float).reshape(-1)
    if alpha.shape[0] not in (1, N):
        raise ValueError("alpha must be scalar or length N.")
    if gamma.shape[0] != N:
        raise ValueError("gamma must be length N.")
    if np.any(gamma <= 0):
        raise ValueError("gamma must be strictly positive.")

    # Broadcast alpha if scalar
    if alpha.shape[0] == 1:
        alpha = np.repeat(alpha[0], N)

    Gamma = np.diag(gamma)
    # Uniqueness condition (sufficient): rho(beta * Gamma^{-1} A) < 1
    try:
        GinvA = (A.T / gamma).T   # row-wise divide by gamma: Gamma^{-1} A
        rho = spectral_radius(beta * GinvA)
    except Exception:
        rho = math.inf

    # Try direct solve
    solved_via = "linear_solve"
    iters = 0
    try:
        M = Gamma - beta * A
        a = np.linalg.solve(M, alpha)
    except np.linalg.LinAlgError:
        # Fallback to fixed-point iteration: a_{t+1} = Gamma^{-1}(alpha + beta A a_t)
        solved_via = "fixed_point"
        a = np.zeros(N, dtype=float)
        Ginv = 1.0 / gamma
        for iters in range(1, max_iters + 1):
            a_new = Ginv * (alpha + beta * (A @ a))
            if clip01:
                a_new = np.clip(a_new, 0.0, 1.0)
            if np.max(np.abs(a_new - a)) < tol:
                a = a_new
                break
            a = a_new
        else:
            # Not converged—still return last iterate
            pass

    if clip01:
        a = np.clip(a, 0.0, 1.0)

    return ContinuousResult(
        a_star=a,
        unique_equilibrium=bool(rho < 1.0),
        spectral_condition=float(rho),
        solved_via=solved_via,
        iterations=iters,
    )


def random_er_graph(n: int, p: float, weighted: bool = False, seed: Optional[int] = None) -> Array:
    """
    Quick Erdos–Renyi adjacency generator (no NetworkX dependency).
    Symmetric, zero diagonal. Optionally add random positive weights on existing edges.
    """
    rng = np.random.default_rng(seed)
    M = rng.uniform(size=(n, n)) < p
    M = np.triu(M, 1)
    A = (M + M.T).astype(float)
    if weighted:
        W = rng.uniform(low=0.5, high=1.5, size=(n, n))
        W = np.triu(W, 1)
        W = W + W.T
        A = A * W
    np.fill_diagonal(A, 0.0)
    return A


def demo() -> Tuple[ThresholdResult, ContinuousResult]:
    """
    Tiny self-test to ensure the module operates.
    """
    N = 200
    A = random_er_graph(N, p=0.04, seed=42)
    alpha = np.random.default_rng(1).normal(loc=0.05, scale=0.02, size=N)
    c = np.random.default_rng(2).normal(loc=0.08, scale=0.02, size=N)
    beta = 0.03
    gamma = np.random.default_rng(3).uniform(0.8, 1.2, size=N)

    # Seed: 5 random nodes adopt initially
    seed_idx = np.random.default_rng(4).choice(N, size=5, replace=False)

    th = threshold_cascade(A, alpha, c, beta, seed=seed_idx, synchronous=True)
    cont = continuous_equilibrium(A, alpha=alpha, beta=beta, gamma=gamma)

    return th, cont


if __name__ == "__main__":
    th, cont = demo()
    print("[Threshold] adoption_rate=%.3f steps=%d converged=%s" %
          (th.adoption_rate, th.steps, th.converged))
    print("[Continuous] unique=%s rho=%.4f via=%s" %
          (cont.unique_equilibrium, cont.spectral_condition, cont.solved_via))
