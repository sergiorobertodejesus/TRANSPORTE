# Segurança — ER Transporte

## 1. Objetivo

Documentar os mecanismos de segurança identificados no sistema
ER Transporte e as verificações necessárias para sua manutenção.

Este documento não substitui uma auditoria completa.

## 2. Autenticação

O sistema possui autenticação separada para motoristas e
administradores.

As senhas são verificadas por meio de
`werkzeug.security.check_password_hash`.

O cadastro de motoristas utiliza
`generate_password_hash` para armazenar hashes das senhas.

## 3. Sessões

Configurações identificadas em `app.py`:

- SESSION_COOKIE_HTTPONLY = True
- SESSION_COOKIE_SAMESITE = "Lax"
- SESSION_COOKIE_SECURE condicionado a FLASK_HTTPS=1

A aplicação possui um controle `before_request`.

A implementação completa desse controle deverá ser
considerada nos testes de autorização.

## 4. Proteção CSRF

A aplicação utiliza Flask-WTF com `CSRFProtect(app)`.

Essa proteção deve ser preservada nas operações
administrativas e nos formulários dos motoristas.

## 5. Fotografias

As fotografias das jornadas são armazenadas fora da
pasta pública `static/`.

A rota `/foto_jornada/<nome_arquivo>` possui verificações
de sessão e autorização.

O código examinado inclui:

- Validação do nome do arquivo.
- Rejeição de sessão com dois tipos de usuário.
- Redirecionamento quando não existe autenticação.
- Consulta ao banco para verificar autorização.

A revisão completa dessa rota permanece pendente.

## 6. Limites de requisição

A configuração `MAX_CONTENT_LENGTH` estabelece um limite
de 8 MiB por requisição.

## 7. Proteção dos arquivos

O `.gitignore` exclui:

- Bancos SQLite.
- Arquivos de ambiente.
- Chave secreta local do Flask.
- Credenciais iniciais.
- Fotografias privadas em `instance/`.
- Backups locais.

O `.gitignore` não substitui a verificação dos arquivos
efetivamente rastreados pelo Git.

## 8. Ambiente de produção

A implantação utiliza AWS EC2, Ubuntu, Gunicorn e Nginx.

Verificações pendentes:

- Confirmar FLASK_HTTPS=1 no serviço de produção.
- Revisar permissões dos arquivos e diretórios.
- Revisar a autorização de todas as rotas administrativas.
- Revisar a autorização de acesso às fotografias.
- Verificar a proteção e a retenção dos backups.
- Confirmar os procedimentos de atualização e recuperação.

## 9. Diretrizes de manutenção

- Não registrar senhas ou chaves na documentação.
- Testar alterações primeiro no ambiente de teste.
- Realizar backup consistente antes de alterações críticas.
- Manter documentação e código versionados conjuntamente.
- Evitar alterações desnecessárias no sistema em produção.
