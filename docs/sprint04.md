# Sprint 04 — Estratégia simples com regras objetivas de entrada e saída

**Projeto fictício:** CrossSignal  
**Diretório sugerido:** `crosssignal`  
**Etapa de estudo:** 4 — Estratégia simples com regras objetivas de entrada e saída  
**Objetivo:** criar um laboratório de sinais por cruzamento de médias móveis simples, com decisões explicáveis e confirmação separada de execuções fictícias.

O CrossSignal é independente do SpotLab, PySpot, CandleVault e do robô principal. Utiliza somente dados locais fictícios. As janelas de 3 e 5 períodos foram escolhidas para facilitar a conferência manual, sem avaliação de rentabilidade ou recomendação de investimento.

## 1. Conhecimentos trabalhados

| Conhecimento | Aplicação no exemplo |
| --- | --- |
| Média móvel simples — SMA | Calcular médias de fechamentos em janelas móveis |
| Cruzamento | Comparar a relação entre médias no candle anterior e no atual |
| Aquecimento | Aguardar histórico suficiente para comparar duas janelas |
| Sinal, decisão e execução | Separar análise, intenção e confirmação de operação |
| Estado da posição | Controlar posição aberta e intenção pendente |
| Causalidade | Impedir que candles futuros alterem sinais passados |
| Qualidade dos dados | Tratar duplicatas, candles abertos, lacunas e ordem temporal |
| Testes determinísticos | Conferir regras com sequências pequenas e reproduzíveis |

## 2. Resultado esperado

Uma aplicação de terminal que processe candles sequencialmente e explique médias, sinais, decisões e estado da posição. Deve incluir fixtures, testes, glossário e roteiro de validação. Não será um motor de backtest nem uma integração com exchange.

## 3. Prompt autossuficiente de execução

Copie o bloco abaixo para o agente responsável pela implementação. Todas as regras necessárias estão neste prompt.

````text
Você é um desenvolvedor Python experiente. Implemente a Sprint 04 do projeto fictício CrossSignal: um laboratório de estratégia por cruzamento de médias móveis simples.

OBJETIVO E DIRETÓRIO

O usuário conhece desenvolvimento de software e está aprendendo os fundamentos de um robô de criptomoedas. Implemente o projeto e sua documentação; não entregue apenas um plano.

Use um diretório próprio chamado crosssignal no diretório de trabalho indicado pelo usuário ou, se não houver indicação, no diretório atual. Se já existir, inspecione e preserve trabalho alheio. Não altere projetos vizinhos. Não dependa de arquivos ou módulos de outras sprints.

TECNOLOGIA E ESCOPO

- Python 3.11 ou superior; somente biblioteca padrão, incluindo Decimal, dataclasses, Enum, datetime, json, argparse e unittest.
- Dados inteiramente fictícios, processados localmente, sem rede, credenciais, Binance ou ordens externas.
- Uma origem FICTICIA, par BTCUSDT e candles de 1m por sessão.
- SMA curta de 3 e longa de 5 períodos por padrão. Permita configurar inteiros com 1 <= curta < longa. Rejeite booleanos como períodos.
- Apenas posição comprada no Spot, sem margem, alavancagem ou venda descoberta; no máximo uma posição e uma intenção pendente.
- Não implemente otimização de parâmetros, seleção de moedas, indicadores adicionais, backtest, cálculo de rentabilidade, carteira financeira, taxas, stops, gestão de risco, persistência ou interface web.
- A quantidade fictícia de cada entrada será 0,001 BTC. Este valor é convenção do laboratório, não dimensionamento de risco.

ORGANIZAÇÃO

Separe validação dos dados, cálculo de indicadores, geração de sinal, decisão conforme estado e tratamento de confirmação de execução. Use funções puras para cálculos e um estado de sessão explícito, sem variáveis globais mutáveis. Prints e formatação pertencem à interface.

Represente candle, avaliação, sinal, intenção, confirmação e posição com modelos tipados simples. Use Enum e dataclass onde ajudarem. Não crie um framework de estratégias.

VALORES E HORÁRIOS

