"""Interface de terminal; formatação e saída ficam fora do domínio."""
import argparse
import sys
from decimal import Context, ROUND_HALF_EVEN, localcontext
from .models import Evaluation, Invalid
from .session import Session
from .scenarios import run_scenario
from .validation import load, periods


def display(value):
    if value is None:
        return 'null'
    with localcontext(Context(prec=210, rounding=ROUND_HALF_EVEN)):
        return format(value, '.6f').rstrip('0').rstrip('.')


def position_text(position):
    if position is None:
        return 'VAZIA'
    return f'{position.quantity} BTC a {position.price} USDT desde {position.opened_at.isoformat()}'


def intent_text(intent):
    if intent is None:
        return 'NENHUMA'
    return f'{intent.id}/{intent.side.value}/{intent.quantity} BTC/criada={intent.created_at.isoformat()}'


def report(value):
    if not isinstance(value, Evaluation):
        print(value)
        return
    a = value.averages
    print(f'candle=[{value.candle.open_time.isoformat()}, {value.candle.close_time.isoformat()}) '
          f'disponível={value.candle.close_time.isoformat()} avaliação={value.evaluated_at.isoformat()} '
          f'SMA anterior=({display(a.previous_short)}, {display(a.previous_long)}) '
          f'atual=({display(a.short)}, {display(a.long)}) '
          f'sinal={a.signal.value} decisão={value.decision} motivo={value.reason} '
          f'posição={position_text(value.position)} intenção_pendente={intent_text(value.pending)}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='CrossSignal: laboratório fictício, local, sem ordens externas.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--cenario', choices=list('abcde'), help='Cenário didático isolado (padrão: todos).')
    mode.add_argument('--arquivo', help='Fixture JSON; não confirma operações automaticamente.')
    parser.add_argument('--curta', type=int, default=3)
    parser.add_argument('--longa', type=int, default=5)
    args = parser.parse_args(argv)
    try:
        periods(args.curta, args.longa)
        if args.arquivo:
            session = Session(args.curta, args.longa)
            for candle in load(args.arquivo):
                report(session.process(candle, candle.close_time))
            print(f'FINAL posição={position_text(session.position)} intenção_pendente={intent_text(session.pending)}')
        else:
            if (args.curta, args.longa) != (3, 5):
                raise Invalid('Demonstrações fixas exigem 3/5; use --arquivo para outras janelas.')
            for name in [args.cenario] if args.cenario else 'abcde':
                run_scenario(name, report)
        return 0
    except Invalid as exc:
        print(f'REJEICAO: {exc}', file=sys.stderr)
        return 2
    except OSError as exc:
        print(f'FALHA_DE_ARQUIVO: {exc}', file=sys.stderr)
        return 1
    except Exception:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
