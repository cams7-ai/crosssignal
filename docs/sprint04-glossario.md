# Sprint 04 — Glossário

| Termo | Significado no CrossSignal |
| --- | --- |
| SMA | Média móvel simples: soma dos fechamentos de uma janela dividida pelo seu tamanho. |
| Janela | Quantidade dos últimos candles válidos usada no cálculo. Padrões: 3 e 5. |
| Cruzamento | Mudança da relação entre médias anteriores e atuais, com separação estrita atual. |
| Aquecimento | Histórico ainda insuficiente para comparar as duas médias em dois instantes. Com 3/5, exige seis candles para terminar. |
| Sinal | Resultado do indicador: ENTRADA, SAIDA ou NENHUM. Independe da posição. |
| Intenção | Pedido fictício pendente criado pela decisão; ainda não altera a posição. |
| Confirmação | Evento explícito posterior que informa execução total e altera a posição. |
| Posição | Quantidade comprada confirmada ainda não vendida integralmente. |
| Causalidade | Cada avaliação depende somente dos dados disponíveis até seu instante. |
| Look-ahead bias | Uso indevido de informações futuras numa decisão passada. O laboratório verifica invariância do prefixo para evitá-lo. |
| Disponibilidade | Momento em que o fechamento está disponível, igual a close_time por convenção local. |
| Avaliação | Instante fornecido ao processamento; para candle fechado, não pode anteceder sua disponibilidade. |
| Lacuna | Ausência de um ou mais candles entre o último aceito e um evento posterior. Bloqueia novas avaliações até recuperação explícita. |
| Deduplicação | Ignorar repetição idêntica sem repetir efeitos, preservando a detecção de conflitos. |

Exemplo: às 12:06 UTC do cenário A surge ENTRADA. A decisão cria intenção, mas a
posição continua vazia. Somente a confirmação às 12:06:01 UTC abre a posição.
