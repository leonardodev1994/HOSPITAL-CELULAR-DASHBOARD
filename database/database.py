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


MIGRATIONS = [
    ("0001_initial_schema", "_migration_0001_initial_schema"),
    ("0002_quiosques", "_migration_0002_quiosques"),
    ("0003_renomeia_quiosques", "_migration_0003_renomeia_quiosques"),
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


def _create_sqlite_schema(conn):
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
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        total REAL,
        status TEXT DEFAULT 'Ativa',
        usuario_id INTEGER,
        usuario_nome TEXT,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
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
        valor_total REAL
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
    _add_column_if_missing(cursor, "lancamentos", "venda_id", "INTEGER")
    _add_column_if_missing(cursor, "lancamentos", "venda_item_id", "INTEGER")

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
        venda_item_id INTEGER
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
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        valor_total DOUBLE PRECISION
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

    _add_postgres_column_if_missing(cursor, "lancamentos", "produto_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "quantidade", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "lancamentos", "venda_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "venda_item_id", "INTEGER")


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
