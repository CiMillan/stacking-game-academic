import numpy as np
from src.models.network_coordination_game import (
    random_er_graph,
    threshold_cascade,
    continuous_equilibrium,
    hhi,
)

def main():
    N = 300
    A = random_er_graph(N, p=0.03, seed=123)
    rng = np.random.default_rng(7)

    # Params: light heterogeneity
    alpha = rng.normal(0.06, 0.02, size=N)          # private benefit
    c     = rng.normal(0.08, 0.02, size=N)          # private cost
    beta  = 0.035                                    # coordination strength
    gamma = rng.uniform(0.9, 1.3, size=N)           # convexity

    # Seed 1% of nodes
    seed = rng.choice(N, size=max(1, N // 100), replace=False)

    th = threshold_cascade(A, alpha, c, beta, seed=seed, synchronous=True)
    cont = continuous_equilibrium(A, alpha=alpha, beta=beta, gamma=gamma)

    # Example "concentration" proxy: HHI on continuous adoption levels (normalized)
    adoption_hhi = hhi(cont.a_star)

    print("=== Network Coordination Game Example ===")
    print(f"N={N}  p=0.03  beta={beta:.3f}")
    print(f"[Threshold] adoption_rate={th.adoption_rate:.3f} steps={th.steps} converged={th.converged}")
    print(f"[Continuous] unique={cont.unique_equilibrium}  rho={cont.spectral_condition:.4f}  via={cont.solved_via}")
    print(f"[Continuous] mean(a*)={cont.a_star.mean():.3f}  HHI(adoption)={adoption_hhi:.4f}")

if __name__ == "__main__":
    main()