- Preços e quantidades em Decimal criado diretamente de strings, nunca via float.
- Rejeite preços/quantidades não positivos, NaN e infinitos. Tipagem não substitui validação em execução.
- Use contexto decimal local de precisão 28 e ROUND_HALF_EVEN, preservando o contexto externo.
- Não arredonde as médias antes de decidir cruzamentos. Exiba até seis casas no relatório e explique a diferença entre apresentação e cálculo.
- Como todas as médias são racionais de somas finitas, prefira comparar as médias usando multiplicação cruzada das somas e tamanhos das janelas, com precisão suficiente para os valores admitidos. Documente limites de entrada/precisão ou outra solução explícita que evite falsos cruzamentos por arredondamento.
- Datas com fuso obrigatório, normalizadas para UTC. Dados de demonstração com horários fixos.

CONTRATO DE CANDLES

Forneça fixtures JSON no formato {"schema_version": 1, "candles": [...]}.
Cada candle deve conter source, symbol, interval, open_time, close_time, open, high, low, close, volume e is_closed. Strings decimais usam ponto e não têm separadores de milhares. Horários são ISO 8601 com fuso. is_closed é booleano real.

close_time é o fim exclusivo de [open_time, close_time), exatamente um minuto após uma abertura alinhada ao minuto UTC. Essa é uma convenção do laboratório.

Valide OHLC positivo, volume não negativo e low <= open/close <= high. Rejeite JSON inválido, chaves duplicadas, NaN/Infinity, versão diferente de 1 e campos ausentes ou inesperados. Não aceite booleano como versão.

Para processar um candle fechado, receba também o instante de avaliação. Exija avaliação >= close_time. Nas fixtures, o instante de avaliação será o próprio close_time; nos testes, permita fornecê-lo explicitamente.

REGRAS DAS MÉDIAS E DOS SINAIS

SMA(n, t) = soma dos últimos n fechamentos válidos, incluindo t, dividida por n.

Use somente candles fechados, contíguos e da mesma origem/par/intervalo. Para comparar médias anteriores e atuais, exija longa + 1 candles. Com 3/5, o primeiro sinal possível surge no sexto candle; não invente médias anteriores.

- ENTRADA: curta_anterior <= longa_anterior E curta_atual > longa_atual.
- SAIDA: curta_anterior >= longa_anterior E curta_atual < longa_atual.
- NENHUM: histórico suficiente sem cruzamento.
- Durante aquecimento: sinal NENHUM com motivo HISTORICO_INSUFICIENTE; médias indisponíveis devem ser null/ausentes, nunca zero fictício.

Igualdade atual não gera cruzamento. Igualdade anterior seguida de separação estrita pode gerar cruzamento conforme as regras acima. Permanecer acima/abaixo não deve repetir sinal.

ESTADO, DECISÃO E CONFIRMAÇÃO

Separe o sinal produzido pelo indicador da decisão que depende da sessão:

- ENTRADA com posição vazia e sem intenção pendente: criar intenção de compra de 0,001 BTC.
- ENTRADA com posição aberta: ignorar a entrada, explicando POSICAO_JA_ABERTA.
- SAIDA com posição aberta e sem intenção pendente: criar intenção de venda da quantidade integral.
- SAIDA com posição vazia: ignorar a saída, explicando SEM_POSICAO.
- NENHUM: não criar intenção.
- Enquanto existir intenção pendente: não criar outra; continue registrando sinais e explique INTENCAO_PENDENTE quando um sinal for bloqueado.

Criar intenção não altera a posição. Somente confirmação explícita de execução total altera a posição. Use identificadores determinísticos e uma referência clara à intenção confirmada.

Uma confirmação válida deve ter ID de execução não vazio, ID de intenção correspondente, lado/par/quantidade compatíveis, preço positivo e instante estritamente posterior ao instante de criação da intenção. Não execute no mesmo fechamento que produziu o sinal.

Somente confirmações totais são suportadas; rejeite execução parcial sem mutar estado. Confirmação de compra abre posição; confirmação de venda encerra a posição. Falha/cancelamento explícito libera a intenção e preserva a posição; não gere tentativa automática posterior sem novo cruzamento.

