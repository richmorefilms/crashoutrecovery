import pytest

from app.financial_model import (
    build_seeded_growth_projection,
    build_valuation_projection,
)


def test_example_valuation_projection():
    assert build_valuation_projection(
        user_count=50_000,
        conversion_rate=0.10,
        arpu=120,
        ev_sales_multiple=1.8,
    ) == {
        "year1": {"users": 50_000, "revenue": 600_000, "valuation": 1_080_000},
        "year3": {"users": 200_000, "revenue": 2_400_000, "valuation": 4_320_000},
        "year5": {"users": 500_000, "revenue": 6_000_000, "valuation": 10_800_000},
    }


def test_default_multiple_and_fractional_currency():
    projection = build_valuation_projection(
        user_count=3,
        conversion_rate=0.5,
        arpu=9.99,
    )

    assert projection["year1"] == {
        "users": 3,
        "revenue": 14.98,
        "valuation": 26.97,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("user_count", -1),
        ("conversion_rate", -0.01),
        ("conversion_rate", 1.01),
        ("arpu", -1),
        ("ev_sales_multiple", -1),
    ],
)
def test_rejects_invalid_inputs(field, value):
    inputs = {
        "user_count": 50_000,
        "conversion_rate": 0.10,
        "arpu": 120,
        "ev_sales_multiple": 1.8,
    }
    inputs[field] = value

    with pytest.raises(ValueError):
        build_valuation_projection(**inputs)


def test_seeded_growth_projection_uses_retention_and_growth():
    assert build_seeded_growth_projection(
        launch_users=10_000,
        conversion_rate=0.08,
        retention_rate=0.85,
        arpu=120,
        ev_sales_multiple=1.8,
    ) == {
        "year1": {"users": 800, "revenue": 96_000, "valuation": 172_800},
        "year3": {"users": 2_312, "revenue": 277_440, "valuation": 499_392},
        "year5": {"users": 4_176, "revenue": 501_120, "valuation": 902_016},
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("launch_users", -1),
        ("conversion_rate", -0.01),
        ("conversion_rate", 1.01),
        ("retention_rate", -0.01),
        ("retention_rate", 1.01),
        ("arpu", -1),
        ("ev_sales_multiple", -1),
    ],
)
def test_seeded_growth_rejects_invalid_inputs(field, value):
    inputs = {
        "launch_users": 10_000,
        "conversion_rate": 0.08,
        "retention_rate": 0.85,
        "arpu": 120,
        "ev_sales_multiple": 1.8,
    }
    inputs[field] = value

    with pytest.raises(ValueError):
        build_seeded_growth_projection(**inputs)
