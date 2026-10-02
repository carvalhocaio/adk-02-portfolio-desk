from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .portfolio import CENT, Portfolio, Position
from .sectors import Sector, SectorClassifier, sector_of

ONE_HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class SectorExposure:
    sector: Sector
    cost: Decimal
    weight_percent: Decimal
    tickers: tuple[str, ...]


def exposure_by_sector(
    portfolio: Portfolio, classify: SectorClassifier = sector_of
) -> tuple[SectorExposure, ...]:
    total = portfolio.total_cost
    if not total:
        return ()

    grouped: defaultdict[Sector, list[Position]] = defaultdict(list)
    for position in portfolio.positions:
        grouped[classify(position.ticker)].append(position)

    exposures = (
        _summarize(sector, positions, total) for sector, positions in grouped.items()
    )
    return tuple(sorted(exposures, key=lambda e: (-e.cost, e.sector)))


def _summarize(
    sector: Sector, positions: list[Position], total: Decimal
) -> SectorExposure:
    cost = sum((position.cost for position in positions), Decimal(0))
    return SectorExposure(
        sector=sector,
        cost=cost,
        weight_percent=(cost / total * ONE_HUNDRED).quantize(CENT),
        tickers=tuple(position.ticker for position in positions),
    )