Repetição da mesma confirmação não altera a posição novamente. Se o mesmo ID reaparecer com conteúdo divergente, rejeite como conflito. Rejeite confirmação sem intenção correspondente. Mantenha essa deduplicação apenas em memória durante a sessão e documente que não há recuperação após reinício.

Não simule saldo ou aprovação de risco: a decisão verifica somente as condições de posição e pendência descritas. Explique que esses controles adicionais serão necessários em outras etapas.

QUALIDADE E ORDEM DOS DADOS

- Candle aberto é ignorado e não entra no histórico. Uma versão fechada da mesma chave pode ser aceita posteriormente.
- Duplicata exata de candle fechado já aceito é ignorada, sem repetir avaliação ou intenção. Considere valores Decimal equivalentes mesmo com zeros finais diferentes.
- Mesma chave fechada com conteúdo divergente é conflito; não substitua silenciosamente.
- Novo candle fechado anterior ao último aceito é rejeitado como fora de ordem. Não ordene silenciosamente o fluxo de eventos para esconder esse problema.
- Um candle de outra origem/par/intervalo é rejeitado sem entrar nas médias.
- Ao receber um candle fechado posterior ao próximo minuto esperado, bloqueie novas avaliações: detecte e informe a lacuna sem incorporar o candle posterior ao histórico da estratégia.
- Não preencha intervalos com preços artificiais. Não cancele intenções nem feche posições automaticamente por causa da lacuna.
- A retomada é explícita: valide um conjunto local com o prefixo já aceito inalterado e os candles faltantes; reconstrua somente o histórico dos indicadores em uma nova sessão, sem gerar intenções retroativas. Essa recuperação didática só é permitida com posição vazia e sem intenção pendente. Se houver posição ou intenção, explique o bloqueio em vez de tentar reconstruir operações.
- Demonstre a recuperação numa sessão sem operações confirmadas. Dados de recuperação podem ser arquivo separado; não é necessário comando de recuperação para produção.

CAUSALIDADE

Processe candles um por vez. No instante t, use somente fechamentos até t. O fato de o arquivo conter o restante da sequência não autoriza usar preços futuros.

Confirmar operação é um evento posterior, explicitamente fornecido pelo cenário. O laboratório não deve escolher um preço futuro do arquivo automaticamente para preencher a intenção.

CENÁRIOS OBRIGATÓRIOS

A. Entrada e saída com conferência manual
   Fechamentos: 105, 104, 103, 102, 101, 110, 90.
   Primeiro candle: [2026-11-05T12:00:00+00:00, 12:01:00+00:00); demais consecutivos.
   Fixtures devem ter OHLCV consistente. Pode usar open=high=low=close em cada candle fictício e volume "1" para facilitar a leitura.
   Após o quinto: SMA curta=102 e longa=103; ainda falta a comparação anterior completa.
   Após o sexto: SMA curta=313/3 e longa=104; sinal ENTRADA às 12:06:00 UTC e uma intenção de compra, sem posição aberta imediatamente.
   Forneça confirmação fictícia de compra a 110 USDT às 12:06:01 UTC, quantidade 0,001 BTC. Somente então a posição fica aberta.
   Após o sétimo: SMA curta=301/3 e longa=101,2; sinal SAIDA às 12:07:00 UTC.
   Confirme venda fictícia a 90 USDT às 12:07:01 UTC, quantidade 0,001 BTC; posição final vazia.
   Não apresente essa sequência como estratégia lucrativa nem calcule métricas de retorno.

B. Ausência de cruzamento e igualdade
   Fechamentos constantes: 100, 100, 100, 100, 100, 100, 100; nenhum sinal.
   Fechamentos crescentes: 100, 101, 102, 103, 104, 105, 106; não criar entrada só porque curta está acima quando a comparação passa a existir.
   Teste igualdade anterior e cruzamento para cima com 100,100,100,100,100,101; para baixo com 100,100,100,100,100,99.

