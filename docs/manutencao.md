# Manutenção operacional — ER Transporte

## 1. Objetivo

Registrar as verificações necessárias para manter
o sistema ER Transporte estável e recuperável.

## 2. Verificações periódicas

- Confirmar disponibilidade do site.
- Verificar erros registrados pelos serviços.
- Conferir a execução dos backups.
- Verificar espaço disponível no servidor.
- Conferir a limpeza programada de fotografias.

## 3. Backup do banco

Script: `backup_banco.py`.

- Utiliza o mecanismo de backup do SQLite.
- Verifica integridade com `PRAGMA integrity_check`.
- Retenção padrão: 14 dias.
- A execução automática depende do timer systemd.

Procedimentos detalhados:
`docs/backup_recuperacao.md`.

## 4. Fotografias

Script: `limpar_fotos.py`.

- Retenção configurada: 14 dias.
- Possui mecanismo de quarentena e recuperação.
- Preserva os dados estruturados das jornadas.

Consultar o código antes de executar
manualmente qualquer operação de limpeza.

## 5. Atualizações

Antes de modificar a produção:

1. Confirmar backup recuperável.
2. Testar no ambiente de teste.
3. Revisar alterações no banco.
4. Planejar a reversão.
5. Registrar mudanças no GitHub.

## 6. Segurança

Consultar `docs/seguranca.md`.

Não armazenar credenciais no repositório.

## 7. Pendências operacionais

- Confirmar timers na AWS.
- Verificar backups recentes.
- Implementar backup externo.
- Documentar logs e serviços reais.
- Criar testes automatizados.
- Testar recuperação periodicamente.
