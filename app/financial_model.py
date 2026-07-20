"""Revenue and EV/sales valuation projections for Crashout Recovery."""
from __future__ import annotations

from typing import TypeAlias


Number: TypeAlias = int | float
Projection: TypeAlias = dict[str, dict[str, Number]]

GROWTH_FACTORS = {
    "year1": 1,
    "year3": 4,
    "year5": 10,
}

SEEDED_GROWTH_ASSUMPTIONS = {
    "year1": (1, 0),
    "year3": (4, 2),
    "year5": (10, 4),
}


def _money(value: float) -> Number:
    """Round currency output to cents and omit a redundant decimal."""
    rounded = round(value, 2)
    return int(rounded) if rounded.is_integer() else rounded


def build_valuation_projection(
    *,
    user_count: int,
    conversion_rate: float,
    arpu: float,
    ev_sales_multiple: float = 1.8,
) -> Projection:
    """Project users, annual revenue, and valuation at years 1, 3, and 5.

    ``conversion_rate`` is a decimal fraction, so 10% is supplied as ``0.10``.
    ARPU is annual revenue per paying user.
    """
    if user_count < 0:
        raise ValueError("user_count must be non-negative")
    if not 0 <= conversion_rate <= 1:
        raise ValueError("conversion_rate must be between 0 and 1")
    if arpu < 0:
        raise ValueError("arpu must be non-negative")
    if ev_sales_multiple < 0:
        raise ValueError("ev_sales_multiple must be non-negative")

    projection: Projection = {}
    for year, growth_factor in GROWTH_FACTORS.items():
        users = user_count * growth_factor
        paying_users = users * conversion_rate
        annual_revenue = paying_users * arpu
        valuation = annual_revenue * ev_sales_multiple
        projection[year] = {
            "users": users,
            "revenue": _money(annual_revenue),
            "valuation": _money(valuation),
        }

    return projection


def build_seeded_growth_projection(
    *,
    launch_users: int,
    conversion_rate: float,
    retention_rate: float,
    arpu: float,
    ev_sales_multiple: float = 1.8,
) -> Projection:
    """Project retained paying users seeded by free launch accounts.

    Conversion and retention are decimal fractions. Projected users are rounded
    to whole people before revenue and valuation are calculated.
    """
    if launch_users < 0:
        raise ValueError("launch_users must be non-negative")
    if not 0 <= conversion_rate <= 1:
        raise ValueError("conversion_rate must be between 0 and 1")
    if not 0 <= retention_rate <= 1:
        raise ValueError("retention_rate must be between 0 and 1")
    if arpu < 0:
        raise ValueError("arpu must be non-negative")
    if ev_sales_multiple < 0:
        raise ValueError("ev_sales_multiple must be non-negative")

    paying_users_year1 = launch_users * conversion_rate
    projection: Projection = {}
    for year, (growth_factor, retention_years) in SEEDED_GROWTH_ASSUMPTIONS.items():
        users = round(
            paying_users_year1
            * (retention_rate**retention_years)
            * growth_factor
        )
        annual_revenue = users * arpu
        valuation = annual_revenue * ev_sales_multiple
        projection[year] = {
            "users": users,
            "revenue": _money(annual_revenue),
            "valuation": _money(valuation),
        }

    return projection
