import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, getcontext, localcontext, ROUND_DOWN
from pathlib import Path

from crosssignal.__main__ import display, main
from crosssignal.indicators import evaluate
from crosssignal.models import Confirmation, Invalid, Side, Signal
from crosssignal.scenarios import candles, execution, replay, sequence_a, run_scenario
from crosssignal.session import Session
from crosssignal.validation import load, validate_candle


class StrategyTests(unittest.TestCase):
    def test_manual_a(self):
        session = Session()
        results = []
        for candle in sequence_a()[:6]:
            results.append(session.process(candle, candle.close_time))
        self.assertEqual(results[4].averages.short, Decimal('102'))
        self.assertEqual(results[4].averages.long, Decimal('103'))
        self.assertIsNone(results[4].averages.previous_long)
        self.assertEqual(results[4].reason, 'HISTORICO_INSUFICIENTE')
        self.assertEqual(results[5].averages.short, Decimal('104.3333333333333333333333333'))
        self.assertEqual(results[5].averages.long, Decimal('104'))
        self.assertEqual(results[5].averages.signal, Signal.ENTRADA)
        self.assertIsNone(session.position)
        session.confirm(execution(session, '110', 'buy'))
        self.assertEqual(session.position.quantity, Decimal('0.001'))
        candle = sequence_a()[6]
        out = session.process(candle, candle.close_time)
        self.assertEqual(out.averages.signal, Signal.SAIDA)
        self.assertEqual(out.averages.short, Decimal('100.3333333333333333333333333'))
        self.assertEqual(out.averages.long, Decimal('101.2'))
        self.assertEqual(out.pending.side, Side.VENDA)
        session.confirm(execution(session, '90', 'sell'))
        self.assertIsNone(session.position)
        self.assertIsNone(session.pending)

    def test_b_and_no_repeated_signal(self):
        for values in (['100'] * 7, [str(i) for i in range(100, 107)]):
            with self.subTest(values=values):
                session, rows = replay(candles(values))
                self.assertTrue(all(r.averages.signal == Signal.NENHUM for r in rows))
                self.assertIsNone(session.pending)
        for last, signal in [('101', Signal.ENTRADA), ('99', Signal.SAIDA)]:
            values = [Decimal('100')] * 5 + [Decimal(last)]
            self.assertEqual(evaluate(values).signal, signal)
            self.assertEqual(evaluate(values + [Decimal(last)]).signal, Signal.NENHUM)
        self.assertEqual(evaluate(list(map(Decimal, ['90','90','100','100','100','100','100']))).signal, Signal.NENHUM)

    def test_history_and_configurable_periods(self):
        for n in range(6):
            a = evaluate([Decimal('100')] * n)
            self.assertEqual(a.signal, Signal.NENHUM)
            self.assertEqual(a.short is None, n < 3)
            self.assertEqual(a.long is None, n < 5)
            self.assertEqual(a.previous_short is None, n < 4)
            self.assertIsNone(a.previous_long)
        session = Session(1, 2)
        for c in candles(['100','100','101']):
            result = session.process(c, c.close_time)
        self.assertEqual(result.averages.signal, Signal.ENTRADA)
        for short, long in [(True,5), (3,True), (0,5), (5,3), (3,3), (1.0,5), ('3',5)]:
            with self.subTest(periods=(short,long)), self.assertRaises(Invalid):
                Session(short,long)

    def test_exact_comparison_below_display_precision_and_context(self):
        values = [Decimal('100')] * 5 + [Decimal('100.000000000000000000000000000001')]
        before = getcontext().copy()
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            context.traps[next(iter(context.traps))] = True
            settings = context.copy()
            a = evaluate(values)
            self.assertEqual(a.signal, Signal.ENTRADA)
            self.assertEqual(display(a.short), display(a.long))
            self.assertEqual(context.prec, settings.prec)
            self.assertEqual(context.rounding, settings.rounding)
            self.assertEqual(context.flags, settings.flags)
            self.assertEqual(context.traps, settings.traps)
        self.assertEqual(evaluate(values), a)
        self.assertEqual(getcontext().prec, before.prec)

    def test_causal_scenarios(self):
        lines = []
        run_scenario('e', lines.append)
        self.assertIn('CAUSALIDADE_VERIFICADA', lines[-1])


