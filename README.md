# The Staking Game
Risk-adjusted game-theoretic model for validator concentration in PoS.

> Validators maximize risk-adjusted utility: linear rewards vs convex costs (ops, correlated slashing, market penalties) ⇒ interior optimal share \(s_i^\*\) and decentralized equilibrium.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
make test
make sim   # add --plot for a bar chart
Core equation:

𝑠
𝑖
\*
=
𝑅
2
 
(
𝑎
𝑖
+
𝑏
𝑖
+
𝛾
𝑖
)
s 
i
\*
​
 = 
2(a 
i
​
 +b 
i
​
 +γ 
i
​
 )
R
​
 
See docs/abstract.md and docs/equations.tex.
