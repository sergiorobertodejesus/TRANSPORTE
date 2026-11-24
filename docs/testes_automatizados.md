# Testes automatizados - ER Transporte

## 1. Objetivo

Garantir a estabilidade, a seguranca e a consistencia
do sistema durante sua evolucao e manutencao.

## 2. Execucao

Na raiz do projeto, executar:

    ER_AMBIENTE=teste venv/bin/python executar_testes.py

A execucao exige explicitamente o ambiente de teste.

## 3. Isolamento

Os testes utilizam bancos SQLite temporarios,
cadastros ficticios e diretorios temporarios.

A infraestrutura compartilhada permite testar
a aplicacao sem utilizar o banco de producao.

Os recursos temporarios sao removidos ao final
dos testes.

## 4. Organizacao

| Arquivo | Responsabilidade |
| --- | --- |
| ambiente_flask.py | Infraestrutura e isolamento |
| ambiente_jornadas.py | Preparacao de jornadas ficticias |
| test_inicializacao.py | Inicializacao da aplicacao |
| test_autenticacao.py | Login e contas de usuarios |
| test_permissoes.py | Sessoes, permissoes e CSRF |
| test_jornadas.py | Bloqueios e encerramento financeiro |
| test_excel.py | Exportacao e filtros |
| test_fotos.py | Checklist, fotografias e permissoes |
| test_banco.py | Estrutura e integridade do banco |
| test_backup.py | Backup, recuperacao e retencao |

## 5. Cobertura funcional

- Inicializacao e isolamento da aplicacao.
- Autenticacao administrativa e de motoristas.
- Bloqueio de contas desativadas.
- Controle de permissoes e sessoes.
- Protecao CSRF.
- Bloqueio de veiculos ocupados.
- Validacao de encerramentos invalidos.
- Registro de ganhos e despesas.
- Exportacao Excel e filtros.
- Inicio de jornada e checklist.
- Validacao e armazenamento de fotografias.
- Controle de acesso as fotografias.
- Integridade do banco de dados.
- Backup, recuperacao e retencao.

## 6. Procedimento de manutencao

Antes de publicar alteracoes:

1. Executar os testes automatizados.
2. Investigar e corrigir eventuais falhas.
3. Executar novamente todos os testes.
4. Atualizar a documentacao quando necessario.
5. Registrar as alteracoes no Git.

## 7. Validacao de referencia

Data: 24/11/2026

- Testes executados: 20
- Testes aprovados: 20
- Falhas: 0
- Tempo registrado: 8,575 segundos

## 8. Melhorias futuras

- Separar os testes de checklist e fotografias.
- Ampliar a cobertura conforme novas funcionalidades.
- Implantar integracao continua.
- Avaliar cobertura de codigo.
- Ampliar os testes de concorrencia.
