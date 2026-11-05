"""Cenários reproduzíveis; preços de execução são eventos explícitos."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from .models import Candle, Confirmation, Invalid
from .session import Session


def candles(prices):
    start = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    result = []
    for i, price in enumerate(prices):
        value = Decimal(str(price))
        opening = start + timedelta(minutes=i)
        result.append(Candle('FICTICIA', 'BTCUSDT', '1m', opening,
                             opening + timedelta(minutes=1), value, value, value,
                             value, Decimal('1'), True))
    return result


def sequence_a():
    return candles(['105', '104', '103', '102', '101', '110', '90'])


def execution(session, price, identifier):
    intent = session.pending
    if intent is None:
        raise AssertionError('Cenário esperava intenção pendente')
    return Confirmation(identifier, intent.id, intent.side, intent.symbol,
                        intent.quantity, Decimal(price), intent.created_at + timedelta(seconds=1))


def replay(rows, *, confirm=False):
    session = Session()
    results = []
    for i, candle in enumerate(rows):
        results.append(session.process(candle, candle.close_time))
        if confirm and i == 5:
            session.confirm(execution(session, '110', 'compra-a'))
        if confirm and i == 6 and session.pending:
            session.confirm(execution(session, '90', 'venda-a'))
    return session, results


def expected_error(action):
    try:
        action()
    except Invalid as exc:
        return f'REJEICAO_ESPERADA: {exc}'
    raise AssertionError('A rejeição esperada não ocorreu')


def run_scenario(name, emit):
    emit(f'CENARIO {name.upper()}')
    if name == 'a':
        session = Session()
        for i, candle in enumerate(sequence_a()):
            emit(session.process(candle, candle.close_time))
            if i in (5, 6):
                c = execution(session, '110' if i == 5 else '90', f'execucao-a-{i}')
                result = session.confirm(c)
                emit(f'CONFIRMACAO execução={c.execution_id} intenção={c.intent_id} lado={c.side.value} '
                     f'quantidade={c.quantity} BTC preço={c.price} USDT horário={c.time.isoformat()} '
                     f'resultado={result} posição={"ABERTA" if session.position else "VAZIA"}')
    elif name == 'b':
        for label, prices in (
            ('constantes', ['100'] * 7),
            ('crescentes', [str(i) for i in range(100, 107)]),
            ('igualdade e alta', ['100'] * 5 + ['101']),
            ('igualdade e baixa', ['100'] * 5 + ['99']),
        ):
            emit(label)
            for result in replay(candles(prices))[1]:
                emit(result)
    elif name == 'c':
        for reason in ('CANCELAMENTO', 'FALHA'):
            session, results = replay(sequence_a())
            for result in results:
                emit(result)
            emit(f'{session.release(session.pending.id, reason)} posição={session.position} pendência={session.pending}')
    elif name == 'd':
        rows = sequence_a()
        session = Session()
        emit(session.process(replace(rows[0], is_closed=False), rows[0].open_time))
        emit(session.process(rows[0], rows[0].close_time))
        emit(session.process(rows[0], rows[0].close_time))
        emit(expected_error(lambda: session.process(replace(rows[0], volume=Decimal('2')), rows[0].close_time)))
        emit(expected_error(lambda: session.process(replace(rows[1], symbol='ETHUSDT'), rows[1].close_time)))
        emit(expected_error(lambda: session.process(replace(rows[0], open_time=rows[0].open_time-timedelta(minutes=1), close_time=rows[0].open_time), rows[0].close_time)))
        emit(expected_error(lambda: session.process(rows[2], rows[2].close_time)))
        emit(expected_error(lambda: session.process(rows[1], rows[1].close_time)))
        recovered = session.recover(rows[:3])
        emit(f'RECUPERACAO_EXPLICITA histórico={len(recovered.history)} avaliações={len(recovered.evaluations)} posição={recovered.position} pendência={recovered.pending}')
        for candle in rows[3:]:
            emit(recovered.process(candle, candle.close_time))
        # Duplicate after a crossing must not repeat its intention.
        emit(recovered.process(rows[-1], rows[-1].close_time))
    elif name == 'e':
        original = sequence_a()
        changed = original[:6] + [replace(original[6], open=Decimal('9000'), high=Decimal('9000'), low=Decimal('9000'), close=Decimal('9000'))]
        _, prefix = replay(original[:6], confirm=True)
        _, future = replay(changed, confirm=True)
        _, complete = replay(original, confirm=True)
        if prefix != future[:6] or prefix != complete[:6]:
            raise AssertionError('Futuro alterou avaliações do prefixo')
        incremental = Session()
        first = []
        for candle in original[:6]:
            first.append(incremental.process(candle, candle.close_time))
        incremental.confirm(execution(incremental, '110', 'compra-a'))
        first.append(incremental.process(original[6], original[6].close_time))
        if first != complete:
            raise AssertionError('Processamento incremental divergente')
        emit('CAUSALIDADE_VERIFICADA: prefixo idêntico com futuro diferente e processamento incremental; mesmas confirmações no prefixo.')
