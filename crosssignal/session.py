"""Estado explícito, decisões e eventos de execução independentes do indicador."""
from dataclasses import replace
from decimal import Decimal
from .models import (Confirmation, Evaluation, Intent, Invalid, Position, Side, Signal)
from .validation import decimal_value, periods, utc, validate_candle
from .indicators import evaluate


class Session:
    def __init__(self, short=3, long=5):
        periods(short, long)
        self.short, self.long = short, long
        self.history = []
        self.evaluations = []
        self.position = None
        self.pending = None
        self.confirmations = {}
        self.blocked_until = None
        self._sequence = 0

    def decide(self, signal, time):
        time = utc(time)
        if not isinstance(signal, Signal):
            raise Invalid('SINAL_INVALIDO')
        if signal == Signal.NENHUM:
            return 'SEM_INTENCAO', 'SEM_SINAL'
        if self.pending:
            return 'IGNORAR', 'INTENCAO_PENDENTE'
        if signal == Signal.ENTRADA and self.position:
            return 'IGNORAR', 'POSICAO_JA_ABERTA'
        if signal == Signal.SAIDA and not self.position:
            return 'IGNORAR', 'SEM_POSICAO'
        self._sequence += 1
        self.pending = Intent(f'intencao-{self._sequence:04d}',
                              Side.COMPRA if signal == Signal.ENTRADA else Side.VENDA,
                              'BTCUSDT', Decimal('0.001') if not self.position else self.position.quantity,
                              time)
        return 'CRIAR_INTENCAO', 'CONDICOES_ATENDIDAS'

    def process(self, candle, evaluated_at):
        candle = validate_candle(candle)
        time = utc(evaluated_at)
        if not candle.is_closed:
            return 'CANDLE_ABERTO_IGNORADO'
        if time < candle.close_time:
            raise Invalid('FECHAMENTO_AINDA_INDISPONIVEL')
        for previous in self.history:
            if previous.open_time == candle.open_time:
                if previous == candle:
                    return 'DUPLICATA_IGNORADA'
                raise Invalid('CONFLITO_CANDLE')
        if self.history and candle.open_time < self.history[-1].open_time:
            raise Invalid('FORA_DE_ORDEM')
        if self.blocked_until is not None:
            raise Invalid('SESSAO_BLOQUEADA_POR_LACUNA')
        if self.history and candle.open_time != self.history[-1].close_time:
            self.blocked_until = candle.close_time
            raise Invalid('LACUNA_DETECTADA: novas avaliações bloqueadas')
        averages = evaluate([c.close for c in self.history] + [candle.close], self.short, self.long)
        decision, reason = self.decide(averages.signal, time)
        if averages.signal == Signal.NENHUM:
            reason = averages.reason
        result = Evaluation(candle, time, averages, decision, reason, self.position, self.pending)
        self.history.append(candle)
        self.evaluations.append(result)
        return result

    def confirm(self, confirmation):
        if not isinstance(confirmation, Confirmation):
            raise Invalid('CONFIRMACAO_INVALIDA')
        c = confirmation
        if not isinstance(c.execution_id, str) or not c.execution_id.strip():
            raise Invalid('ID_EXECUCAO_OBRIGATORIO')
        decimal_value(c.quantity)
        decimal_value(c.price)
        c = replace(c, time=utc(c.time))
        if c.execution_id in self.confirmations:
            if self.confirmations[c.execution_id] == c:
                return 'CONFIRMACAO_DUPLICADA_IGNORADA'
            raise Invalid('CONFLITO_EXECUCAO')
        intent = self.pending
        if intent is None or c.intent_id != intent.id:
            raise Invalid('INTENCAO_NAO_CORRESPONDENTE')
        if (c.side, c.symbol, c.quantity) != (intent.side, intent.symbol, intent.quantity):
            raise Invalid('EXECUCAO_INCOMPATIVEL_OU_PARCIAL')
        if c.time <= intent.created_at:
            raise Invalid('EXECUCAO_DEVE_SER_POSTERIOR_A_INTENCAO')
        self.position = Position(c.quantity, c.price, c.time) if c.side == Side.COMPRA else None
        self.pending = None
        self.confirmations[c.execution_id] = c
        return 'EXECUCAO_TOTAL_CONFIRMADA'

    def release(self, intent_id, reason):
        if reason not in ('FALHA', 'CANCELAMENTO'):
            raise Invalid('MOTIVO_DE_LIBERACAO_INVALIDO')
        if self.pending is None or self.pending.id != intent_id:
            raise Invalid('INTENCAO_NAO_CORRESPONDENTE')
        self.pending = None
        return reason

    def recover(self, candles):
        if self.position or self.pending:
            raise Invalid('RECUPERACAO_EXIGE_SESSAO_VAZIA_SEM_PENDENCIA')
        if self.blocked_until is None:
            raise Invalid('RECUPERACAO_EXIGE_LACUNA')
        validated = [validate_candle(c) for c in candles]
        if validated[:len(self.history)] != self.history:
            raise Invalid('PREFIXO_ALTERADO')
        if not validated or validated[-1].close_time < self.blocked_until:
            raise Invalid('RECUPERACAO_INCOMPLETA')
        for index, candle in enumerate(validated):
            if not candle.is_closed or (index and candle.open_time != validated[index-1].close_time):
                raise Invalid('RECUPERACAO_NAO_CONTIGUA')
        new = Session(self.short, self.long)
        new.history = validated
        return new
