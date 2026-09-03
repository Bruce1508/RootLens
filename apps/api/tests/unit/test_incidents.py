from app.evaluation.incidents import _sample


def test_sample_is_deterministic_for_same_seed() -> None:
    order_ids = [f"order-{i}" for i in range(20)]
    first = _sample(order_ids, fraction=0.3, seed=42)
    second = _sample(order_ids, fraction=0.3, seed=42)
    assert first == second


def test_sample_differs_for_different_seeds() -> None:
    order_ids = [f"order-{i}" for i in range(20)]
    assert _sample(order_ids, fraction=0.3, seed=1) != _sample(order_ids, fraction=0.3, seed=2)


def test_sample_size_matches_fraction() -> None:
    order_ids = [f"order-{i}" for i in range(20)]
    assert len(_sample(order_ids, fraction=0.5, seed=1)) == 10


def test_sample_returns_at_least_one_when_fraction_would_round_to_zero() -> None:
    order_ids = [f"order-{i}" for i in range(3)]
    assert len(_sample(order_ids, fraction=0.08, seed=1)) == 1


def test_sample_of_empty_list_is_empty() -> None:
    assert _sample([], fraction=0.5, seed=1) == []
