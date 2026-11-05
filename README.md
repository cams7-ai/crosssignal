# CrossSignal

Laboratório didático independente de cruzamento de médias móveis simples, usando
Python 3.11+ e somente biblioteca padrão em execução. Todos os dados são fictícios,
locais e fixos. Não acessa exchanges, rede ou credenciais.

Execute na raiz do repositório, sem instalação ou dependências adicionais:

```bash
python -m crosssignal
python -m crosssignal --cenario a
python -m crosssignal --cenario b
python -m crosssignal --cenario c
python -m crosssignal --cenario d
python -m crosssignal --cenario e
python -m crosssignal --arquivo data/exemplos/cruzamento.json
python -m crosssignal --arquivo data/exemplos/cruzamento.json --curta 1 --longa 2
python -m crosssignal --curta 3 --longa 5
python -m crosssignal --help
python -m unittest discover -s tests -v
```

As demonstrações exigem 3/5 para preservar seus cálculos manuais. O modo de arquivo
aceita quaisquer períodos inteiros com `1 <= curta < longa`. A API Python rejeita
booleanos. O modo de arquivo produz intenções, sem confirmar operações.

## Estrutura

- `crosssignal/models.py`: modelos imutáveis de candle, médias/sinal, avaliação,
  intenção, confirmação e posição; enums de sinal e lado.
- `crosssignal/validation.py`: contrato de dados, JSON e períodos.
- `crosssignal/indicators.py`: cálculos puros de médias e cruzamentos.
- `crosssignal/session.py`: histórico, decisão, posição, pendência e confirmações.
- `crosssignal/scenarios.py`: cinco cenários com sessões independentes.
- `crosssignal/__main__.py`: argumentos, apresentação e códigos de saída.
- `data/exemplos/`: fixtures de cruzamento, igualdade, ausência de cruzamento,
  lacuna e recuperação.
- `tests/test_crosssignal.py`: testes determinísticos da API e da interface.
- `docs/sprint04.md`: especificação original, preservada.
- `docs/sprint04-glossario.md` e `docs/sprint04-validacao.md`: conceitos e evidências.

## Contrato de entrada

JSON estrito com somente `schema_version: 1` (inteiro real) e `candles` (lista).
Cada candle contém exatamente `source`, `symbol`, `interval`, `open_time`,
`close_time`, `open`, `high`, `low`, `close`, `volume`, `is_closed`.
Veja os arquivos completos em `data/exemplos/`.

Origem/par/intervalo admitidos: `FICTICIA`, `BTCUSDT`, `1m`. OHLC são strings
decimais positivas; volume é string decimal não negativa. A gramática é
`[0-9]+(\.[0-9]+)?`: ponto, sem espaços, expoente ou separadores de milhares.
A API usa `Decimal`, nunca float. Valores finitos têm até 100 dígitos no
coeficiente e expoente decimal absoluto até 100; valores fora disso são rejeitados.
Os limites também se aplicam às quantidades/preços de confirmação na API.

Horários ISO 8601 precisam de fuso e são normalizados para UTC. A abertura deve
estar alinhada ao minuto; fechamento é exatamente um minuto depois, fim exclusivo
de `[open_time, close_time)`. `is_closed` precisa ser booleano. Exige-se
`low <= open/close <= high`. Chaves ausentes, extras ou duplicadas, JSON inválido,
NaN/Infinity e versões diferentes são rejeitados.

`Session.process(candle, evaluated_at)` recebe explicitamente o instante de
avaliação. Para candle fechado, esse instante precisa ser igual ou posterior ao
fechamento. As fixtures usam o próprio fechamento. O relatório distingue abertura,
fechamento/disponibilidade e avaliação; médias ausentes aparecem como `null`.

## Médias, igualdade e precisão

`SMA(n,t) = soma dos últimos n fechamentos válidos, incluindo t) / n`.
As médias atuais aparecem assim que há dados para suas próprias janelas. Para
comparar anterior e atual, exige-se `longa + 1` candles. Com 3/5, o quinto candle
já permite médias atuais, mas continua em aquecimento; o primeiro cruzamento
possível é no sexto.

- ENTRADA: curta anterior <= longa anterior e curta atual > longa atual.
- SAIDA: curta anterior >= longa anterior e curta atual < longa atual.
- NENHUM: nenhum cruzamento; no aquecimento, `HISTORICO_INSUFICIENTE`.

