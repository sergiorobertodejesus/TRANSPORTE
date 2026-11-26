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

## 7. Rotina operacional

### Diariamente

- Confirmar disponibilidade do sistema.
- Conferir a execução do backup local e externo.
- Conferir a geração dos relatórios.
- Investigar falhas nos serviços automáticos.

### Semanalmente

- Verificar espaço em disco e memória disponível.
- Revisar os registros de erros dos serviços.
- Conferir a retenção de backups e fotografias.
- Verificar atualizações de segurança disponíveis.

### Periodicamente

- Testar a recuperação dos backups em ambiente isolado.
- Revisar permissões e configurações de segurança.
- Planejar atualizações do sistema operacional.
- Atualizar a documentação técnica.

## 8. Comandos de diagnóstico

    systemctl --failed --no-pager
    systemctl status er-transporte --no-pager
    systemctl list-timers --all --no-pager
    journalctl -u er-transporte -n 50 --no-pager
    journalctl -u er-backup-banco.service -n 30 --no-pager
    journalctl -u er-limpeza-fotos.service -n 30 --no-pager
    journalctl -u er-relatorios.service -n 30 --no-pager
    df -h
    free -h

## 9. Registro de manutenção — 26/11/2026

Manutenção preventiva da instância EC2 compartilhada
pelos sistemas ER Transporte e MC Advocacia.

### Medidas preventivas

- Backup atualizado do banco ER Transporte.
- Envio do backup ER ao Amazon S3 confirmado.
- Backup consistente do banco MC Advocacia.
- Cópias externas dos dois bancos na estação local.
- Integridade das cópias confirmada.
- Snapshot preventivo do volume EBS concluído.

O snapshot foi criado com a instância em funcionamento.
Os backups SQLite foram realizados separadamente.

### Atualizações realizadas

- Atualização de 71 pacotes do Ubuntu.
- Nenhum pacote removido.
- Ubuntu 26.04.1 LTS após reinicialização.
- Kernel anterior: 7.0.0-1008-aws.
- Kernel atual: 7.0.0-1018-aws.
- Reinicialização controlada concluída.

### Validação posterior

- Nenhuma unidade systemd com falha.
- Nenhuma reinicialização pendente.
- Nginx e serviços das aplicações ativos.
- Conexão SSH operacional.
- Ambos os sites respondendo HTTP 200.
- Integridade dos dois bancos SQLite confirmada.
- Quatro timers operacionais ativos.
- Testes funcionais pelo navegador aprovados.

### Recursos após a manutenção

- Memória total: 908 MiB.
- Memória disponível: 479 MiB.
- Armazenamento raiz: 6,7 GB.
- Espaço disponível: aproximadamente 2 GB.
- Ocupação do armazenamento: 70%.

Valores registrados no momento da verificação.

Não houve ampliação do volume EBS, alteração
das regras de negócio ou limpeza extraordinária
de fotografias.

## 10. Pendências para acompanhamento

- Realizar testes periódicos de recuperação.
- Avaliar criptografia do volume EBS.
- Avaliar as duas atualizações disponíveis pelo ESM Apps.
- Acompanhar crescimento do armazenamento.
- Avaliar retenção dos relatórios gerados.
- Revisar o snapshot preventivo em 03/12/2026.

Excluir o snapshot somente após confirmar
a estabilidade e a disponibilidade dos backups.

A restauração do snapshot ainda não foi testada.
