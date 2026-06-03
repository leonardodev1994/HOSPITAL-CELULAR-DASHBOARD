import os
import sqlite3
import time


def _get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    try:
        import streamlit as st

        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None


class PostgresCursor:
    TRANSACTION_STATUS_INERROR = 3

    def __init__(self, cursor, conn):
        self._cursor = cursor
        self._conn = conn

    def execute(self, query, params=None):
        if self._conn.get_transaction_status() == self.TRANSACTION_STATUS_INERROR:
            self._conn.rollback()
        try:
            self._cursor.execute(_postgres_query(query), params)
        except Exception as error:
            self._conn.rollback()
            if error.__class__.__name__ == "InFailedSqlTransaction":
                self._cursor = self._conn.cursor()
                self._cursor.execute(_postgres_query(query), params)
                return self
            raise
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        return self._cursor.close()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnection:
    backend = "postgres"

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        if self._conn.get_transaction_status() == PostgresCursor.TRANSACTION_STATUS_INERROR:
            self._conn.rollback()
        return PostgresCursor(self._conn.cursor(), self._conn)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _postgres_query(query):
    return query.replace("?", "%s")


def init_db(db_path="banco.db"):
    database_url = _get_database_url()

    if database_url:
        return connect_postgres(database_url)

    return connect_sqlite(db_path)


def connect_sqlite(db_path="banco.db"):
    return sqlite3.connect(db_path, check_same_thread=False)


def connect_postgres(database_url):
    import psycopg2

    if "sslmode=" in database_url:
        raw_conn = psycopg2.connect(database_url)
    else:
        raw_conn = psycopg2.connect(database_url, sslmode="require")
    return PostgresConnection(raw_conn)


def recover_connection(conn):
    if getattr(conn, "backend", "sqlite") != "postgres":
        return

    try:
        conn.rollback()
    except Exception:
        pass


MIGRATIONS = [
    ("0001_initial_schema", "_migration_0001_initial_schema"),
    ("0002_quiosques", "_migration_0002_quiosques"),
    ("0003_renomeia_quiosques", "_migration_0003_renomeia_quiosques"),
    ("0004_os_history_notifications", "_migration_0004_os_history_notifications"),
    ("0005_preco_alterado_venda", "_migration_0005_preco_alterado_venda"),
    ("0006_estoque_planilha", "_migration_0006_estoque_planilha"),
    ("0007_cancelamento_vendas", "_migration_0007_cancelamento_vendas"),
    ("0008_indices_performance", "_migration_0008_indices_performance"),
    ("0009_servicos_sangrias", "_migration_0009_servicos_sangrias"),
    ("0010_catalogo_pecas", "_migration_0010_catalogo_pecas"),
    ("0011_catalogo_precos", "_migration_0011_catalogo_precos"),
]


QUIOSQUES_PADRAO = [
    (1, "Polo 1", "polo1"),
    (2, "Polo 2", "polo2"),
    (3, "São Luiz", "saoluiz"),
    (4, "Peixinho", "peixinho"),
]


SCOPED_TABLES = [
    "lancamentos",
    "pagamentos",
    "vendas",
    "venda_itens",
    "auditoria",
    "estoque",
    "estoque_movimentacoes",
    "despesas",
    "caixa",
    "ordens_servico",
    "clientes",
]


