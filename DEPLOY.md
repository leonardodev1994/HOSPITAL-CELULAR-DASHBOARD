# Hospedagem online

## Estado atual

O sistema está pronto para rodar como app Streamlit com:

- `app.py` como arquivo principal;
- `requirements.txt` com dependências;
- banco SQLite local em `banco.db`;
- suporte a PostgreSQL/Supabase quando `DATABASE_URL` estiver configurado;
- backups locais na pasta `backups/`.

## Recomendação

Para uso interno rápido, hospedar em uma VPS simples é o caminho mais seguro, porque o SQLite e os backups locais continuam funcionando.

Para Streamlit Community Cloud, Render ou Railway, o app sobe mais facilmente, mas o banco SQLite pode não ser persistente dependendo do plano/ambiente. Para produção online de verdade, o ideal é migrar o banco para PostgreSQL/Supabase.

## Streamlit Cloud + Supabase

No Supabase, crie um projeto e copie a connection string PostgreSQL em:

```text
Project Settings > Database > Connection string
```

No Streamlit Cloud, abra:

```text
App > Settings > Secrets
```

E adicione:

```toml
DATABASE_URL = "postgresql://postgres.SEUPROJETO:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
```

Depois de salvar o Secret, reinicie o app no Streamlit Cloud.

## Migrar dados do banco local para Supabase

Com a URL do Supabase em mãos, rode no seu computador:

```bash
./.venv/bin/python scripts/migrate_sqlite_to_supabase.py --database-url "SUA_DATABASE_URL_DO_SUPABASE" --replace
```

O `--replace` apaga os dados atuais no Supabase antes de enviar os dados do `banco.db` local. Use sem `--replace` se quiser apenas atualizar/inserir pelos IDs.

## Comando de execução

```bash
streamlit run app.py --server.port 8503
```

## Render/Railway

Use:

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT`

O `Procfile` já contém esse start command.

## Próximo passo recomendado

Antes de colocar online para uso diário:

1. Definir onde os dados ficarão: VPS com SQLite ou PostgreSQL online.
2. Alterar a senha padrão do usuário `admin`.
3. Fazer backup do `banco.db`.
4. Testar login, OS, PDF e backup no servidor.

## Backup no Google Drive

Este projeto usa `rclone` para enviar backups para:

```text
gdrive:Hospital do Celular/Backups
```

No computador local, o `rclone` fica em `tools/rclone` e a autorização da conta Google fica fora do projeto, em:

```text
~/.config/rclone/rclone.conf
```

Em outro computador ou servidor, será necessário configurar o `rclone` novamente.
