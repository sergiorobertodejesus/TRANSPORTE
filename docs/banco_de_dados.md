# Banco de dados — ER Transporte

## 1. Visão geral

O sistema utiliza **SQLite**, com a conexão e a inicialização definidas em `database.py`. Há dois arquivos de banco conforme `ER_AMBIENTE`:

| Ambiente | Arquivo |
| --- | --- |
| `teste` | `transporte_teste.db` |
| `producao` | `transporte.db` |

**Importante:** sem `ER_AMBIENTE`, a aplicação seleciona `producao`. Não executar testes de escrita sem definir explicitamente o ambiente.

A função `conectar()` habilita chaves estrangeiras (`PRAGMA foreign_keys = ON`), usa linhas do tipo `sqlite3.Row` e configura `busy_timeout` de 10 segundos.

## 2. Tabelas

| Tabela | Finalidade | Relacionamentos principais |
| --- | --- | --- |
| `administradores` | Credenciais e estado dos administradores | Referenciada por `auditoria_jornadas` |
| `motoristas` | Cadastro e estado dos motoristas | Referenciada por `acessos`, `escalas` e `jornadas` |
| `veiculos` | Cadastro, placa e estado dos veículos | Referenciada por `escalas` e `jornadas` |
| `acessos` | Usuário, hash de senha e situação do acesso do motorista | `motorista_id` → `motoristas.id`, único |
| `escalas` | Associação de motorista, veículo, horários e situação da escala | `motorista_id` → `motoristas.id`; `veiculo_id` → `veiculos.id` |
| `jornadas` | Início, encerramento, quilometragem, bateria, estado e fotografias | `motorista_id` → `motoristas.id`; `veiculo_id` → `veiculos.id` |
| `checklists` | Inspeção do veículo e registro de avarias | `jornada_id` → `jornadas.id`, único |
| `ganhos` | Valores Uber, 99, particulares, dinheiro e PIX | `jornada_id` → `jornadas.id`, único |
| `despesas` | Categoria, valor e descrição de despesas | `jornada_id` → `jornadas.id` |
| `auditoria_jornadas` | Histórico de correções administrativas | `jornada_id` → `jornadas.id`; `administrador_id` → `administradores.id` |

## 3. Relacionamentos funcionais

- Um motorista pode possuir um registro de acesso e diversas jornadas ao longo do tempo.
- Uma escala associa um motorista a um veículo e a um intervalo de horário. O índice parcial existente permite **somente uma escala ativa por motorista**.
- Uma jornada pertence a um motorista e a um veículo.
- Cada jornada admite no máximo um checklist e um registro na tabela `ganhos`, conforme as restrições `UNIQUE`.
- Uma jornada pode ter várias linhas de despesas.
- Uma jornada pode ter várias entradas de auditoria, cada uma vinculada a um administrador.

Essas relações descrevem o esquema e não substituem as regras adicionais implementadas nas rotas Flask.

## 4. Campos relevantes

### `jornadas`

Campos-base: `id`, `motorista_id`, `veiculo_id`, `data_inicio`, `km_inicial`, `bateria_inicial`, `data_fim`, `km_final`, `bateria_final`, `status`.

Campos adicionais introduzidos por migrações: `foto_km_inicial`, `foto_km_final`, `avaria_final`, `descricao_avaria_final`, `foto_avaria_final`.

### `checklists`

Inclui verificações de retrovisores, farol alto, setas, luz de freio, brake light, pneus, bancos, painel, riscos nas portas, outras avarias, descrição e `foto_avaria`.

### `ganhos`

Campos-base: `uber_total`, `uber_dinheiro`, `noventa_nove_total`, `noventa_nove_dinheiro`, `corridas_particulares`, `dinheiro_total`.

Migrações identificadas: `particulares_dinheiro`, `uber_pix`, `noventa_nove_pix`, `particulares_pix`, `pix_empresa`.

### `auditoria_jornadas`

Registra `jornada_id`, `administrador_id`, `data_alteracao`, `motivo`, `dados_anteriores` e `dados_novos`.

## 5. Índices identificados

| Índice | Finalidade |
| --- | --- |
| `idx_escalas_motorista_ativo` | Índice único parcial sobre `motorista_id` para escalas com `ativo = 1` |
| `idx_jornadas_motorista_id` | Consultas de jornadas por motorista |
| `idx_despesas_jornada_id` | Consultas e agrupamentos de despesas por jornada |

Outros índices implícitos podem ser criados pelo SQLite para chaves primárias e restrições `UNIQUE`.

## 6. Inicialização e migrações

A função `inicializar_banco()`:

1. Cria as tabelas, caso ainda não existam.
2. Verifica a existência de campos adicionais em `jornadas`, `ganhos` e `checklists` e os acrescenta quando necessário.
3. Migra a estrutura antiga de `escalas` quando detecta uma restrição `UNIQUE` incompatível com o histórico de escalas.
4. Cria os índices listados acima.
5. Tenta cadastrar, com `INSERT OR IGNORE`, os veículos iniciais `GS`, `Song`, `Mini preto`, `Mini branco` e `Polo`, e os dez motoristas iniciais definidos no código.

**Ponto de manutenção:** a inicialização contém dados de cadastro iniciais. Mudanças futuras devem avaliar a separação entre migração de esquema e dados de exemplo/cadastro, evitando efeitos indesejados em novos ambientes.

## 7. Fotografias e retenção

O banco armazena nomes/referências dos arquivos de fotografia; os arquivos ficam em `instance/fotos_jornadas/`. A limpeza programada atua sobre fotografias de jornadas encerradas há pelo menos 14 dias, preservando os registros de jornadas, checklists, ganhos e despesas.

## 8. Cuidados operacionais

- Não versionar arquivos `.db` nem credenciais.
- Fazer backup consistente antes de migrações ou manutenção com escrita.
- Validar alterações primeiro em `ER_AMBIENTE=teste`.
- Não copiar o arquivo SQLite de produção durante gravações sem um procedimento de backup consistente.
- Testar a restauração periodicamente; a existência de uma cópia não garante recuperação.

## 9. Pendências de documentação

Documentar separadamente o procedimento de backup/restauração na AWS, a política de retenção de backups, as verificações de integridade e as permissões de acesso às informações. Esta versão descreve o esquema observado no código, não uma auditoria completa do banco em produção.
