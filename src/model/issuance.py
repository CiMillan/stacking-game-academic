"""
Issuance / reward baseline scaffolding.
Define R(s): per-validator baseline reward rate given network issuance, priority fees, and MEV share.
This is a placeholder; wire real data in notebooks/market/01_fee_mev_inputs.ipynb.
"""
from dataclasses import dataclass

@dataclass
class RewardInputs:
    issuance_rate_annual: float  # e.g., 0.004 = 0.4%/yr
    avg_priority_fee_rate: float # fraction of total reward attributable to tips
    avg_mev_rate: float          # fraction attributable to MEV
    network_effective_stake: float  # total effective stake (normalized to 1 if using shares)

def baseline_reward_rate(validator_share: float, x: RewardInputs) -> float:
    """
    Linear-in-share placeholder:
      R_i = validator_share * (issuance + tips + mev)
    Replace with protocol-specific curve when data is loaded.
    """
    total_rate = x.issuance_rate_annual + x.avg_priority_fee_rate + x.avg_mev_rate
    return validator_share * total_rate