def initialize_database(conn):
    _ensure_migration_history(conn)
    applied = _applied_migrations(conn)

    for migration_id, migration_name in MIGRATIONS:
        if migration_id in applied:
            continue

        migration = globals()[migration_name]
        try:
            migration(conn)
            _record_migration(conn, migration_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _ensure_migration_history(conn):
    cursor = conn.cursor()
    timestamp_type = "TIMESTAMP" if getattr(conn, "backend", "sqlite") == "postgres" else "TEXT"
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS migration_history (
        id TEXT PRIMARY KEY,
        applied_at {timestamp_type} DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()


def _applied_migrations(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM migration_history")
    return {row[0] for row in cursor.fetchall()}


def _record_migration(conn, migration_id):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO migration_history (id) VALUES (?)",
        (migration_id,),
    )


def _migration_0001_initial_schema(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_schema(conn)
        return

    _create_sqlite_schema(conn)


def _migration_0002_quiosques(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_quiosque_schema(conn)
        return

    _create_sqlite_quiosque_schema(conn)


def _migration_0003_renomeia_quiosques(conn):
    cursor = conn.cursor()
    _seed_quiosques(cursor)
    _rename_quiosque_users(conn)


def _migration_0004_os_history_notifications(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_os_audit_schema(conn)
        return

    _create_sqlite_os_audit_schema(conn)


def _migration_0005_preco_alterado_venda(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_price_change_schema(conn)
        return

    _create_sqlite_price_change_schema(conn)


def _migration_0006_estoque_planilha(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_stock_spreadsheet_schema(conn)
        return

    _create_sqlite_stock_spreadsheet_schema(conn)


def _migration_0007_cancelamento_vendas(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_sales_cancel_schema(conn)
        return

    _create_sqlite_sales_cancel_schema(conn)


def _migration_0008_indices_performance(conn):
    _create_performance_indexes(conn)


def _migration_0009_servicos_sangrias(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_services_cash_schema(conn)
        return

    _create_sqlite_services_cash_schema(conn)


def _migration_0010_catalogo_pecas(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_parts_catalog_schema(conn)
        return

    _create_sqlite_parts_catalog_schema(conn)


def _migration_0011_catalogo_precos(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_catalog_price_schema(conn)
        return

    _create_sqlite_catalog_price_schema(conn)


def ensure_catalog_price_schema(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_catalog_price_schema(conn)
    else:
        _create_sqlite_catalog_price_schema(conn)
    conn.commit()


def ensure_quiosques_schema(conn):
    if getattr(conn, "backend", "sqlite") == "postgres":
        _create_postgres_quiosque_schema(conn)
    else:
        _create_sqlite_quiosque_schema(conn)
    conn.commit()


def _create_sqlite_schema(conn):
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        tipo TEXT,
        descricao TEXT,
        valor REAL,
        status TEXT DEFAULT 'Ativo',
        cancelado_em TEXT,
        cancelado_por_id INTEGER,
        cancelado_por_nome TEXT,
        cancelado_por_perfil TEXT,
        cancelado_motivo TEXT,
        alterado_em TEXT,
        alterado_por_id INTEGER,
        alterado_por_nome TEXT,
        alterado_por_perfil TEXT,
        alterado_motivo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lancamento_id INTEGER,
        forma_pagamento TEXT,
        valor REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        total REAL,
        status TEXT DEFAULT 'Ativa',
        usuario_id INTEGER,
        usuario_nome TEXT,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        cancelado_em TEXT,
        cancelado_por_id INTEGER,
        cancelado_por_nome TEXT,
        cancelado_por_perfil TEXT,
        cancelado_motivo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        lancamento_id INTEGER,
        tipo TEXT,
        descricao TEXT,
        produto_id INTEGER,
        quantidade REAL,
        valor_unitario REAL,
        valor_total REAL,
        status TEXT DEFAULT 'Ativo'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        acao TEXT,
        entidade TEXT,
        entidade_id INTEGER,
        detalhes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto TEXT NOT NULL,
        modelo TEXT,
        categoria TEXT,
        quantidade REAL NOT NULL DEFAULT 0,
        valor_venda REAL NOT NULL DEFAULT 0,
        estoque_minimo REAL NOT NULL DEFAULT 0,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        codigo TEXT,
        marca TEXT,
        custo REAL,
        fornecedor TEXT,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER,
        data TEXT,
        tipo TEXT,
        quantidade REAL,
        motivo TEXT,
        lancamento_id INTEGER,
        responsavel TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        descricao TEXT,
        valor REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        valor_inicial REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sangrias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        valor REAL NOT NULL DEFAULT 0,
        retirado_por TEXT,
        usuario_id INTEGER,
        usuario_nome TEXT,
        observacao TEXT,
        quiosque_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT,
        modelo TEXT,
        valor_padrao REAL NOT NULL DEFAULT 0,
        custo_estimado REAL,
        tempo_estimado TEXT,
        garantia TEXT,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        quiosque_id INTEGER,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marca TEXT,
        modelo TEXT NOT NULL,
        qualidade TEXT,
        custo_sem_aro REAL,
        venda_sem_aro REAL,
        lucro_sem_aro REAL,
        custo_com_aro REAL,
        venda_com_aro REAL,
        lucro_com_aro REAL,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        atendente TEXT,
        loja TEXT,
        cliente TEXT,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        marca TEXT,
        modelo TEXT,
        imei TEXT,
        senha TEXT,
        defeito TEXT,
        servico TEXT,
        valor REAL,
        garantia TEXT,
        status TEXT,
        observacoes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        email TEXT,
        observacoes TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        senha_salt TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'Atendente',
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    for column, column_type in [
        ("cliente_id", "INTEGER"),
        ("data", "TEXT"),
        ("atendente", "TEXT"),
        ("loja", "TEXT"),
        ("cliente", "TEXT"),
        ("cpf", "TEXT"),
        ("telefone", "TEXT"),
        ("endereco", "TEXT"),
        ("marca", "TEXT"),
        ("modelo", "TEXT"),
        ("imei", "TEXT"),
        ("senha", "TEXT"),
        ("defeito", "TEXT"),
        ("servico", "TEXT"),
        ("valor", "REAL"),
        ("garantia", "TEXT"),
        ("status", "TEXT"),
        ("observacoes", "TEXT"),
    ]:
        _add_column_if_missing(cursor, "ordens_servico", column, column_type)

    _add_column_if_missing(cursor, "lancamentos", "produto_id", "INTEGER")
    _add_column_if_missing(cursor, "lancamentos", "quantidade", "REAL")
    _add_column_if_missing(cursor, "lancamentos", "venda_id", "INTEGER")
    _add_column_if_missing(cursor, "lancamentos", "venda_item_id", "INTEGER")
    _add_column_if_missing(cursor, "lancamentos", "preco_original", "REAL")
    _add_column_if_missing(cursor, "lancamentos", "preco_vendido", "REAL")
    _add_column_if_missing(cursor, "lancamentos", "diferenca_preco", "REAL")
    _add_column_if_missing(cursor, "lancamentos", "observacao_alteracao_preco", "TEXT")
    _add_column_if_missing(cursor, "lancamentos", "usuario_responsavel_preco", "TEXT")
    _add_column_if_missing(cursor, "lancamentos", "data_hora_alteracao_preco", "TEXT")
    _add_column_if_missing(cursor, "venda_itens", "preco_original", "REAL")
    _add_column_if_missing(cursor, "venda_itens", "preco_vendido", "REAL")
    _add_column_if_missing(cursor, "venda_itens", "diferenca_preco", "REAL")
    _add_column_if_missing(cursor, "venda_itens", "observacao_alteracao_preco", "TEXT")
    _add_column_if_missing(cursor, "venda_itens", "usuario_responsavel_preco", "TEXT")
    _add_column_if_missing(cursor, "venda_itens", "data_hora_alteracao_preco", "TEXT")

    _add_column_if_missing(cursor, "ordens_servico", "checklist_entrada", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "checklist_reparo", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "checklist_saida", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "pagamento_os", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "assinatura_entrada", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "assinatura_saida", "TEXT")


def _create_postgres_schema(conn):
    cursor = conn.cursor()

    cursor.execute("SET LOCAL lock_timeout = '5s'")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lancamentos (
        id SERIAL PRIMARY KEY,
        data TEXT,
        tipo TEXT,
        descricao TEXT,
        valor DOUBLE PRECISION,
        produto_id INTEGER,
        quantidade DOUBLE PRECISION,
        venda_id INTEGER,
        venda_item_id INTEGER,
        status TEXT DEFAULT 'Ativo',
        cancelado_em TIMESTAMP,
        cancelado_por_id INTEGER,
        cancelado_por_nome TEXT,
        cancelado_por_perfil TEXT,
        cancelado_motivo TEXT,
        alterado_em TIMESTAMP,
        alterado_por_id INTEGER,
        alterado_por_nome TEXT,
        alterado_por_perfil TEXT,
        alterado_motivo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagamentos (
        id SERIAL PRIMARY KEY,
        lancamento_id INTEGER,
        forma_pagamento TEXT,
        valor DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id SERIAL PRIMARY KEY,
        data TEXT,
        total DOUBLE PRECISION,
        status TEXT DEFAULT 'Ativa',
        usuario_id INTEGER,
        usuario_nome TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cancelado_em TIMESTAMP,
        cancelado_por_id INTEGER,
        cancelado_por_nome TEXT,
        cancelado_por_perfil TEXT,
        cancelado_motivo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id SERIAL PRIMARY KEY,
        venda_id INTEGER,
        lancamento_id INTEGER,
        tipo TEXT,
        descricao TEXT,
        produto_id INTEGER,
        quantidade DOUBLE PRECISION,
        valor_unitario DOUBLE PRECISION,
        valor_total DOUBLE PRECISION,
        status TEXT DEFAULT 'Ativo'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id SERIAL PRIMARY KEY,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        acao TEXT,
        entidade TEXT,
        entidade_id INTEGER,
        detalhes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        id SERIAL PRIMARY KEY,
        produto TEXT NOT NULL,
        modelo TEXT,
        categoria TEXT,
        quantidade DOUBLE PRECISION NOT NULL DEFAULT 0,
        valor_venda DOUBLE PRECISION NOT NULL DEFAULT 0,
        estoque_minimo DOUBLE PRECISION NOT NULL DEFAULT 0,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        codigo TEXT,
        marca TEXT,
        custo DOUBLE PRECISION,
        fornecedor TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id SERIAL PRIMARY KEY,
        produto_id INTEGER,
        data TEXT,
        tipo TEXT,
        quantidade DOUBLE PRECISION,
        motivo TEXT,
        lancamento_id INTEGER,
        responsavel TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id SERIAL PRIMARY KEY,
        data TEXT,
        descricao TEXT,
        valor DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caixa (
        id SERIAL PRIMARY KEY,
        data TEXT,
        valor_inicial DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sangrias (
        id SERIAL PRIMARY KEY,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        valor DOUBLE PRECISION NOT NULL DEFAULT 0,
        retirado_por TEXT,
        usuario_id INTEGER,
        usuario_nome TEXT,
        observacao TEXT,
        quiosque_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        categoria TEXT,
        modelo TEXT,
        valor_padrao DOUBLE PRECISION NOT NULL DEFAULT 0,
        custo_estimado DOUBLE PRECISION,
        tempo_estimado TEXT,
        garantia TEXT,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        quiosque_id INTEGER,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_pecas (
        id SERIAL PRIMARY KEY,
        marca TEXT,
        modelo TEXT NOT NULL,
        qualidade TEXT,
        custo_sem_aro DOUBLE PRECISION,
        venda_sem_aro DOUBLE PRECISION,
        lucro_sem_aro DOUBLE PRECISION,
        custo_com_aro DOUBLE PRECISION,
        venda_com_aro DOUBLE PRECISION,
        lucro_com_aro DOUBLE PRECISION,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id SERIAL PRIMARY KEY,
        data TEXT,
        cliente_id INTEGER,
        atendente TEXT,
        loja TEXT,
        cliente TEXT,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        marca TEXT,
        modelo TEXT,
        imei TEXT,
        senha TEXT,
        defeito TEXT,
        servico TEXT,
        valor DOUBLE PRECISION,
        garantia TEXT,
        status TEXT,
        observacoes TEXT,
        checklist_entrada TEXT,
        checklist_reparo TEXT,
        checklist_saida TEXT,
        pagamento_os TEXT,
        assinatura_entrada TEXT,
        assinatura_saida TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        email TEXT,
        observacoes TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        usuario TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        senha_salt TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'Atendente',
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    _add_postgres_column_if_missing(cursor, "lancamentos", "produto_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "quantidade", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "lancamentos", "venda_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "venda_item_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "preco_original", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "lancamentos", "preco_vendido", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "lancamentos", "diferenca_preco", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "lancamentos", "observacao_alteracao_preco", "TEXT")
    _add_postgres_column_if_missing(cursor, "lancamentos", "usuario_responsavel_preco", "TEXT")
    _add_postgres_column_if_missing(cursor, "lancamentos", "data_hora_alteracao_preco", "TIMESTAMP")
    _add_postgres_column_if_missing(cursor, "venda_itens", "preco_original", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "venda_itens", "preco_vendido", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "venda_itens", "diferenca_preco", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "venda_itens", "observacao_alteracao_preco", "TEXT")
    _add_postgres_column_if_missing(cursor, "venda_itens", "usuario_responsavel_preco", "TEXT")
    _add_postgres_column_if_missing(cursor, "venda_itens", "data_hora_alteracao_preco", "TIMESTAMP")


def _create_sqlite_quiosque_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiosques (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL UNIQUE,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    _seed_quiosques(cursor)

    for table in SCOPED_TABLES:
        _add_column_if_missing(cursor, table, "quiosque_id", "INTEGER")
        cursor.execute(f"UPDATE {table} SET quiosque_id = 1 WHERE quiosque_id IS NULL")

    _add_column_if_missing(cursor, "usuarios", "quiosque_id", "INTEGER")
    _add_column_if_missing(cursor, "usuarios", "acesso_todos_quiosques", "INTEGER NOT NULL DEFAULT 0")
    cursor.execute("UPDATE usuarios SET quiosque_id = 1 WHERE quiosque_id IS NULL")
    cursor.execute("UPDATE usuarios SET acesso_todos_quiosques = 1 WHERE perfil = 'Admin'")
    _seed_quiosque_users(conn)


def _create_postgres_quiosque_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiosques (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL UNIQUE,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    _seed_quiosques(cursor)

    for table in SCOPED_TABLES:
        _add_postgres_column_if_missing(cursor, table, "quiosque_id", "INTEGER")
        cursor.execute(f"UPDATE {table} SET quiosque_id = 1 WHERE quiosque_id IS NULL")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_quiosque_id ON {table}(quiosque_id)")

    _add_postgres_column_if_missing(cursor, "usuarios", "quiosque_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "usuarios", "acesso_todos_quiosques", "INTEGER NOT NULL DEFAULT 0")
    cursor.execute("UPDATE usuarios SET quiosque_id = 1 WHERE quiosque_id IS NULL")
    cursor.execute("UPDATE usuarios SET acesso_todos_quiosques = 1 WHERE perfil = 'Admin'")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_quiosque_id ON usuarios(quiosque_id)")
    _seed_quiosque_users(conn)


def _create_sqlite_os_audit_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS os_historico_alteracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        os_id INTEGER NOT NULL,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        campo TEXT NOT NULL,
        valor_antigo TEXT,
        valor_novo TEXT,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notificacoes_admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        tipo TEXT,
        titulo TEXT,
        mensagem TEXT,
        entidade TEXT,
        entidade_id INTEGER,
        lida INTEGER NOT NULL DEFAULT 0,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_os_historico_os_id ON os_historico_alteracoes(os_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notificacoes_admin_lida ON notificacoes_admin(lida)")


def _create_postgres_os_audit_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS os_historico_alteracoes (
        id SERIAL PRIMARY KEY,
        os_id INTEGER NOT NULL,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        campo TEXT NOT NULL,
        valor_antigo TEXT,
        valor_novo TEXT,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notificacoes_admin (
        id SERIAL PRIMARY KEY,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tipo TEXT,
        titulo TEXT,
        mensagem TEXT,
        entidade TEXT,
        entidade_id INTEGER,
        lida INTEGER NOT NULL DEFAULT 0,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_os_historico_os_id ON os_historico_alteracoes(os_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_os_historico_quiosque_id ON os_historico_alteracoes(quiosque_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notificacoes_admin_lida ON notificacoes_admin(lida)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notificacoes_admin_quiosque_id ON notificacoes_admin(quiosque_id)")


def _create_sqlite_price_change_schema(conn):
    cursor = conn.cursor()
    for table in ["lancamentos", "venda_itens"]:
        _add_column_if_missing(cursor, table, "preco_original", "REAL")
        _add_column_if_missing(cursor, table, "preco_vendido", "REAL")
        _add_column_if_missing(cursor, table, "diferenca_preco", "REAL")
        _add_column_if_missing(cursor, table, "observacao_alteracao_preco", "TEXT")
        _add_column_if_missing(cursor, table, "usuario_responsavel_preco", "TEXT")
        _add_column_if_missing(cursor, table, "data_hora_alteracao_preco", "TEXT")


def _create_postgres_price_change_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    for table in ["lancamentos", "venda_itens"]:
        _add_postgres_column_if_missing(cursor, table, "preco_original", "DOUBLE PRECISION")
        _add_postgres_column_if_missing(cursor, table, "preco_vendido", "DOUBLE PRECISION")
        _add_postgres_column_if_missing(cursor, table, "diferenca_preco", "DOUBLE PRECISION")
        _add_postgres_column_if_missing(cursor, table, "observacao_alteracao_preco", "TEXT")
        _add_postgres_column_if_missing(cursor, table, "usuario_responsavel_preco", "TEXT")
        _add_postgres_column_if_missing(cursor, table, "data_hora_alteracao_preco", "TIMESTAMP")


def _create_sqlite_stock_spreadsheet_schema(conn):
    cursor = conn.cursor()
    _add_column_if_missing(cursor, "estoque", "codigo", "TEXT")
    _add_column_if_missing(cursor, "estoque", "marca", "TEXT")
    _add_column_if_missing(cursor, "estoque", "custo", "REAL")
    _add_column_if_missing(cursor, "estoque", "fornecedor", "TEXT")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_importacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        arquivo TEXT,
        cadastrados INTEGER NOT NULL DEFAULT 0,
        atualizados INTEGER NOT NULL DEFAULT 0,
        ignorados INTEGER NOT NULL DEFAULT 0,
        erros INTEGER NOT NULL DEFAULT 0,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_codigo_quiosque ON estoque(codigo, quiosque_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_importacoes_quiosque ON estoque_importacoes(quiosque_id)")


def _create_postgres_stock_spreadsheet_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    _add_postgres_column_if_missing(cursor, "estoque", "codigo", "TEXT")
    _add_postgres_column_if_missing(cursor, "estoque", "marca", "TEXT")
    _add_postgres_column_if_missing(cursor, "estoque", "custo", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "estoque", "fornecedor", "TEXT")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_importacoes (
        id SERIAL PRIMARY KEY,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        arquivo TEXT,
        cadastrados INTEGER NOT NULL DEFAULT 0,
        atualizados INTEGER NOT NULL DEFAULT 0,
        ignorados INTEGER NOT NULL DEFAULT 0,
        erros INTEGER NOT NULL DEFAULT 0,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_codigo_quiosque ON estoque(codigo, quiosque_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_importacoes_quiosque ON estoque_importacoes(quiosque_id)")


def _create_sqlite_sales_cancel_schema(conn):
    cursor = conn.cursor()
    for column, column_type in [
        ("status", "TEXT DEFAULT 'Ativo'"),
        ("cancelado_em", "TEXT"),
        ("cancelado_por_id", "INTEGER"),
        ("cancelado_por_nome", "TEXT"),
        ("cancelado_por_perfil", "TEXT"),
        ("cancelado_motivo", "TEXT"),
        ("alterado_em", "TEXT"),
        ("alterado_por_id", "INTEGER"),
        ("alterado_por_nome", "TEXT"),
        ("alterado_por_perfil", "TEXT"),
        ("alterado_motivo", "TEXT"),
    ]:
        _add_column_if_missing(cursor, "lancamentos", column, column_type)

    for column, column_type in [
        ("cancelado_em", "TEXT"),
        ("cancelado_por_id", "INTEGER"),
        ("cancelado_por_nome", "TEXT"),
        ("cancelado_por_perfil", "TEXT"),
        ("cancelado_motivo", "TEXT"),
    ]:
        _add_column_if_missing(cursor, "vendas", column, column_type)

    _add_column_if_missing(cursor, "venda_itens", "status", "TEXT DEFAULT 'Ativo'")
    cursor.execute("UPDATE lancamentos SET status = 'Ativo' WHERE status IS NULL OR status = ''")
    cursor.execute("UPDATE vendas SET status = 'Ativa' WHERE status IS NULL OR status = ''")
    cursor.execute("UPDATE venda_itens SET status = 'Ativo' WHERE status IS NULL OR status = ''")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lancamentos_status_data ON lancamentos(status, data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lancamentos_cancelado_em ON lancamentos(cancelado_em)")


def _create_postgres_sales_cancel_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    for column, column_type in [
        ("status", "TEXT DEFAULT 'Ativo'"),
        ("cancelado_em", "TIMESTAMP"),
        ("cancelado_por_id", "INTEGER"),
        ("cancelado_por_nome", "TEXT"),
        ("cancelado_por_perfil", "TEXT"),
        ("cancelado_motivo", "TEXT"),
        ("alterado_em", "TIMESTAMP"),
        ("alterado_por_id", "INTEGER"),
        ("alterado_por_nome", "TEXT"),
        ("alterado_por_perfil", "TEXT"),
        ("alterado_motivo", "TEXT"),
    ]:
        _add_postgres_column_if_missing(cursor, "lancamentos", column, column_type)

    for column, column_type in [
        ("cancelado_em", "TIMESTAMP"),
        ("cancelado_por_id", "INTEGER"),
        ("cancelado_por_nome", "TEXT"),
        ("cancelado_por_perfil", "TEXT"),
        ("cancelado_motivo", "TEXT"),
    ]:
        _add_postgres_column_if_missing(cursor, "vendas", column, column_type)

    _add_postgres_column_if_missing(cursor, "venda_itens", "status", "TEXT DEFAULT 'Ativo'")
    cursor.execute("UPDATE lancamentos SET status = 'Ativo' WHERE status IS NULL OR status = ''")
    cursor.execute("UPDATE vendas SET status = 'Ativa' WHERE status IS NULL OR status = ''")
    cursor.execute("UPDATE venda_itens SET status = 'Ativo' WHERE status IS NULL OR status = ''")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lancamentos_status_data ON lancamentos(status, data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lancamentos_cancelado_em ON lancamentos(cancelado_em)")


def _create_performance_indexes(conn):
    cursor = conn.cursor()
    if getattr(conn, "backend", "sqlite") == "postgres":
        cursor.execute("SET LOCAL lock_timeout = '5s'")

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_lancamentos_quiosque_status_data ON lancamentos(quiosque_id, status, data)",
        "CREATE INDEX IF NOT EXISTS idx_lancamentos_quiosque_data_id ON lancamentos(quiosque_id, data, id)",
        "CREATE INDEX IF NOT EXISTS idx_lancamentos_venda_id ON lancamentos(venda_id)",
        "CREATE INDEX IF NOT EXISTS idx_pagamentos_lancamento ON pagamentos(lancamento_id)",
        "CREATE INDEX IF NOT EXISTS idx_pagamentos_quiosque ON pagamentos(quiosque_id)",
        "CREATE INDEX IF NOT EXISTS idx_vendas_quiosque_status_data ON vendas(quiosque_id, status, data)",
        "CREATE INDEX IF NOT EXISTS idx_venda_itens_lancamento ON venda_itens(lancamento_id)",
        "CREATE INDEX IF NOT EXISTS idx_ordens_quiosque_status_id ON ordens_servico(quiosque_id, status, id)",
        "CREATE INDEX IF NOT EXISTS idx_ordens_cliente_busca ON ordens_servico(quiosque_id, cliente, telefone, cpf)",
        "CREATE INDEX IF NOT EXISTS idx_clientes_quiosque_ativo_nome ON clientes(quiosque_id, ativo, nome)",
        "CREATE INDEX IF NOT EXISTS idx_estoque_quiosque_ativo_produto ON estoque(quiosque_id, ativo, categoria, produto)",
        "CREATE INDEX IF NOT EXISTS idx_despesas_quiosque_data ON despesas(quiosque_id, data)",
        "CREATE INDEX IF NOT EXISTS idx_caixa_quiosque_data ON caixa(quiosque_id, data)",
    ]
    for query in indexes:
        cursor.execute(query)


def _create_sqlite_services_cash_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sangrias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        valor REAL NOT NULL DEFAULT 0,
        retirado_por TEXT,
        usuario_id INTEGER,
        usuario_nome TEXT,
        observacao TEXT,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT,
        modelo TEXT,
        valor_padrao REAL NOT NULL DEFAULT 0,
        custo_estimado REAL,
        tempo_estimado TEXT,
        garantia TEXT,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        quiosque_id INTEGER,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sangrias_quiosque_data ON sangrias(quiosque_id, data_hora)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servicos_quiosque_ativo_nome ON servicos(quiosque_id, ativo, nome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servicos_modelo ON servicos(modelo)")


def _create_postgres_services_cash_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sangrias (
        id SERIAL PRIMARY KEY,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        valor DOUBLE PRECISION NOT NULL DEFAULT 0,
        retirado_por TEXT,
        usuario_id INTEGER,
        usuario_nome TEXT,
        observacao TEXT,
        quiosque_id INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        categoria TEXT,
        modelo TEXT,
        valor_padrao DOUBLE PRECISION NOT NULL DEFAULT 0,
        custo_estimado DOUBLE PRECISION,
        tempo_estimado TEXT,
        garantia TEXT,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        quiosque_id INTEGER,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sangrias_quiosque_data ON sangrias(quiosque_id, data_hora)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servicos_quiosque_ativo_nome ON servicos(quiosque_id, ativo, nome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servicos_modelo ON servicos(modelo)")


def _create_sqlite_parts_catalog_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marca TEXT,
        modelo TEXT NOT NULL,
        qualidade TEXT,
        custo_sem_aro REAL,
        venda_sem_aro REAL,
        lucro_sem_aro REAL,
        custo_com_aro REAL,
        venda_com_aro REAL,
        lucro_com_aro REAL,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalogo_pecas_busca ON catalogo_pecas(ativo, marca, modelo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalogo_pecas_modelo ON catalogo_pecas(modelo)")


def _create_postgres_parts_catalog_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_pecas (
        id SERIAL PRIMARY KEY,
        marca TEXT,
        modelo TEXT NOT NULL,
        qualidade TEXT,
        custo_sem_aro DOUBLE PRECISION,
        venda_sem_aro DOUBLE PRECISION,
        lucro_sem_aro DOUBLE PRECISION,
        custo_com_aro DOUBLE PRECISION,
        venda_com_aro DOUBLE PRECISION,
        lucro_com_aro DOUBLE PRECISION,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalogo_pecas_busca ON catalogo_pecas(ativo, marca, modelo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalogo_pecas_modelo ON catalogo_pecas(modelo)")


def _create_sqlite_catalog_price_schema(conn):
    cursor = conn.cursor()
    for column in ["venda_sem_aro", "lucro_sem_aro", "venda_com_aro", "lucro_com_aro"]:
        _add_column_if_missing(cursor, "catalogo_pecas", column, "REAL")

    cursor.execute("""
    UPDATE catalogo_pecas
    SET
        venda_sem_aro = CASE
            WHEN COALESCE(venda_sem_aro, 0) > 0 THEN venda_sem_aro
            WHEN COALESCE(custo_sem_aro, 0) > 0 THEN MAX(custo_sem_aro * 2, custo_sem_aro + 100)
            ELSE 0
        END,
        lucro_sem_aro = CASE
            WHEN COALESCE(lucro_sem_aro, 0) > 0 THEN lucro_sem_aro
            WHEN COALESCE(custo_sem_aro, 0) > 0 THEN MAX(custo_sem_aro * 2, custo_sem_aro + 100) - custo_sem_aro
            ELSE 0
        END,
        venda_com_aro = CASE
            WHEN COALESCE(venda_com_aro, 0) > 0 THEN venda_com_aro
            WHEN COALESCE(custo_com_aro, 0) > 0 THEN MAX(custo_com_aro * 2, custo_com_aro + 100)
            ELSE 0
        END,
        lucro_com_aro = CASE
            WHEN COALESCE(lucro_com_aro, 0) > 0 THEN lucro_com_aro
            WHEN COALESCE(custo_com_aro, 0) > 0 THEN MAX(custo_com_aro * 2, custo_com_aro + 100) - custo_com_aro
            ELSE 0
        END
    """)


def _create_postgres_catalog_price_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SET LOCAL lock_timeout = '5s'")
    for column in ["venda_sem_aro", "lucro_sem_aro", "venda_com_aro", "lucro_com_aro"]:
        _add_postgres_column_if_missing(cursor, "catalogo_pecas", column, "DOUBLE PRECISION")

    cursor.execute("""
    UPDATE catalogo_pecas
    SET
        venda_sem_aro = CASE
            WHEN COALESCE(venda_sem_aro, 0) > 0 THEN venda_sem_aro
            WHEN COALESCE(custo_sem_aro, 0) > 0 THEN GREATEST(custo_sem_aro * 2, custo_sem_aro + 100)
            ELSE 0
        END,
        lucro_sem_aro = CASE
            WHEN COALESCE(lucro_sem_aro, 0) > 0 THEN lucro_sem_aro
            WHEN COALESCE(custo_sem_aro, 0) > 0 THEN GREATEST(custo_sem_aro * 2, custo_sem_aro + 100) - custo_sem_aro
            ELSE 0
        END,
        venda_com_aro = CASE
            WHEN COALESCE(venda_com_aro, 0) > 0 THEN venda_com_aro
            WHEN COALESCE(custo_com_aro, 0) > 0 THEN GREATEST(custo_com_aro * 2, custo_com_aro + 100)
            ELSE 0
        END,
        lucro_com_aro = CASE
            WHEN COALESCE(lucro_com_aro, 0) > 0 THEN lucro_com_aro
            WHEN COALESCE(custo_com_aro, 0) > 0 THEN GREATEST(custo_com_aro * 2, custo_com_aro + 100) - custo_com_aro
            ELSE 0
        END
    """)


def _seed_quiosques(cursor):
    for quiosque_id, nome, _usuario in QUIOSQUES_PADRAO:
        cursor.execute(
            """
            INSERT INTO quiosques (id, nome, ativo)
            VALUES (?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                nome = excluded.nome,
                ativo = excluded.ativo
            """,
            (quiosque_id, nome, 1),
        )


def _seed_quiosque_users(conn):
    from utils.auth import hash_password

    cursor = conn.cursor()
    for quiosque_id, nome, usuario in QUIOSQUES_PADRAO:
        exists = cursor.execute(
            "SELECT id FROM usuarios WHERE usuario = ? LIMIT 1",
            (usuario,),
        ).fetchone()
        if exists:
            continue

        salt, password_hash = hash_password(usuario)
        cursor.execute("""
        INSERT INTO usuarios (
            nome,
            usuario,
            senha_hash,
            senha_salt,
            perfil,
            ativo,
            quiosque_id,
            acesso_todos_quiosques
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome,
            usuario,
            password_hash,
            salt,
            "Atendente",
            1,
            quiosque_id,
            0,
        ))

    _rename_quiosque_users(conn)


def _rename_quiosque_users(conn):
    from utils.auth import hash_password

    cursor = conn.cursor()
    for quiosque_id, nome, usuario in QUIOSQUES_PADRAO:
        legacy_user = f"quiosque{quiosque_id}"
        official_exists = cursor.execute(
            "SELECT id FROM usuarios WHERE usuario = ? LIMIT 1",
            (usuario,),
        ).fetchone()

        if official_exists:
            cursor.execute(
                "UPDATE usuarios SET nome = ?, quiosque_id = ? WHERE usuario = ?",
                (nome, quiosque_id, usuario),
            )
            continue

        salt, password_hash = hash_password(usuario)
        cursor.execute(
            """
            UPDATE usuarios
            SET nome = ?, usuario = ?, senha_hash = ?, senha_salt = ?, quiosque_id = ?
            WHERE usuario = ?
            """,
            (nome, usuario, password_hash, salt, quiosque_id, legacy_user),
        )


def execute_insert_returning_id(conn, cursor, query, params):
    if getattr(conn, "backend", "sqlite") == "postgres":
        cursor.execute(f"{query.strip()} RETURNING id", params)
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id

    cursor.execute(query, params)
    conn.commit()
    return cursor.lastrowid


def _add_column_if_missing(cursor, table, column, column_type):
    columns = [
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def _add_postgres_column_if_missing(cursor, table, column, column_type):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ?
          AND column_name = ?
        LIMIT 1
        """,
        (table, column),
    )
    if cursor.fetchone():
        print(f"[migration] ALTER TABLE {table} ADD COLUMN {column} skipped; column exists")
        return

    started_at = time.perf_counter()
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
    elapsed = time.perf_counter() - started_at
    print(f"[migration] ALTER TABLE {table} ADD COLUMN {column} finished in {elapsed:.3f}s")