C. Posição e intenção pendente
   Mostre que uma intenção de entrada sem confirmação preserva posição vazia.
   Na sequência A, omita a confirmação de compra: o sinal de saída posterior não pode criar nova intenção enquanto a compra estiver pendente.
   Demonstre cancelamento/falha e ausência de alteração da posição.
   Teste também entrada com posição já aberta e saída sem posição. Para isolar essas regras, é permitido fornecer sinais construídos ao componente de decisão nos testes, sem falsificar os cálculos do indicador.

D. Dados abertos, duplicados e inválidos
   Demonstre candle aberto ignorado e sua versão fechada aceita, duplicata ignorada sem repetir intenção, divergência na mesma chave rejeitada, evento fora de ordem e par incompatível.
   Demonstre lacuna de um minuto, bloqueio e recuperação explícita em sessão vazia, sem geração retroativa de intenções.

E. Ausência de uso do futuro
   Processe um prefixo e guarde as avaliações até t.
   Reprocesse em sessão nova com o mesmo prefixo e um sufixo futuro muito diferente.
   As avaliações até t devem ser idênticas, incluindo médias, sinais e decisões quando os eventos de confirmação do prefixo forem os mesmos.
   Compare também processamento incremental com processamento sequencial do arquivo completo.

INTERFACE

Implemente:
- python -m crosssignal: executa todos os cenários didáticos em sessões isoladas.
- python -m crosssignal --cenario a: seleciona a, b, c, d ou e.
- python -m crosssignal --arquivo data/exemplos/cruzamento.json: processa candles sem confirmar operações automaticamente; relata intenções pendentes.
- python -m crosssignal --curta 3 --longa 5: configura janelas; demonstrações com resultados fixos podem exigir 3/5, mas devem explicar essa restrição. A opção de arquivo deve aceitar períodos válidos configuráveis.
- python -m crosssignal --help.
- python -m unittest discover -s tests -v.

O relatório deve distinguir horário do candle, disponibilidade do fechamento e instante de avaliação. Mostre médias anteriores/atuais, sinal, decisão, motivo, posição e intenção pendente. Registre confirmações em linhas separadas. Não use resultado financeiro ou taxa de acerto como evidência de funcionamento.

Use código de saída 0 para execução concluída, inclusive cenários com erros esperados demonstrados; 1 para falha inesperada ou de arquivo; 2 para dados/configuração inválidos ou bloqueio por lacuna no modo de arquivo. Rejeições devem aparecer com motivo e sem estado parcialmente alterado. Não esconda exceções inesperadas em mensagens de sucesso.

ENTREGÁVEIS

- pyproject.toml, pacote crosssignal, fixtures JSON, testes e .gitignore apropriado.
- README.md com comandos, estrutura, contrato de entrada, fórmulas, convenções de igualdade, fluxo de estados, aquecimento e simplificações.
- docs/sprint04-glossario.md com SMA, janela, cruzamento, aquecimento, sinal, intenção, confirmação, posição, causalidade e look-ahead bias.
- docs/sprint04-validacao.md com passos, cálculos manuais, resultados esperados, comandos efetivamente executados e resultados observados.

TESTES E ACEITE

Verifique cálculos e sinais de A/B, limites de histórico, períodos configuráveis, igualdade, estados de C, confirmações inválidas/duplicadas, preservação de estado nas rejeições, regras de D, bloqueio/recuperação e causalidade de E.

Inclua preços separados por diferenças menores que a precisão exibida no terminal: decisões devem usar valores internos, nunca strings arredondadas. Teste que mudar a precisão decimal externa não muda os resultados admitidos pelo contrato e que o contexto externo é preservado.

Execute todos os cenários, cada cenário individual, modo de arquivo, --help, configurações válidas/inválidas e unittest. Corrija falhas. Não apresente comandos não executados como verificados.

Ao concluir, informe arquivos criados, comandos executados, resultados e limitações. Se algo não puder ser executado, registre causa e comando pendente. Não faça commits, publicação ou operações externas sem solicitação.
````

## 4. Conclusão da etapa

A etapa estará concluída quando cada sinal puder ser explicado pelos candles disponíveis naquele instante, sem compras repetidas por permanência acima da média e sem alterar posição antes de confirmação explícita.

A próxima etapa será gestão de risco: tamanho da posição, exposição e condições de interrupção.
