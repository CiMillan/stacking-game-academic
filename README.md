# The Staking Game: A Risk-Adjusted Equilibrium of Validator Concentration in Proof-of-Stake Networks

## Abstract

We model **Proof-of-Stake (PoS) validation** as a strategic game in which each validator maximizes *risk-adjusted utility* rather than raw block rewards.  
While block-proposal probability grows linearly with staked share, operational complexity, correlated slashing risk, and delegator aversion to concentration introduce **convex costs** that bound rational growth.  
Using a quadratic approximation of these costs, we show the existence of a finite *interior equilibrium stake share* $s_i^{*}$ for each validator and derive comparative-statics conditions under which decentralization remains stable.  
Our framework bridges validator micro-economics and network-level resilience: **decentralization emerges as a Nash equilibrium** when risk and social penalties rise faster than linear rewards.  
We discuss empirical calibration for Ethereum and Cosmos networks and outline how diversity technologies—multi-client infrastructure, DVT, regional dispersion—flatten risk convexity and expand the safe operational range without centralizing control.

---

## Model and Core Equations

Let there be $N$ validators with stake shares $s_i \in [0,1]$ such that

$$
U_i'(s_i^{*})=\lambda,\qquad \forall\, i\ \text{with } s_i^{*}>0.
$$


Let there be $N$ validators with stake shares $s_i \in [0,1]$ such that

$$ \sum_{i=1}^{N} s_i = 1. $$ 

Each validator $i$ maximizes expected annualized utility 

$$ U_i(s_i,S_{-i}) = s_i R - c_i(s_i) - r_i(s_i,\rho) - p_i(s_i,S_{-i}), 
$$

where  

- $R$ — base reward rate (issuance + transaction + MEV income);  
- $c_i(s_i)$ — operational cost, increasing in $s_i$;  
- $r_i(s_i,\rho)$ — expected loss from slashing or correlated downtime, convex in $s_i$ with correlation parameter $\rho$;  
- $p_i(s_i,S_{-i})$ — market or reputational penalty capturing delegator aversion to concentration.

---

### Quadratic approximation

Assume local quadratic forms around the operating region:

$$
c_i(s_i)=a_i s_i^2, \qquad  
r_i(s_i,\rho)=b_i(\rho) s_i^2, \qquad  
p_i(s_i,S_{-i})=\gamma_i s_i^2 .
$$

Utility simplifies to

$$
U_i'(s_i^{*})=\lambda,\qquad \forall\, i \text{ with } s_i^{*}>0.
$$

The first-order condition yields the interior best response

$$
\boxed{\, s_i^{*} = \dfrac{R}{2(a_i + b_i + \gamma_i)} \,} \tag{1}
$$

producing a finite equilibrium share for each validator.  
Higher gross rewards $R$ enlarge $s_i^{*}$; higher operational, risk, or social convexities shrink it.  
Heterogeneous parameters $(a_i,b_i,\gamma_i)$ generate a stable mixed distribution of validator sizes.

System-wide equilibrium requires equality of marginal utilities:

$$
U_i'(s_i^{*})=\lambda,\qquad \forall\, i \text{ with } s_i^{*}>0.
$$

where $\lambda$ is the common marginal risk-adjusted return. Aggregating across all validators yields the stationary stake distribution

$$
\boldsymbol{s}^{*}=(s_1^{*},\ldots,s_N^{*}),\qquad \sum_{i=1}^{N} s_i^{*}=1.
$$

---

## Interpretation

Equation (1) defines a **self-limiting equilibrium**: validators expand until marginal reward equals the marginal cost of concentration and risk.  
If $a_i,b_i,\gamma_i>0$, the equilibrium share $s_i^{*}$ is strictly less than one, preventing monopoly even without explicit protocol caps.  
Protocol-level diversity incentives reduce $b_i$ (risk convexity) and $\gamma_i$ (delegator penalty) simultaneously, shifting equilibrium toward higher efficiency while preserving decentralization stability.

---

## Repository Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
make sim    # add --plot for the bar chart
