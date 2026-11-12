# ER Transporte — Backup e recuperação do banco de dados

## 1. Objetivo

Documentar a rotina de backup do banco SQLite da ER Transporte na AWS EC2, as verificações de integridade, o teste de recuperação e os cuidados necessários para uma eventual restauração em produção.

> **Atenção:** uma restauração real substitui dados e exige uma janela de manutenção. Não execute o procedimento de substituição sem antes confirmar o backup escolhido e interromper as gravações da aplicação.

## 2. Ambiente e caminhos

| Item | Configuração |
| --- | --- |
| Aplicação | Flask, executada pelo serviço `er-transporte` |
| Projeto | `/home/ubuntu/projetos/transporte` |
| Banco de produção | `/home/ubuntu/projetos/transporte/transporte.db` |
| Script de backup | `/home/ubuntu/projetos/transporte/backup_banco.py` |
| Diretório de backups | `/home/ubuntu/backups/er-transporte` |
| Serviço systemd | `er-backup-banco.service` |
| Agendamento systemd | `er-backup-banco.timer` |
| Horário | Todos os dias às 02h30, `America/Sao_Paulo` |
| Retenção | 14 dias para backups automáticos gerados pelo script |

O timer da limpeza de fotografias (`er-limpeza-fotos.timer`) está programado separadamente para as 03h00, horário de Brasília.

## 3. Como o backup funciona

O script `backup_banco.py` usa a API de backup do SQLite para produzir uma cópia consistente, sem necessidade de interromper a aplicação. Ele exige a definição explícita de `ER_AMBIENTE=producao` ou `ER_AMBIENTE=teste`, verifica a integridade da cópia com `PRAGMA integrity_check` e salva arquivos com nomes no padrão `er_auto_producao_*.db` ou `er_auto_teste_*.db`.

A retenção de 14 dias é aplicada aos backups automáticos do ambiente correspondente, no diretório informado. Backups manuais com outros nomes não fazem parte dessa limpeza automática.

O backup cobre **o banco SQLite**, não os arquivos de fotografias armazenados separadamente pela aplicação.

## 4. Verificar o agendamento e a última execução

No servidor EC2:

```bash
systemctl status er-backup-banco.timer --no-pager
systemctl list-timers --all --no-pager | grep -E 'er-backup|er-limpeza'
systemctl show er-backup-banco.service -p Result -p ExecMainStatus -p ActiveState
sudo journalctl -u er-backup-banco.service -n 30 --no-pager
```

Um serviço `oneshot` pode aparecer como `inactive` após terminar. Para uma execução bem-sucedida, procure `Result=success`, `ExecMainStatus=0` e `BACKUP OK` no registro da execução correspondente.

Listar os backups automáticos:

```bash
find /home/ubuntu/backups/er-transporte \
  -maxdepth 1 -type f -name 'er_auto_producao_*.db' \
  -printf '%TY-%Tm-%Td %TH:%TM %s bytes %f\n' | sort
```

**Importante:** timer ativo não significa, por si só, que o backup mais recente funcionou. Confira também os logs e a existência de arquivos recentes.

## 5. Executar um backup manual sem parar a aplicação

```bash
cd /home/ubuntu/projetos/transporte
ER_AMBIENTE=producao venv/bin/python backup_banco.py \
  --destino /home/ubuntu/backups/er-transporte
```

Resultado esperado: mensagem `BACKUP OK`, caminho do arquivo criado e `integridade: ok`. O comando cria uma **nova cópia**, sem substituir o banco original.

## 6. Testar a recuperação sem alterar a produção

O teste abaixo abre o backup automático mais recente, copia seu conteúdo para um banco temporário, verifica a integridade e consulta a quantidade de tabelas e jornadas. **Não substitui `transporte.db` e não interrompe a aplicação.**

