import sqlite3


def init_db(db_path="banco.db"):
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


def _add_column_if_missing(cursor, table, column, column_type):
    columns = [
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
