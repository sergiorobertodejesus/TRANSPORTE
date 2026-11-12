# ER Transporte

Sistema web de gestão operacional da ER Transporte, desenvolvido com Python, Flask e SQLite.

## Objetivo

Digitalizar as jornadas dos motoristas, centralizar dados operacionais e financeiros e facilitar o acompanhamento administrativo da frota.

## Funcionalidades

### Motoristas

- Autenticação individual e visualização do veículo e turno atribuídos.
- Abertura e encerramento de jornadas.
- Checklist das condições do veículo.
- Registro de quilometragem, bateria, fotografias e avarias.
- Registro de ganhos e despesas.

### Administração

- Painel de acompanhamento e histórico de jornadas com filtros.
- Cadastro e gerenciamento de motoristas, veículos e escalas.
- Correção administrativa de jornadas com registro de auditoria.
- Indicadores operacionais e financeiros.
- Exportação de relatórios em Excel.

## Tecnologias

Python, Flask, Flask-WTF, SQLite, Pillow, openpyxl e Gunicorn. A implantação utiliza Ubuntu, Nginx e AWS EC2.

## Estrutura principal

| Caminho | Finalidade |
| --- | --- |
| `app.py` | Aplicação Flask, regras e rotas |
| `database.py` | Conexão, inicialização e migrações SQLite |
| `criar_admin.py` | Utilitário de criação de administrador |
| `limpar_fotos.py` | Manutenção das fotografias |
| `templates/` | Páginas HTML |
| `static/` | CSS e imagens públicas |
| `instance/fotos_jornadas/` | Fotografias privadas das jornadas |
| `requirements.txt` | Dependências Python |

## Ambientes e banco de dados

A variável `ER_AMBIENTE` seleciona o banco:

- `ER_AMBIENTE=teste`: `transporte_teste.db`
- `ER_AMBIENTE=producao`: `transporte.db`

**Atenção:** quando a variável não é informada, o padrão atual é `producao`. Defina explicitamente `ER_AMBIENTE=teste` nos testes locais.

O banco contém as tabelas `administradores`, `motoristas`, `veiculos`, `acessos`, `escalas`, `jornadas`, `checklists`, `ganhos`, `despesas` e `auditoria_jornadas`.

## Execução local

Em um ambiente virtual Python já configurado, instale as dependências:

```bash
pip install -r requirements.txt
```

A aplicação exige uma chave secreta Flask, obtida da variável `FLASK_SECRET_KEY` ou do arquivo local `.flask_secret_key`. Não publique essa chave.

Para executar explicitamente no ambiente de teste:

```bash
ER_AMBIENTE=teste python app.py
```

Esse comando utiliza o servidor de desenvolvimento Flask, não o servidor de produção.

## Segurança e fotografias

A aplicação utiliza proteção CSRF e configurações de segurança para cookies de sessão. O acesso aos registros e fotografias depende das verificações implementadas nas rotas Flask.

As fotografias ficam fora de `static/`, em `instance/fotos_jornadas/`.

A rotina `limpar_fotos.py` realiza a limpeza de fotografias de jornadas encerradas há pelo menos 14 dias, preservando os dados estruturados. Na AWS, a execução automática está agendada por um timer systemd.

## Implantação

A aplicação está implantada na AWS EC2 com Ubuntu, Gunicorn e Nginx. Os procedimentos específicos de publicação, reinício, backup e recuperação serão detalhados na documentação operacional.

## Documentação planejada

- `docs/arquitetura.md`: componentes e fluxos.
- `docs/banco_de_dados.md`: tabelas e relacionamentos.
- `docs/seguranca.md`: autenticação, permissões e cuidados operacionais.
- `docs/implantacao_aws.md`: implantação e serviços.
- `docs/backup_recuperacao.md`: cópias de segurança e restauração.
- `docs/manutencao.md`: tarefas recorrentes e limpeza de fotografias.

## Diretriz de evolução

Priorizar consistência, segurança, backups, manutenção, documentação e testes antes de ampliar as funcionalidades comerciais.
