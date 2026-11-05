# Sprint 04 — Validação executada

Validação local em 5 de novembro de 2026, na raiz do repositório, com Python
3.12.14. Nenhuma dependência de execução adicional. O documento original da sprint
foi preservado.

## Comandos efetivamente executados

Cada comando abaixo foi executado como processo separado e seu código comparado
com o esperado. Códigos 1 e 2 nas entradas inválidas são resultados esperados.

| Comando | Código observado | Conferência |
| --- | --- | --- |
| `python --version` | 0 | OK |
| `python -m crosssignal` | 0 | OK |
| `python -m crosssignal --cenario a` | 0 | OK |
| `python -m crosssignal --cenario b` | 0 | OK |
| `python -m crosssignal --cenario c` | 0 | OK |
| `python -m crosssignal --cenario d` | 0 | OK |
| `python -m crosssignal --cenario e` | 0 | OK |
| `python -m crosssignal --arquivo data/exemplos/cruzamento.json` | 0 | OK |
| `python -m crosssignal --curta 3 --longa 5` | 0 | OK |
| `python -m crosssignal --arquivo data/exemplos/cruzamento.json --curta 1 --longa 2` | 0 | OK |
| `python -m crosssignal --help` | 0 | OK |
| `python -m crosssignal --curta 0 --longa 5` | 2 | OK |
| `python -m crosssignal --curta 5 --longa 3` | 2 | OK |
| `python -m crosssignal --curta 3 --longa 3` | 2 | OK |
| `python -m crosssignal --curta true` | 2 | OK |
| `python -m crosssignal --curta 1 --longa 2` | 2 | OK |
| `python -m crosssignal --arquivo data/exemplos/lacuna.json` | 2 | OK |
| `python -m crosssignal --arquivo /tmp/crosssignal-arquivo-inexistente.json` | 1 | OK |
| `python -m unittest discover -s tests -v` | 0 | OK |

A suíte concluiu **23 testes, todos aprovados**. Depois do ajuste de apresentação
da saída, foram reexecutados `python -m unittest discover -s tests -v` (23/23) e
`python -m crosssignal --cenario a` (código 0). A suíte também executa novamente
todos os cenários, cada cenário individual e os modos de arquivo.
`git diff --check` também foi executado e não apontou problemas.

## Conferência manual do cenário A

Execute `python -m crosssignal --cenario a` e compare as linhas de avaliação.
Os horários abaixo são UTC; primeiro candle abre às 12:00 e fecha às 12:01.

| Fechamento | Últimas somas curta/longa | SMA curta/longa | Resultado observado |
| --- | --- | --- | --- |
| 12:05 | 306 / 515 | 102 / 103 | Aquecimento; média longa anterior ausente |
| 12:06 | 313 / 520 | 313/3 / 104 | ENTRADA; intenção de compra, posição vazia |
| 12:07 | 301 / 506 | 301/3 / 101,2 | SAIDA; intenção de venda, após compra confirmada |

Às 12:06, a relação anterior é `102 <= 103` e a atual é `313/3 > 104`.
A confirmação fornecida a 110 USDT, 0,001 BTC, às 12:06:01 abre a posição.
Às 12:07, a relação anterior é `313/3 >= 104` e a atual é `301/3 < 101,2`.
A confirmação fornecida a 90 USDT, 0,001 BTC, às 12:07:01 encerra a posição.
A saída mostra `104.333333` e `100.333333`: somente apresentação arredondada.
Não são calculados resultados financeiros.

## Demais cenários e resultados observados

1. **B:** constantes e crescentes não geraram intenções. Igualdade anterior com
   último fechamento 101 gerou ENTRADA; com 99 gerou SAIDA, ignorada por posição
   vazia. Os testes também verificaram igualdade atual e permanência sem repetição.
2. **C:** sem confirmação da compra, posição permaneceu vazia. O sinal SAIDA foi
   registrado e bloqueado por `INTENCAO_PENDENTE`. Cancelamento e falha liberaram a
   intenção e preservaram posição. Testes isolaram entrada com posição aberta e
   saída sem posição, além de falha da venda preservando posição comprada.
3. **D:** candle aberto ignorado, versão fechada aceita, duplicata ignorada,
   conflito, par incompatível e evento fora de ordem rejeitados. A lacuna de um
   minuto bloqueou a sessão sem incorporar o candle posterior. Recuperação
   explícita criou nova sessão com três candles e nenhuma avaliação/intenção
   retroativa. O fluxo prosseguiu somente com os próximos eventos.
4. **E:** prefixo até o sexto candle foi idêntico com sufixo 90 ou 9000,
   mantendo a mesma confirmação de compra no prefixo. Processamento incremental
   coincidiu com o processamento sequencial completo.
5. **Arquivo:** `cruzamento.json` terminou com posição vazia e compra pendente;
   não houve confirmação automática. Com janelas 1/2 o arquivo também concluiu.
   `lacuna.json` informou a lacuna e retornou código 2. Arquivo inexistente retornou 1.

## Testes adicionais e preservação de estado

A suíte cobre JSON inválido, versão booleana, campos extras/ausentes, chaves
repetidas inclusive dentro de candles, NaN/Infinity, floats, strings decimais
inválidas, OHLC inconsistente, volume negativo, horário sem fuso, normalização
para UTC, intervalo incorreto e avaliação anterior ao fechamento.

Confirmações com ID vazio, referência divergente, lado/par/quantidade incompatíveis,
execução parcial, preço inválido e horário igual/anterior à intenção foram
rejeitadas sem alteração do estado. Repetição idêntica foi inócua; conteúdo
conflitante com o mesmo ID foi rejeitado, inclusive com outra intenção pendente.
Duplicata de candle após o cruzamento não repetiu intenção. Lacuna preservou a
pendência; recuperação com pendência ou posição foi bloqueada. Recuperação com
prefixo alterado, conjunto aberto, incompleto ou descontínuo foi rejeitada.

Um fechamento `100.000000000000000000000000000001` após cinco valores 100 gerou
ENTRADA, embora médias exibidas coincidam. O mesmo resultado foi obtido com
precisão decimal externa 2 e arredondamento ROUND_DOWN; configurações, flags e
traps externos foram preservados. O sinal usa razões exatas, conforme README.

## Limites e reprodução

Use os comandos da tabela para reproduzir; nenhum comando necessário ficou
pendente. Os resultados são determinísticos, sem rede, exchange ou ordens reais.
O laboratório usa memória e não recupera posições ou deduplicação após reinício.
A recuperação de lacunas é apenas didática, exige sessão vazia e é acessada pela
API Python e pelo cenário D. Não há avaliação de rentabilidade, saldo ou risco.
