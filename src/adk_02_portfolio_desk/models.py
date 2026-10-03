from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

from .domain import (
    Portfolio,
    Position,
    Sector,
    SectorExposure,
    Side,
    Trade,
    exposure_by_sector,
    sector_of,
)


class _Output(BaseModel):
    model_config = ConfigDict(frozen=True)


class TradeEntry(_Output):
    ticker: str
    side: Side
    quantity: int
    price: Decimal
    notional: Decimal

    @classmethod
    def of(cls, trade: Trade) -> Self:
        return cls(
            ticker=trade.ticker,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            notional=trade.notional,
        )


class PositionEntry(_Output):
    ticker: str
    sector: Sector
    quantity: int
    average_price: Decimal
    cost: Decimal

    @classmethod
    def of(cls, position: Position) -> Self:
        return cls(
            ticker=position.ticker,
            sector=sector_of(position.ticker),
            quantity=position.quantity,
            average_price=position.average_price,
            cost=position.cost,
        )


class PortfolioReport(_Output):
    positions: list[PositionEntry]
    total_cost: Decimal

    @classmethod
    def of(cls, portfolio: Portfolio) -> Self:
        return cls(
            positions=[PositionEntry.of(p) for p in portfolio.positions],
            total_cost=portfolio.total_cost,
        )


class SectorEntry(_Output):
    sector: Sector
    cost: Decimal
    weight_percent: Decimal
    tickers: list[str]

    @classmethod
    def of(cls, exposure: SectorExposure) -> Self:
        return cls(
            sector=exposure.sector,
            cost=exposure.cost,
            weight_percent=exposure.weight_percent,
            tickers=list(exposure.tickers),
        )


class ExposureReport(_Output):
    total_cost: Decimal
    sectors: list[SectorEntry]

    @classmethod
    def of(cls, portfolio: Portfolio) -> Self:
        return cls(
            total_cost=portfolio.total_cost,
            sectors=[SectorEntry.of(e) for e in exposure_by_sector(portfolio)],
        )


class TradeReceipt(_Output):
    trade: TradeEntry
    position: PositionEntry | None

    @classmethod
    def of(cls, trade: Trade, portfolio: Portfolio) -> Self:
        position = portfolio.position(trade.ticker)
        return cls(
            trade=TradeEntry.of(trade),
            position=PositionEntry.of(position) if position else None,
        )


class ScenarioReport(_Output):
    trades: list[TradeEntry]
    projected: PortfolioReport
    projected_exposure: ExposureReport

    @classmethod
    def of(cls, trades: tuple[Trade, ...], projected: Portfolio) -> Self:
        return cls(
            trades=[TradeEntry.of(t) for t in trades],
            projected=PortfolioReport.of(projected),
            projected_exposure=ExposureReport.of(projected),
        )
