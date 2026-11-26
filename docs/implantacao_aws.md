# Implantação AWS — ER Transporte

## 1. Infraestrutura

O sistema utiliza AWS EC2 com Ubuntu, Nginx,
Gunicorn, Flask e SQLite.

A instância está na região us-east-2 (Ohio)
e também hospeda o sistema MC Advocacia.

Configuração verificada em 26/11/2026:

- Ubuntu 26.04.1 LTS.
- Kernel 7.0.0-1018-aws.
- Volume EBS gp3 de 8 GiB.
- Memória disponível ao sistema: 908 MiB no total.
- HTTPS ativo.

## 2. Diretórios

- Projeto: `/home/ubuntu/projetos/transporte`
- Banco: `/home/ubuntu/projetos/transporte/transporte.db`
- Backups: `/home/ubuntu/backups/er-transporte`
- Fotografias: `instance/fotos_jornadas/`
- Relatórios: `/home/ubuntu/relatorios_diarios`

## 3. Serviços

- `er-transporte.service`: aplicação ER Transporte.
- `mc-advocacia.service`: aplicação MC Advocacia.
- `nginx.service`: proxy reverso e HTTPS.
- `ssh.service`: administração remota.

## 4. Agendamentos automáticos

Horários de Brasília:

| Atividade | Timer | Horário |
| --- | --- | --- |
| Backup SQLite e S3 | er-backup-banco.timer | 02h30 |
| Limpeza de fotografias | er-limpeza-fotos.timer | 03h00 |
| Geração de relatórios | er-relatorios.timer | 07h00 |
| Renovação HTTPS | certbot.timer | Conforme timer |

Os quatro timers foram confirmados ativos após
a reinicialização de 26/11/2026.

## 5. Atualizações em produção

O código é versionado no GitHub.

Antes de atualizar:

1. Confirmar backups recuperáveis.
2. Executar os testes automatizados localmente.
3. Revisar alterações e dependências.
4. Planejar atualização e reversão.
5. Definir janela de manutenção quando necessário.

No servidor, verificar o estado do repositório:

    cd /home/ubuntu/projetos/transporte
    git status --short
    git log -1 --oneline

Com o repositório limpo e a publicação autorizada:

    git pull --ff-only origin main

Quando houver alterações de dependências,
revisar o requirements.txt antes da instalação.

Quando houver alterações na aplicação,
avaliar a necessidade de reiniciar:

    sudo systemctl restart er-transporte.service

Alterações exclusivamente documentais não exigem
reinicialização da aplicação.

Após a publicação:

    systemctl status er-transporte --no-pager
    sudo nginx -t

Confirmar também o funcionamento pelo navegador.

## 6. Segurança

Consultar `docs/seguranca.md`.

Não armazenar senhas, chaves ou credenciais
na documentação.

O acesso administrativo utiliza SSH.
O backup externo utiliza uma função IAM
associada à instância EC2.

## 7. Backup e recuperação

Consultar `docs/backup_recuperacao.md`.

- Backups locais: retenção de 14 dias.
- Backups externos S3: retenção de 30 dias.
- Fotografias locais: retenção de 14 dias.

A geração e o envio dos backups externos
foram implementados e validados.

## 8. Relatórios automatizados

A geração diária está implantada na AWS.

Consultar `docs/relatorios_automatizados.md`.

## 9. Manutenção da infraestrutura

Consultar `docs/manutencao.md`.

Como a instância hospeda dois sistemas,
atualizações do sistema operacional e reinicializações
devem considerar a disponibilidade de ambos.

## 10. Verificações futuras

- Revisar periodicamente permissões e configurações.
- Testar procedimentos de recuperação e reversão.
- Acompanhar capacidade do armazenamento.
- Avaliar criptografia do volume EBS.
