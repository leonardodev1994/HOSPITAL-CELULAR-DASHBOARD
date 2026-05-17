# Hospedagem online

## Estado atual

O sistema está pronto para rodar como app Streamlit com:

- `app.py` como arquivo principal;
- `requirements.txt` com dependências;
- banco SQLite em `banco.db`;
- backups locais na pasta `backups/`.

## Recomendação

Para uso interno rápido, hospedar em uma VPS simples é o caminho mais seguro, porque o SQLite e os backups locais continuam funcionando.

Para Streamlit Community Cloud, Render ou Railway, o app sobe mais facilmente, mas o banco SQLite pode não ser persistente dependendo do plano/ambiente. Para produção online de verdade, o ideal é migrar o banco para PostgreSQL/Supabase.

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
