"""Modelos imutáveis do laboratório."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Invalid(ValueError):
    """Evento ou configuração inválida; nenhuma operação parcial é aplicada."""


class Signal(Enum):
    ENTRADA = 'ENTRADA'
    SAIDA = 'SAIDA'
    NENHUM = 'NENHUM'


class Side(Enum):
    COMPRA = 'COMPRA'
    VENDA = 'VENDA'


@dataclass(frozen=True)
class Candle:
    source: str
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_closed: bool


@dataclass(frozen=True)
class Averages:
    short: Decimal | None
    long: Decimal | None
    previous_short: Decimal | None
    previous_long: Decimal | None
    signal: Signal
    reason: str


@dataclass(frozen=True)
class Intent:
    id: str
    side: Side
    symbol: str
    quantity: Decimal
    created_at: datetime


@dataclass(frozen=True)
class Position:
    quantity: Decimal
    price: Decimal
    opened_at: datetime


@dataclass(frozen=True)
class Confirmation:
    execution_id: str
    intent_id: str
    side: Side
    symbol: str
    quantity: Decimal
    price: Decimal
    time: datetime


@dataclass(frozen=True)
class Evaluation:
    candle: Candle
    evaluated_at: datetime
    averages: Averages
    decision: str
    reason: str
    position: Position | None
    pending: Intent | None