Igualdade atual não produz sinal; igualdade anterior pode produzir sinal se houver
separação estrita atual. Permanecer acima ou abaixo não repete sinal.

Para decidir, as somas usam `Fraction` criada diretamente dos Decimals e
multiplicação cruzada dos tamanhos das janelas. São razões exatas com inteiros de
precisão arbitrária; não há falso cruzamento por arredondamento, mesmo se as
médias tiverem a mesma representação exibida. As médias numéricas são convertidas
para Decimal em contexto local novo de precisão 28, `ROUND_HALF_EVEN`, preservando
precisão, flags e traps externos. Somente a apresentação limita a seis casas;
essa representação não participa da decisão. O contexto da apresentação também
é isolado e comporta os limites de magnitude do contrato.

## Fluxo de estados e eventos

A decisão verifica somente posição e pendência. ENTRADA com posição vazia cria
intenção de compra de `0.001 BTC`; SAIDA com posição aberta cria intenção de venda
da quantidade integral. Intenções recebem IDs sequenciais determinísticos por
sessão. Criar intenção preserva a posição. ENTRADA com posição aberta informa
`POSICAO_JA_ABERTA`; SAIDA com posição vazia informa `SEM_POSICAO`. Sinais continuam
sendo calculados durante uma pendência, mas são bloqueados por `INTENCAO_PENDENTE`.

`Session.confirm(Confirmation(...))` exige ID de execução não vazio, intenção
correspondente, lado/par/quantidade exatos, preço positivo e horário estritamente
posterior à criação da intenção. Não há execução parcial ou no mesmo fechamento
do sinal. Uma compra confirmada abre posição; venda confirmada encerra posição.
Os preços 110 e 90 e os horários +1 segundo do cenário A são eventos fornecidos
explicitamente, sem seleção automática de preços futuros.

`Session.release(intent_id, 'CANCELAMENTO' ou 'FALHA')` libera a pendência e
preserva a posição. Não tenta novamente sem um novo cruzamento. Repetir confirmação
idêntica é inócuo, inclusive depois de encerrada a intenção; reutilizar ID com outro
conteúdo é conflito. Deduplicação existe apenas em memória, sem recuperação após
reinício. Rejeições de execução preservam integralmente o estado.

## Qualidade, lacunas e causalidade

Candles abertos são ignorados; sua versão fechada pode chegar depois. Duplicata
fechada exata é ignorada, inclusive Decimals equivalentes com zeros finais
diferentes. Conteúdo divergente na mesma abertura é conflito. Novo evento anterior
ao último aceito é rejeitado. O fluxo não é ordenado silenciosamente.

Uma lacuna bloqueia novas avaliações sem incorporar o candle posterior e preserva
posição/pendência. Esse bloqueio é a mudança explícita de estado da detecção;
não há aplicação parcial do candle. Não há preenchimento artificial.

A recuperação didática via `Session.recover(candles)` exige sessão bloqueada,
posição vazia e ausência de pendência. Valida prefixo inalterado e conjunto fechado
contíguo cobrindo pelo menos o candle que detectou a lacuna. Retorna **nova sessão**
com histórico dos indicadores, sem avaliações, intenções ou operações retroativas;
a sessão original continua bloqueada. O próximo candle compara o histórico
reconstruído. O cenário D mostra isso; a fixture `recuperacao.json` contém os três
candles completos correspondentes a `lacuna.json`. Essa API não é um comando de
recuperação operacional.

O processamento é candle a candle e usa somente o prefixo disponível. O cenário E
compara avaliações com futuros diferentes e processamento incremental, fornecendo
as mesmas confirmações no prefixo.

## Saída e limites

Código 0: execução concluída, inclusive rejeições esperadas nos cenários.
Código 1: falha de leitura/arquivo ou exceção inesperada (com traceback).
Código 2: JSON/dados/configuração inválidos ou bloqueio por lacuna no modo arquivo.
Argumentos inválidos do argparse também retornam 2.

Sem backtest, rentabilidade, saldo, taxas, persistência, otimização, stops, venda
descoberta ou gestão de risco. A quantidade fixa é convenção didática. Saldo,
aprovação de risco e controles operacionais precisariam de outras etapas. O
histórico e a deduplicação crescem em memória, adequados a este laboratório local.
As fixtures são dados de repositório, executados a partir da raiz; o pacote não
precisa delas para implementar a API ou executar os cenários.
