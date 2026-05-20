import os
import sqlite3


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
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        self._cursor.execute(_postgres_query(query), params)
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
        return PostgresCursor(self._conn.cursor())

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
        return init_postgres_db(database_url)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        tipo TEXT,
        descricao TEXT,
        valor REAL
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

    _add_column_if_missing(cursor, "ordens_servico", "checklist_entrada", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "checklist_reparo", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "checklist_saida", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "pagamento_os", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "assinatura_entrada", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "assinatura_saida", "TEXT")

    conn.commit()
    return conn


def init_postgres_db(database_url):
    import psycopg2

    if "sslmode=" in database_url:
        raw_conn = psycopg2.connect(database_url)
    else:
        raw_conn = psycopg2.connect(database_url, sslmode="require")
    conn = PostgresConnection(raw_conn)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lancamentos (
        id SERIAL PRIMARY KEY,
        data TEXT,
        tipo TEXT,
        descricao TEXT,
        valor DOUBLE PRECISION,
        produto_id INTEGER,
        quantidade DOUBLE PRECISION
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

    conn.commit()
    return conn


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
