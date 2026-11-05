"""Cálculos puros: razões exatas para sinais; Decimal para médias exibíveis."""
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from .models import Averages, Signal
from .validation import periods


def average(values):
    if not values:
        return None
    ratio = sum(map(Fraction, values), Fraction()) / len(values)
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        return Decimal(ratio.numerator) / Decimal(ratio.denominator)


def relation(values, short, long):
    # Cross multiplication of exact rational sums: independent of Decimal context.
    return sum(map(Fraction, values[-short:]), Fraction()) * long - sum(
        map(Fraction, values[-long:]), Fraction()) * short


def evaluate(closes, short=3, long=5):
    periods(short, long)
    n = len(closes)
    current_short = average(closes[-short:]) if n >= short else None
    current_long = average(closes[-long:]) if n >= long else None
    previous = closes[:-1]
    prev_short = average(previous[-short:]) if n > short else None
    prev_long = average(previous[-long:]) if n > long else None
    signal, reason = Signal.NENHUM, 'HISTORICO_INSUFICIENTE'
    if n > long:
        before, now = relation(previous, short, long), relation(closes, short, long)
        reason = 'SEM_CRUZAMENTO'
        if before <= 0 and now > 0:
            signal, reason = Signal.ENTRADA, 'CRUZAMENTO_PARA_CIMA'
        elif before >= 0 and now < 0:
            signal, reason = Signal.SAIDA, 'CRUZAMENTO_PARA_BAIXO'
    return Averages(current_short, current_long, prev_short, prev_long, signal, reason)
