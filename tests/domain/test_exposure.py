from decimal import Decimal

from adk_02_portfolio_desk.domain import (
    Portfolio,
    Position,
    Sector,
    SectorExposure,
    exposure_by_sector,
)


def portfolio_of(*positions: Position) -> Portfolio:
    return Portfolio(tuple(sorted(positions, key=lambda p: p.ticker)))


def test_empty_portfolio_has_no_exposure() -> None:
    assert exposure_by_sector(Portfolio()) == ()


def test_groups_positions_by_sector_ordered_by_cost() -> None:
    portfolio = portfolio_of(
        Position("PETR4", 100, Decimal("3820.00")),
        Position("PRIO3", 50, Decimal("2180.00")),
        Position("ITUB4", 100, Decimal("3500.00")),
        Position("BOVA11", 5, Decimal("500.00")),
    )

    assert exposure_by_sector(portfolio) == (
        SectorExposure(
            Sector.OIL_AND_GAS, Decimal("6000.00"), Decimal("60.00"), ("PETR4", "PRIO3")
        ),
        SectorExposure(Sector.BANKS, Decimal("3500.00"), Decimal("35.00"), ("ITUB4",)),
        SectorExposure(
            Sector.UNCLASSIFIED, Decimal("500.00"), Decimal("5.00"), ("BOVA11",)
        ),
    )


def test_ties_on_cost_break_by_sector_name() -> None:
    portfolio = portfolio_of(
        Position("VALE3", 10, Decimal("600.00")),
        Position("ITUB4", 20, Decimal("600.00")),
    )

    sectors = [e.sector for e in exposure_by_sector(portfolio)]

    assert sectors == [Sector.BANKS, Sector.MINING_AND_STEEL]


def test_weights_are_percentages_rounded_to_cents() -> None:
    portfolio = portfolio_of(
        Position("PETR4", 1, Decimal("10.00")),
        Position("VALE3", 1, Decimal("10.00")),
        Position("ITUB4", 1, Decimal("10.00")),
    )

    weights = {e.weight_percent for e in exposure_by_sector(portfolio)}

    assert weights == {Decimal("33.33")}


def test_classifier_is_injectable() -> None:
    portfolio = portfolio_of(Position("PETR4", 1, Decimal("10.00")))

    (exposure,) = exposure_by_sector(portfolio, classify=lambda _: Sector.RETAIL)

    assert exposure.sector is Sector.RETAIL
