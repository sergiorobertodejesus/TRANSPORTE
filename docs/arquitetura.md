# Arquitetura — ER Transporte

## 1. Visão geral

A ER Transporte utiliza uma aplicação web monolítica em **Python/Flask**, com páginas renderizadas por **Jinja2**, arquivos estáticos e persistência em **SQLite**. O sistema atende motoristas e administradores, com autenticação separada e funções distintas.

Na implantação atual, a aplicação é servida em uma instância **AWS EC2 (Ubuntu)** com **Nginx** e **Gunicorn**. A execução local utiliza o servidor de desenvolvimento do Flask.

## 2. Componentes do repositório

| Componente | Responsabilidade |
| --- | --- |
| `app.py` | Inicialização Flask, autenticação, validações, rotas e regras operacionais |
| `database.py` | Seleção do ambiente, conexão SQLite, tabelas, índices e migrações |
| `criar_admin.py` | Utilitário administrativo para criação de acesso |
| `limpar_fotos.py` | Rotina independente de retenção e limpeza de fotografias |
| `templates/` | Telas públicas, dos motoristas e da administração |
| `static/` | Estilos e imagens públicas |
| `instance/fotos_jornadas/` | Arquivos de fotografias privadas, fora de `static/` |
| `requirements.txt` | Dependências Python fixadas |

## 3. Fluxos principais

### Motorista

1. Acessa `/login_motorista` e autentica-se individualmente.
2. Visualiza sua área em `/motorista`, incluindo veículo e turno da escala.
3. Registra o início da jornada, checklist, quilometragem, bateria e fotografias aplicáveis por `POST /jornada`.
4. Ao encerrar, informa dados finais, ganhos e despesas, também por `POST /jornada`.
5. O fluxo retorna à autenticação após iniciar ou encerrar a jornada.

O sistema impede o uso simultâneo de um veículo que já tenha uma jornada aberta. Não se deve presumir que haja validação completa de conflitos entre horários de escalas.

### Administração

1. Autentica-se em `/login_admin`.
2. Acessa `/painel_admin` para acompanhar jornadas e consultar histórico, filtros e indicadores.
3. Gerencia motoristas, veículos e escalas por rotas administrativas.
4. Pode editar/corrigir uma jornada em rotas específicas, com registro na tabela `auditoria_jornadas`.
5. Exporta relatórios em Excel por `/exportar_relatorio_excel`.

## 4. Rotas identificadas

| Rota | Finalidade |
| --- | --- |
| `/` | Página inicial |
| `/login_motorista` | Autenticação do motorista |
| `/motorista` | Área do motorista |
| `/jornada` | Recebimento de registros de jornada (POST) |
| `/sair` | Saída do motorista |
| `/login_admin` | Autenticação administrativa |
| `/painel_admin` | Painel administrativo |
| `/sair_admin` | Saída administrativa (POST) |
| `/admin/jornada/<int:jornada_id>/editar` | Formulário de edição administrativa |
| `/admin/jornada/<int:jornada_id>/salvar` | Gravação da correção (POST) |
| `/exportar_relatorio_excel` | Exportação de relatório |
| `/editar_escala` | Alteração de escala (POST) |
| `/cadastrar_motorista` | Cadastro de motorista (POST) |
| `/editar_motorista` | Edição de motorista (POST) |
| `/desativar_motorista` | Desativação de motorista (POST) |
| `/cadastrar_veiculo` | Cadastro de veículo (POST) |
| `/editar_veiculo` | Edição de veículo (POST) |
| `/foto_jornada/<nome_arquivo>` | Entrega controlada de fotografia |

**Observação:** esta relação foi extraída dos decoradores `@app.route` do código examinado. As verificações de autorização específicas de cada rota devem ser detalhadas em uma auditoria posterior.

## 5. Segurança observada

- Proteção CSRF com Flask-WTF.
- Cookies de sessão com `HttpOnly=True` e `SameSite=Lax`.
- `Secure` controlado por `FLASK_HTTPS=1`.
- Chave Flask fornecida por `FLASK_SECRET_KEY` ou pelo arquivo local `.flask_secret_key`.
- Verificação da situação ativa do administrador ou motorista a cada requisição autenticada, por `before_request`.
- Invalidação de sessão quando há simultaneamente identificação de administrador e motorista.
- Limite de requisição de 8 MiB e validação de formato/dimensões de fotografias.
- Fotografias fora da pasta pública `static/`.

Esses mecanismos foram identificados no código; sua presença não substitui testes de segurança e autorização.

## 6. Persistência e manutenção

O SQLite utiliza `PRAGMA foreign_keys = ON` e espera de até 10 segundos para situações de bloqueio. A seleção de banco é feita por `ER_AMBIENTE`:

- `teste` → `transporte_teste.db`;
- `producao` → `transporte.db`.

**Atenção:** o valor padrão é `producao`; para testes, sempre declarar `ER_AMBIENTE=teste`.

O utilitário `limpar_fotos.py` foi implantado para remover fotografias elegíveis após 14 dias do encerramento da jornada, preservando os registros estruturados. Na AWS, a execução automática utiliza um timer systemd. Os procedimentos de backup e restauração ainda devem ser documentados e testados separadamente.

## 7. Limites desta documentação

Esta é a primeira versão, baseada no levantamento de `app.py`, `database.py`, dependências e histórico de implantação. Não inclui credenciais, endereços internos, dados reais, diagrama completo de infraestrutura ou garantia de cobertura integral dos testes. Deve ser atualizada junto com as mudanças no código.
