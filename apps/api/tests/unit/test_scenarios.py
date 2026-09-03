from app.evaluation.scenarios import SCENARIOS, scenarios_for_split
from app.evaluation.schemas import SELLER_TO_RESOLVE


def test_scenario_ids_are_unique() -> None:
    ids = [s.scenario_id for s in SCENARIOS]
    assert len(ids) == len(set(ids))


def test_total_scenario_count_matches_prd_benchmark_size() -> None:
    assert len(SCENARIOS) == 35


def test_template_counts() -> None:
    by_template: dict[str, int] = {}
    for scenario in SCENARIOS:
        by_template[scenario.template] = by_template.get(scenario.template, 0) + 1

    # 5 unanswerable scenarios reuse order_volume_decline as a nominal
    # template (no incident is applied to them), so that bucket is 10 + 5.
    assert by_template["cancellation_spike"] == 10
    assert by_template["order_volume_decline"] == 15
    assert by_template["seller_category_decline"] == 10


def test_unanswerable_count_and_fields() -> None:
    unanswerable = [s for s in SCENARIOS if s.is_unanswerable]
    assert len(unanswerable) == 5
    for scenario in unanswerable:
        assert scenario.question
        assert scenario.direction is None
        assert scenario.primary_driver is None


def test_answerable_scenarios_have_full_ground_truth() -> None:
    for scenario in SCENARIOS:
        if scenario.is_unanswerable:
            continue
        assert scenario.direction == "decrease"
        assert scenario.primary_driver in {"order_volume", "cancellation"}
        assert scenario.dimensions


def test_split_sizes_and_each_split_has_every_template_and_an_unanswerable_case() -> None:
    dev = scenarios_for_split("dev")
    held_out = scenarios_for_split("held_out")
    assert len(dev) + len(held_out) == 35
    assert len(dev) > len(held_out)

    for split_scenarios in (dev, held_out):
        templates = {s.template for s in split_scenarios}
        assert templates == {
            "cancellation_spike",
            "order_volume_decline",
            "seller_category_decline",
        }
        assert any(s.is_unanswerable for s in split_scenarios)


def test_periods_are_adjacent_and_non_overlapping() -> None:
    for scenario in SCENARIOS:
        assert scenario.comparison_period_end < scenario.current_period_start
        assert scenario.comparison_period_start <= scenario.comparison_period_end
        assert scenario.current_period_start <= scenario.current_period_end


def test_seller_flavored_scenarios_use_the_resolution_sentinel() -> None:
    seller_scenarios = [s for s in SCENARIOS if "seller" in s.dimensions]
    assert len(seller_scenarios) == 5
    for scenario in seller_scenarios:
        assert scenario.dimensions["seller"] == SELLER_TO_RESOLVE
        assert "product_category" in scenario.dimensions
