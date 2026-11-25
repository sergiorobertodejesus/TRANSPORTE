# ER Transporte - Relatorios automatizados

## 1. Objetivo

Automatizar a consolidacao diaria dos resultados
financeiros e da produtividade da frota.

## 2. Periodo operacional

- Fuso: America/Sao_Paulo.
- Inicio: 07h da data de referencia, inclusive.
- Encerramento: 07h do dia seguinte, exclusive.
- Selecao pela data de encerramento da jornada.
- Jornadas abertas entram no periodo em que encerrarem.

## 3. Modulos

- periodo_operacional.py: limites temporais.
- consulta_jornadas.py: consulta compartilhada.
- relatorio_financeiro.py: consolidacao financeira.
- relatorio_produtividade.py: indicadores operacionais.
- excel_financeiro.py: planilha financeira.
- excel_produtividade.py: planilha de produtividade.
- pdf_executivo.py: documento executivo.
- gerar_relatorio_diario.py: orquestracao da geracao.

## 4. Criterios financeiros

Bruto = Uber + 99 + corridas particulares.

Liquido operacional = bruto - despesas registradas.

O liquido operacional nao representa o lucro final.
Custos nao registrados, depreciacao, seguros,
remuneracoes e energia interna podem estar ausentes.

## 5. Indicadores de produtividade

- Quilometros rodados.
- Horas de jornada.
- Faturamento por quilometro.
- Faturamento por hora.

As horas incluem pausas e recargas.
Dados invalidos sao sinalizados.
Divisoes sem denominador valido ficam indisponiveis.

## 6. Documentos gerados

Cada data de referencia possui uma pasta propria:

- 01_Relatorio_Financeiro.xlsx
- 02_Relatorio_Produtividade.xlsx
- 04_Relatorio_Executivo.pdf

As planilhas destinam-se ao back office.
O PDF destina-se ao acompanhamento executivo.

## 7. Execucao manual

    venv/bin/python gerar_relatorio_diario.py \
        --banco /caminho/transporte.db \
        --destino /caminho/relatorios \
        --data AAAA-MM-DD

Sem --data, utiliza o ultimo periodo operacional
completamente encerrado.

## 8. Seguranca e consistencia

- Banco aberto exclusivamente para leitura.
- Transacao compartilhada entre as consultas.
- Validacao da integridade do banco.
- Conferencia dos totais consolidados.
- Geracao em diretorio temporario.
- Publicacao somente apos geracao completa.
- Bloqueio de sobrescrita.
- Permissoes restritas nos arquivos.
- Nenhuma dependencia da aplicacao Flask em execucao.

## 9. Falhas e recuperacao

Em caso de falha, consultar os registros da execucao.
Corrigir a causa e executar novamente.

Relatorios existentes nao sao sobrescritos.

Correcoes posteriores ao fechamento exigem
procedimento controlado de reemissao.

Horarios de encerramento inconsistentes no historico
interrompem a geracao e exigem verificacao.

## 10. Testes automatizados

    ER_AMBIENTE=teste venv/bin/python executar_testes.py

Os testes utilizam bancos temporarios.

A verificacao de conteudo e paginacao do PDF utiliza
pdfinfo e pdftotext, quando disponiveis.

## 11. Arquitetura planejada

AWS:
- Geracao diaria as 07h, horario de Brasilia.
- Agendamento por systemd timer.
- Armazenamento protegido dos documentos.

Estacao local Lubuntu:
- Transferencia segura dos documentos.
- Prototipo de automacao com Selenium.
- Registro de envios e falhas.
- Contingencia de envio manual.

A automacao de entrega sera independente do
sistema de producao.

O envio nao oficial pelo WhatsApp Web apresenta
riscos de incompatibilidade e restricao da conta.

## 12. Estado da implantacao

Geracao local implementada e testada.

Pendencias:
- Implantacao na AWS.
- Agendamento diario.
- Politica de retencao dos relatorios.
- Transferencia automatica.
- Automacao de entrega.
- Arquivamento das fotografias.
