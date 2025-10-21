from staking_game.model import optimal_share, normalize_shares

def test_optimal_share_basic():
    s = optimal_share(R=0.03, a=0.005, b=0.010, gamma=0.005)
    assert s > 0

def test_normalize():
    shares = {"a": 0.2, "b": 0.1}
    norm = normalize_shares(shares)
    assert abs(sum(norm.values()) - 1.0) < 1e-12