class StateTests(unittest.TestCase):
    def setUp(self):
        self.session, _ = replay(sequence_a()[:6])
        self.confirmation = execution(self.session, '110', 'buy')

    def reject_unchanged(self, action):
        before = copy.deepcopy(self.session.__dict__)
        with self.assertRaises(Invalid):
            action()
        self.assertEqual(self.session.__dict__, before)

    def test_pending_blocks_exit(self):
        c = sequence_a()[6]
        pending = self.session.pending
        result = self.session.process(c, c.close_time)
        self.assertEqual(result.averages.signal, Signal.SAIDA)
        self.assertEqual(result.reason, 'INTENCAO_PENDENTE')
        self.assertIsNone(self.session.position)
        self.assertEqual(self.session.pending, pending)

    def test_position_rules(self):
        t = self.confirmation.time
        self.session.confirm(self.confirmation)
        self.assertEqual(self.session.decide(Signal.ENTRADA,t)[1], 'POSICAO_JA_ABERTA')
        empty = Session()
        self.assertEqual(empty.decide(Signal.SAIDA,t)[1], 'SEM_POSICAO')
        self.assertIsNone(empty.pending)

    def test_cancel_and_failure_do_not_retry(self):
        for reason in ('CANCELAMENTO','FALHA'):
            session, _ = replay(sequence_a()[:6])
            session.release(session.pending.id, reason)
            self.assertIsNone(session.position)
            c = sequence_a()[6]
            self.assertEqual(session.process(c,c.close_time).reason, 'SEM_POSICAO')
            self.assertIsNone(session.pending)
        self.reject_unchanged(lambda: self.session.release('missing','CANCELAMENTO'))
        self.reject_unchanged(lambda: self.session.release(self.session.pending.id,'INVALIDO'))

    def test_cancel_sale_preserves_position(self):
        self.session.confirm(self.confirmation)
        position = self.session.position
        c = sequence_a()[6]
        self.session.process(c,c.close_time)
        self.session.release(self.session.pending.id,'FALHA')
        self.assertEqual(self.session.position, position)

    def test_confirmation_validation_is_atomic(self):
        c = self.confirmation
        for changes in [dict(execution_id=' '), dict(intent_id='other'), dict(side=Side.VENDA),
                        dict(symbol='ETHUSDT'), dict(quantity=Decimal('0.0005')),
                        dict(quantity=Decimal('0')), dict(price=Decimal('-1')),
                        dict(price=Decimal('NaN')), dict(price=Decimal('Infinity')),
                        dict(price=110.0), dict(time=self.session.pending.created_at),
                        dict(time=c.time.replace(tzinfo=None)), dict(time=c.time-timedelta(minutes=1))]:
            with self.subTest(changes=changes):
                self.reject_unchanged(lambda: self.session.confirm(replace(c,**changes)))

    def test_confirmation_dedup_conflict_and_missing_intent(self):
        self.session.confirm(self.confirmation)
        self.assertEqual(self.session.confirm(self.confirmation), 'CONFIRMACAO_DUPLICADA_IGNORADA')
        self.reject_unchanged(lambda: self.session.confirm(replace(self.confirmation,price=Decimal('111'))))
        self.reject_unchanged(lambda: self.session.confirm(replace(self.confirmation,execution_id='other')))
        c = sequence_a()[6]
        self.session.process(c,c.close_time)
        pending = self.session.pending
        self.session.confirm(self.confirmation)
        self.assertEqual(self.session.pending, pending)

    def test_duplicate_candle_does_not_repeat_intent(self):
        c = sequence_a()[5]
        before = copy.deepcopy(self.session.__dict__)
        self.assertEqual(self.session.process(replace(c,close=Decimal('110.000')),c.close_time), 'DUPLICATA_IGNORADA')
        self.assertEqual(self.session.__dict__, before)

    def test_gap_preserves_pending_and_blocks_recovery(self):
        c = sequence_a()[6]
        future = replace(c,open_time=c.open_time+timedelta(minutes=1),close_time=c.close_time+timedelta(minutes=1))
        pending = self.session.pending
        with self.assertRaisesRegex(Invalid,'LACUNA'):
            self.session.process(future,future.close_time)
        self.assertEqual(self.session.pending,pending)
        self.assertEqual(len(self.session.history),6)
        self.reject_unchanged(lambda: self.session.recover(sequence_a()))
        self.session.confirm(self.confirmation)
        self.reject_unchanged(lambda: self.session.recover(sequence_a()))


