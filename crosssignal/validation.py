"""Contrato estrito de entrada, compartilhado por JSON e API Python."""
import json
import re
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from .models import Candle, Invalid


def utc(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise Invalid('HORARIO_INVALIDO') from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Invalid('FUSO_OBRIGATORIO')
    return value.astimezone(timezone.utc)


def decimal_value(value, *, zero=False):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise Invalid('DECIMAL_FINITO_OBRIGATORIO')
    if value < 0 or (not zero and value == 0):
        raise Invalid('VALOR_FORA_DO_LIMITE')
    # Bound resource use; comparisons themselves use exact rational arithmetic.
    if len(value.as_tuple().digits) > 100 or abs(value.as_tuple().exponent) > 100:
        raise Invalid('DECIMAL_EXCEDE_100_DIGITOS_OU_EXPOENTE')
    return value


def parse_decimal(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
        raise Invalid('STRING_DECIMAL_INVALIDA')
    return Decimal(value)


def validate_candle(c):
    if not isinstance(c, Candle):
        raise Invalid('CANDLE_INVALIDO')
    if (c.source, c.symbol, c.interval) != ('FICTICIA', 'BTCUSDT', '1m'):
        raise Invalid('ORIGEM_PAR_INTERVALO_INCOMPATIVEL')
    start, end = utc(c.open_time), utc(c.close_time)
    if start.second or start.microsecond or end != start + timedelta(minutes=1):
        raise Invalid('INTERVALO_TEMPORAL_INVALIDO')
    if type(c.is_closed) is not bool:
        raise Invalid('IS_CLOSED_DEVE_SER_BOOLEANO')
    for price in (c.open, c.high, c.low, c.close):
        decimal_value(price)
    decimal_value(c.volume, zero=True)
    if not (c.low <= c.open <= c.high and c.low <= c.close <= c.high):
        raise Invalid('OHLC_INCONSISTENTE')
    return replace(c, open_time=start, close_time=end)


def periods(short, long):
    if type(short) is not int or type(long) is not int or not 1 <= short < long:
        raise Invalid('PERIODOS: exija inteiros 1 <= curta < longa')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid('CHAVE_DUPLICADA: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise Invalid('CONSTANTE_JSON_INVALIDA: ' + value)


def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'),
                          object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise Invalid('JSON_INVALIDO') from exc
    if not isinstance(data, dict) or set(data) != {'schema_version', 'candles'}:
        raise Invalid('CAMPOS_RAIZ_INVALIDOS')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise Invalid('VERSAO_INVALIDA')
    if not isinstance(data['candles'], list):
        raise Invalid('CANDLES_DEVE_SER_LISTA')
    result = []
    expected = {f.name for f in fields(Candle)}
    for row in data['candles']:
        if not isinstance(row, dict) or set(row) != expected:
            raise Invalid('CAMPOS_CANDLE_INVALIDOS')
        row = dict(row)
        for key in ('open', 'high', 'low', 'close', 'volume'):
            row[key] = parse_decimal(row[key])
        result.append(validate_candle(Candle(**row)))
    return result
