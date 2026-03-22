"""Onchain Bonus checks (up to +25 points).

Sub-factors:
- Transaction Success Rate (10 pts)
- Real Volume (10 pts)
- Staking / Commitment (5 pts)

MVP: Stub implementation — returns 0 for all sub-factors.
Will connect to Solana RPC and on-chain analytics in V2.
"""

from typing import Any


async def run_onchain_bonus(base_url: str) -> dict:
    """Stub: returns 0 for all onchain sub-factors in MVP."""
    return {
        "score": 0,
        "max": 25,
        "applicable": False,
        "sub_factors": {
            "transaction_success_rate": {
                "score": 0,
                "max": 10,
                "label": "Transaction Success Rate",
                "evidence": {"reason": "Not applicable or not implemented in MVP"},
            },
            "real_volume": {
                "score": 0,
                "max": 10,
                "label": "Real Volume",
                "evidence": {"reason": "Not applicable or not implemented in MVP"},
            },
            "staking_commitment": {
                "score": 0,
                "max": 5,
                "label": "Staking / Commitment",
                "evidence": {"reason": "Not applicable or not implemented in MVP"},
            },
        },
    }
