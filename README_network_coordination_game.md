# Network Coordination Game for the Staking Game (PoS)

## Overview
We extend **The Staking Game** by embedding validator interactions within a **network coordination game**.  
Each validator is a node \( i \in V \) on a network \( G=(V,E) \). Validators influence each other’s adoption of coordination-sensitive behaviors—e.g., MEV-Boost, distributed validator tech (DVT), and client diversity. Coordination can yield decentralized or centralized equilibria depending on network effects and risk.

---

## 1. Model Setup (Binary Actions)
Each validator chooses \( a_i \in \{0,1\} \) (adopt vs not).

Parameters per validator \( i \):
- \( \alpha_i \): intrinsic private benefit of adopting
- \( c_i \): private cost (ops, risk, compliance)
- \( \beta>0 \): coordination strength; benefits from adopting neighbors
- \( N(i) \): neighbors of \( i \) in \( G \)

**Payoff**
\[
u_i(a_i, a_{N(i)}) \;=\; \alpha_i a_i \;+\; \beta a_i \sum_{j \in N(i)} a_j \;-\; c_i a_i .
\]

**Best response (threshold rule)**
\[
a_i = \begin{cases}
1, & \text{if } \alpha_i - c_i + \beta \sum_{j\in N(i)} a_j \ge 0,\\
0, & \text{otherwise.}
\end{cases}
\]
Equivalently, adopt iff at least
\[
T_i \;=\; \left\lceil \dfrac{c_i - \alpha_i}{\beta} \right\rceil
\]
neighbors have adopted.

**Equilibria & cascades.** Nash equilibria are the fixed points of this threshold rule. Multiple equilibria are typical: all-0, all-1, and partial cluster equilibria. Best-response dynamics (asynchronous or synchronous) generate adoption cascades when vulnerable sets percolate.

---

## 2. Continuous Actions (Smooth Response)
Let \( a_i \in [0,1] \) with quadratic costs and adjacency matrix \( A \):
\[
u_i \;=\; \alpha_i a_i \;+\; \beta a_i \sum_j A_{ij} a_j \;-\; \tfrac{1}{2}\gamma_i a_i^2,\quad \gamma_i>0.
\]
**Best response**
\[
a_i^\star \;=\; \frac{\alpha_i + \beta \sum_j A_{ij} a_j}{\gamma_i}.
\]
Stacked form with \( \Gamma=\mathrm{diag}(\gamma_1,\dots,\gamma_N) \):
\[
(\Gamma - \beta A)\, a^\star \;=\; \alpha \mathbf{1}.
\]
A unique interior equilibrium exists if \( \rho(\beta \Gamma^{-1} A) < 1 \) (spectral radius \( \rho \)).

---

## 3. Stability & Interpretation
- Low \( \beta \): decisions are local → more decentralization.
- High \( \beta \): strong peer pressure → coordination traps possible.
- High \( \gamma_i \): steep marginal cost → resistance to conformity.
- Topology matters (hubs, clustering, core–periphery, temporal edges) → partial equilibria and inertia.

**Potential game & noise.** With symmetric interactions this is a potential game. Adding decision noise (logit) yields Ising-like behavior and selects risk-dominant equilibria.

---

## 4. PoS Mapping (Examples)
Action \( a_i \) can mean “adopt DVT,” “run MEV-Boost with a vetted relay set,” or “meet client-diversity targets.”

| Symbol        | PoS interpretation                                        |
|---------------|-----------------------------------------------------------|
| \( a_i \)     | Adoption level (binary or fractional)                     |
| \( \alpha_i \) | Private efficiency/compliance benefit                    |
| \( c_i \)     | Ops risk, switch costs, regulatory overhead               |
| \( \beta \)   | Coordination gains (compatibility, inclusion distance)    |
| \( \gamma_i \)| Risk convexity (slashing/externalities sensitivity)       |

Measure decentralization via **HHI** or effective number of operators at equilibrium.

---

## 5. Experiment Blueprint
1. Choose \( A \) (empirical or synthetic).  
2. Draw \( \alpha_i, c_i, \gamma_i \) from calibrated distributions.  
3. Run best-response (binary) or solve \( (\Gamma-\beta A)a^\star=\alpha \mathbf{1} \) (continuous).  
4. Record cascade size, equilibrium adoption, HHI, time-to-equilibrium.  
5. Stress-test via rewired graphs and parameter perturbations; use Monte Carlo to obtain uncertainty bands.

---

## 6. References
- Jackson, M. O. (2010). *Social and Economic Networks.* Princeton.  
- Morris, S. (2000). Contagion. *Review of Economic Studies*, 67(1), 57–78.  
- Jackson, M. O., & Yariv, L. (2007). Diffusion and equilibrium in network games. *AER*, 97(2), 92–98.  
- Bramoullé, Y., Kranton, R., & D’Amours, M. (2014). Strategic interaction and networks. *AER*, 104(3), 898–930.

*This section formalizes validator coordination as a network game, linking risk-adjusted utility to system-level decentralization outcomes.*


---

## 7) Interpreting the summary CSV

The Monte Carlo driver writes `reports/metrics/ncg_mc_summary_*.csv`. For each grid value:

- **`adopt_mean` and quantiles (`adopt_q10..adopt_q90`)** — probability mass of final adoption; higher means the cascade usually completes.  
- **`conv_rate`** — fraction of trials that reached a fixed point within the iteration cap; near 1.0 is stable/fast.  
- **`steps_mean`, `steps_q75`, `steps_q90`** — speed of coordination; larger values signal slower or more fragile cascades.  
- **`is_fractional`** — `1` means **fractional thresholds** (τ) were used; `0` means **integer thresholds** (β) mode.

### Mapping to PoS narratives

- Vary **τ** (fractional thresholds) to represent **delegator/peer tolerance for conformity**. Higher τ demands more adopting neighbors to flip a validator → harder cascades.  
- Vary **β** (integer-threshold mode) to represent **coordination strength** (compatibility, shared relay sets, social pressure). Higher β lowers effective thresholds → easier cascades.  
- Compare **ETH vs Cosmos** by plugging their operator edgelists. Report adoption quantiles and time-to-equilibrium to characterize how readily each ecosystem coordinates given its topology.

Tip: Convert adoption distributions into **decentralization metrics** by feeding the continuous equilibrium (or adoption weights) into HHI / \(N_{\text{eff}} = 1/\text{HHI}\) to obtain bands over τ or β.