```bash
cd /home/ubuntu/projetos/transporte
venv/bin/python - <<'PY'
import sqlite3
import tempfile
from pathlib import Path

pasta = Path('/home/ubuntu/backups/er-transporte')
backups = sorted(pasta.glob('er_auto_producao_*.db'))
if not backups:
    raise SystemExit('Nenhum backup automático de produção encontrado')

origem = backups[-1]
with tempfile.TemporaryDirectory(prefix='er_restauracao_') as tmp:
    destino = Path(tmp) / 'restaurado.db'
    with sqlite3.connect(origem.as_uri() + '?mode=ro', uri=True) as fonte:
        with sqlite3.connect(destino) as copia:
            fonte.backup(copia)
    with sqlite3.connect(destino) as banco:
        integridade = banco.execute('PRAGMA integrity_check').fetchone()[0]
        tabelas = banco.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        jornadas = banco.execute('SELECT COUNT(*) FROM jornadas').fetchone()[0]
    print('BACKUP:', origem.name)
    print('INTEGRIDADE:', integridade)
    print('TABELAS:', tabelas)
    print('JORNADAS:', jornadas)
    if integridade != 'ok':
        raise SystemExit('FALHA NA INTEGRIDADE')
    print('TESTE DE RECUPERAÇÃO: APROVADO')
PY
```

A pasta temporária é eliminada ao final. Quantidades de tabelas e jornadas variam conforme a evolução do sistema.

## 7. Procedimento para uma restauração real (somente manutenção planejada)

**Não executar automaticamente.** Em caso de incidente, seguir esta sequência com acompanhamento técnico:

1. Identificar o incidente e escolher a cópia correta, verificando sua data, integridade e os dados que ela contém. Uma cópia antiga pode causar perda de registros posteriores.
2. Avisar os responsáveis e programar uma janela sem uso do sistema. Interromper a aplicação e qualquer processo que possa gravar no banco, incluindo tarefas agendadas relevantes.
3. Preservar uma cópia de segurança do estado atual do banco e dos arquivos auxiliares SQLite (`-wal` e `-shm`, se existirem). Não copiar ou substituir arquivos de um banco ativo de maneira isolada.
4. Restaurar o backup validado para um **arquivo novo**, fora do caminho de produção. Verificar `PRAGMA integrity_check`, tabelas e registros essenciais.
5. Confirmar permissões, proprietário, caminho de destino e compatibilidade com a versão do aplicativo antes de efetuar a substituição controlada.
6. Com todos os processos de escrita interrompidos, realizar a substituição planejada e iniciar novamente a aplicação.
7. Validar login administrativo, consultas de jornadas e demais funções críticas. Monitorar logs e manter a cópia anterior disponível para reversão.

Os comandos específicos da substituição devem ser preparados conforme o estado do servidor no momento do incidente. **Não substituir `transporte.db` enquanto a aplicação estiver em execução.**

## 8. Testes realizados em 12/11/2026

- Backup local no ambiente `teste`: 98.304 bytes, `integridade: ok`.
- Execução sem `ER_AMBIENTE`: corretamente recusada.
- Script publicado no GitHub no commit `d3f7d51`.
- Backup manual na EC2: 114.688 bytes, `integridade: ok`.
- Execução via systemd: `Result=success`, `ExecMainStatus=0`, novo backup de 114.688 bytes.
- Teste de recuperação para banco temporário: `integridade: ok`, **11 tabelas e 33 jornadas**.
- Banco original de produção não foi alterado durante o teste.

Esses resultados comprovam a geração e a leitura de cópias naquela data; não substituem o acompanhamento das execuções futuras.

## 9. Limitações e próximos cuidados

- **Mesmo servidor:** os backups estão armazenados na mesma instância EC2. Uma falha ou perda do disco pode afetar simultaneamente o banco e suas cópias.
- **Cópia externa:** planejar armazenamento fora da instância, por exemplo S3, avaliando custos, permissões, criptografia, retenção e testes de recuperação antes de ativar.
- **Fotografias:** as imagens das jornadas ficam fora do SQLite e não estão incluídas no backup do banco. Exigem política de proteção própria, compatível com sua retenção operacional.
- **Retenção:** 14 dias é a janela configurada para arquivos automáticos locais; não é garantia de recuperação de alterações anteriores a essa janela.
- **Monitoramento:** conferir regularmente o último backup bem-sucedido e, periodicamente, repetir um teste de recuperação.

## 10. Atualização desta documentação

Atualizar este documento sempre que mudarem os caminhos, nomes de serviços, agendamentos, política de retenção, mecanismo de armazenamento ou procedimento de recuperação.