class DataTests(unittest.TestCase):
    def setUp(self):
        self.rows = sequence_a()
        self.session = Session()

    def test_open_then_closed(self):
        c = self.rows[0]
        self.assertEqual(self.session.process(replace(c,is_closed=False),c.open_time), 'CANDLE_ABERTO_IGNORADO')
        self.assertEqual(self.session.history,[])
        self.session.process(c,c.close_time)
        self.assertEqual(len(self.session.history),1)

    def test_early_evaluation_and_timezone(self):
        c = self.rows[0]
        for time in (c.open_time,c.close_time.replace(tzinfo=None)):
            with self.assertRaises(Invalid):
                self.session.process(c,time)
            self.assertEqual(self.session.history,[])
        self.session.process(c,c.close_time+timedelta(seconds=5))
        self.assertNotEqual(self.session.evaluations[0].evaluated_at,c.close_time)

    def test_conflict_incompatible_and_out_of_order_are_atomic(self):
        c = self.rows[0]
        self.session.process(c,c.close_time)
        invalids = [replace(c,volume=Decimal('2')), replace(c,symbol='ETHUSDT'),
                    replace(c,source='OUTRA'),replace(c,interval='5m'),
                    replace(c,open_time=c.open_time-timedelta(minutes=1),close_time=c.open_time)]
        for bad in invalids:
            before = copy.deepcopy(self.session.__dict__)
            with self.subTest(candle=bad), self.assertRaises(Invalid):
                self.session.process(bad,c.close_time)
            self.assertEqual(self.session.__dict__,before)

    def test_gap_and_explicit_recovery_without_retroactive_intents(self):
        self.session.process(self.rows[0],self.rows[0].close_time)
        with self.assertRaisesRegex(Invalid,'LACUNA'):
            self.session.process(self.rows[2],self.rows[2].close_time)
        with self.assertRaisesRegex(Invalid,'BLOQUEADA'):
            self.session.process(self.rows[1],self.rows[1].close_time)
        self.assertEqual(len(self.session.history),1)
        # Rebuilding a prefix containing a crossing never replays decisions.
        recovered = self.session.recover(self.rows[:6])
        self.assertIsNone(recovered.pending)
        self.assertEqual(recovered.evaluations,[])
        self.assertIsNotNone(self.session.blocked_until)
        self.assertEqual(recovered.process(self.rows[6],self.rows[6].close_time).reason,'SEM_POSICAO')

    def test_invalid_recovery(self):
        self.session.process(self.rows[0],self.rows[0].close_time)
        with self.assertRaises(Invalid):
            self.session.recover(self.rows)
        with self.assertRaises(Invalid):
            self.session.process(self.rows[2],self.rows[2].close_time)
        for rows in [self.rows[:1], [self.rows[0],self.rows[2]],
                     [replace(self.rows[0],volume=Decimal('2'))]+self.rows[1:3],
                     [self.rows[0],replace(self.rows[1],is_closed=False),self.rows[2]]]:
            before = copy.deepcopy(self.session.__dict__)
            with self.subTest(rows=rows), self.assertRaises(Invalid):
                self.session.recover(rows)
            self.assertEqual(self.session.__dict__,before)

    def test_candle_validation(self):
        c = self.rows[0]
        for changes in [dict(open=Decimal('0')),dict(close=Decimal('NaN')),dict(high=Decimal('Infinity')),
                        dict(low=Decimal('106')), dict(volume=Decimal('-1')),dict(volume=1.0),dict(is_closed=1),
                        dict(open_time=c.open_time.replace(tzinfo=None)),dict(close_time=c.close_time+timedelta(seconds=1)),
                        dict(open_time=c.open_time+timedelta(seconds=1)),dict(close=Decimal('1e101'))]:
            with self.subTest(changes=changes), self.assertRaises(Invalid):
                validate_candle(replace(c,**changes))
        self.assertEqual(validate_candle(replace(c,volume=Decimal('0'))).volume,0)

    def parse(self,text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'input.json'
            path.write_text(text)
            return load(path)

    def test_strict_json(self):
        good = Path('data/exemplos/cruzamento.json').read_text()
        for text in ['{', '[]', '{"schema_version":1,"schema_version":1,"candles":[]}',
                     good.replace('"schema_version": 1','"schema_version": true'),
                     good.replace('"schema_version": 1','"schema_version": 2'),
                     good.replace('"volume": "1"','"volume": NaN',1),
                     good.replace('"volume": "1"','"volume": Infinity',1),
                     good.replace('"volume": "1"','"volume": "1e2"',1),
                     good.replace('"volume": "1"','"volume": "1,000"',1),
                     good.replace('"volume": "1"','"volume": 1',1),
                     good.replace('"volume": "1",','',1),
                     good.replace('"volume": "1"','"extra": "1", "volume": "1"',1),
                     good.replace('"volume": "1"','"volume": "1", "volume": "1"',1),
                     good.replace('"candles": [','"unexpected": 1, "candles": [',1),
                     '{"schema_version":1,"candles":{}}']:
            with self.subTest(text=text[:80]), self.assertRaises(Invalid):
                self.parse(text)
        self.assertEqual(len(self.parse(good)),7)
        normalized = self.parse(good.replace('12:00:00+00:00','09:00:00-03:00'))
        self.assertEqual(normalized[0],self.rows[0])


class CliTests(unittest.TestCase):
    def call(self,args):
        out, err = io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            code = main(args)
        return code,out.getvalue(),err.getvalue()

    def test_all_and_each_scenario(self):
        self.assertEqual(self.call([])[0],0)
        for name in 'abcde':
            with self.subTest(name=name):
                self.assertEqual(self.call(['--cenario',name])[0],0)

    def test_file_no_auto_confirmation_and_custom_periods(self):
        code,out,_ = self.call(['--arquivo','data/exemplos/cruzamento.json'])
        self.assertEqual(code,0)
        self.assertIn('FINAL posição=VAZIA intenção_pendente=intencao-0001/COMPRA',out)
        self.assertEqual(self.call(['--arquivo','data/exemplos/cruzamento.json','--curta','1','--longa','2'])[0],0)

    def test_exit_codes(self):
        self.assertEqual(self.call(['--arquivo','/tmp/crosssignal-arquivo-inexistente.json'])[0],1)
        self.assertEqual(self.call(['--arquivo','data/exemplos/lacuna.json'])[0],2)
        self.assertEqual(self.call(['--curta','0'])[0],2)
        self.assertEqual(self.call(['--curta','1','--longa','2'])[0],2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'invalid.json'
            path.write_text('{')
            self.assertEqual(self.call(['--arquivo',str(path)])[0],2)


if __name__ == '__main__':
    unittest.main()
