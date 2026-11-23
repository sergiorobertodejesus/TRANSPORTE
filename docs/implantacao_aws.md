# Implantação AWS — ER Transporte

## 1. Infraestrutura

O sistema utiliza AWS EC2 com Ubuntu, Nginx,
Gunicorn, Flask e SQLite.

## 2. Diretórios

- Projeto: `/home/ubuntu/projetos/transporte`
- Banco: `/home/ubuntu/projetos/transporte/transporte.db`
- Backups: `/home/ubuntu/backups/er-transporte`
- Fotografias: `instance/fotos_jornadas/`

## 3. Serviços automáticos

Backup SQLite:
- Serviço: `er-backup-banco.service`
- Timer: `er-backup-banco.timer`
- Horário documentado: 02h30 (Brasília)

Limpeza de fotografias:
- Timer: `er-limpeza-fotos.timer`
- Horário documentado: 03h00 (Brasília)

## 4. Atualizações em produção

O código é versionado no GitHub.

Antes de atualizar:
1. Confirmar um backup recuperável.
2. Testar as alterações no ambiente de teste.
3. Verificar eventuais mudanças no banco.
4. Planejar a atualização e sua reversão.

O procedimento exato de publicação ainda precisa
ser confirmado diretamente na EC2.

## 5. Segurança

Consultar `docs/seguranca.md`.

Não armazenar senhas, chaves ou credenciais
na documentação.

## 6. Backup e recuperação

Consultar `docs/backup_recuperacao.md`.

Os backups locais possuem retenção documentada
de 14 dias. A cópia externa ainda está pendente.

## 7. Verificações pendentes na AWS

- Nome e configuração do serviço Gunicorn.
- Configuração do Nginx e HTTPS.
- Variáveis de ambiente do serviço.
- Permissões dos arquivos.
- Funcionamento atual dos timers.
- Integridade dos backups recentes.
- Procedimento de atualização e reversão.
- Implementação de backup externo.
