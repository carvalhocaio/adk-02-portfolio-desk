import pytest

from adk_02_portfolio_desk.domain import Sector, sector_of


@pytest.mark.parametrize("ticker", ["PETR3", "PETR4"])
def test_share_classes_share_the_issuer_sector(ticker: str) -> None:
    assert sector_of(ticker) is Sector.OIL_AND_GAS


@pytest.mark.parametrize("ticker", ["BOVA11", "WEGE3"])
def test_unknown_issuers_are_unclassified(ticker: str) -> None:
    assert sector_of(ticker) is Sector.UNCLASSIFIED
