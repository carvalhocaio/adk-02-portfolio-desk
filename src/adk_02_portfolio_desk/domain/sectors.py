from collections.abc import Callable
from enum import StrEnum


class Sector(StrEnum):
    OIL_AND_GAS = "oil_and_gas"
    MINING_AND_STEEL = "mining_and_steel"
    BANKS = "banks"
    UTILITIES = "utilities"
    RETAIL = "retail"
    UNCLASSIFIED = "unclassified"


type SectorClassifier = Callable[[str], Sector]

ISSUER_CODE_LENGTH = 4

SECTOR_BY_ISSUER: dict[str, Sector] = {
    "PETR": Sector.OIL_AND_GAS,
    "PRIO": Sector.OIL_AND_GAS,
    "RECV": Sector.OIL_AND_GAS,
    "UGPA": Sector.OIL_AND_GAS,
    "VBBR": Sector.OIL_AND_GAS,
    "VALE": Sector.MINING_AND_STEEL,
    "CMIN": Sector.MINING_AND_STEEL,
    "GGBR": Sector.MINING_AND_STEEL,
    "GOAU": Sector.MINING_AND_STEEL,
    "CSNA": Sector.MINING_AND_STEEL,
    "USIM": Sector.MINING_AND_STEEL,
    "ITUB": Sector.BANKS,
    "BBDC": Sector.BANKS,
    "BBAS": Sector.BANKS,
    "SANB": Sector.BANKS,
    "BPAC": Sector.BANKS,
    "ELET": Sector.UTILITIES,
    "EQTL": Sector.UTILITIES,
    "TAEE": Sector.UTILITIES,
    "CMIG": Sector.UTILITIES,
    "SBSP": Sector.UTILITIES,
    "ENGI": Sector.UTILITIES,
    "MGLU": Sector.RETAIL,
    "LREN": Sector.RETAIL,
    "ASAI": Sector.RETAIL,
}


def sector_of(ticker: str) -> Sector:
    return SECTOR_BY_ISSUER.get(ticker[:ISSUER_CODE_LENGTH], Sector.UNCLASSIFIED)
