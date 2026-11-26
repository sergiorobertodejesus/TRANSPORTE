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

## 11. Arquitetura implantada

A geracao diaria ocorre na instancia AWS EC2,
independentemente da aplicacao Flask.

- Horario: 07h, America/Sao_Paulo.
- Servico: er-relatorios.service.
- Timer: er-relatorios.timer.
- Usuario de execucao: ubuntu.
- Tipo de servico: oneshot.
- Limite de execucao: 120 segundos.
- Diretorio de trabalho: /home/ubuntu/projetos/transporte.
- Diretorio de saida: /home/ubuntu/relatorios_diarios.
- Permissoes restritas nos documentos gerados.

O timer utiliza Persistent=true.

Uma execucao perdida pode ser recuperada
quando o timer voltar a funcionar.

Isso nao representa recuperacao automatica
de todos os periodos anteriores.

## 12. Estado da implantacao

- Desenvolvimento concluido.
- Suite de 56 testes automatizados aprovada.
- Dependencias instaladas na AWS.
- Geracao manual em producao validada.
- Timer diario habilitado e ativo.
- Primeira execucao agendada: 26/11/2026.
- Data de referencia: 25/11/2026.
- Jornadas processadas: 8.
- Tres documentos gerados.
- Duracao do servico: aproximadamente 1,4 segundo.
- Timer confirmado ativo apos reinicializacao.

## 13. Acompanhamento operacional

Consultar agendamento:

    systemctl list-timers er-relatorios.timer --all

Consultar registros:

    journalctl -u er-relatorios.service -n 50 --no-pager

Consultar resultado da ultima execucao:

    systemctl show er-relatorios.service         -p Result -p ExecMainStatus

O servico oneshot normalmente permanece inativo
apos concluir sua execucao com sucesso.

Os documentos podem ser consultados no diretorio
de saida, organizado pela data de referencia.

A transferencia dos documentos deve ocorrer
por canal autenticado e seguro.

## 14. Pendencias futuras

- Definir politica de retencao dos relatorios.
- Formalizar procedimento de reemissao.
- Avaliar arquivamento externo das fotografias.
- Avaliar integracoes oficiais para distribuicao.

Essas atividades nao impedem a operacao
da geracao diaria atualmente implantada.
