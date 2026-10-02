class PortfolioError(Exception):
    pass


class InvalidTradeError(PortfolioError):
    pass


class InsufficientPositionError(PortfolioError):
    pass
