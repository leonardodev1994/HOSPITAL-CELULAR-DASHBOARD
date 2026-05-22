import argparse
import os
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.database import init_postgres_db  # noqa: E402


TABLES = [
    "usuarios",
    "clientes",
    "estoque",
    "vendas",
    "venda_itens",
    "lancamentos",
    "pagamentos",
    "estoque_movimentacoes",
    "despesas",
    "caixa",
    "ordens_servico",
    "auditoria",
]


def sqlite_rows(sqlite_conn, table):
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    columns = [column[0] for column in cursor.description]
    return columns, cursor.fetchall()


def upsert_rows(pg_conn, table, columns, rows):
    if not rows:
        return 0

    quoted_columns = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    update_columns = [column for column in columns if column != "id"]
    updates = ", ".join([f"{column} = EXCLUDED.{column}" for column in update_columns])

    query = f"""
    INSERT INTO {table} ({quoted_columns})
    VALUES ({placeholders})
    ON CONFLICT (id) DO UPDATE SET {updates}
    """

    cursor = pg_conn.cursor()
    for row in rows:
        cursor.execute(query, row)

    pg_conn.commit()
    return len(rows)


def reset_sequence(pg_conn, table):
    cursor = pg_conn.cursor()
    cursor.execute(f"""
    SELECT setval(
        pg_get_serial_sequence('{table}', 'id'),
        COALESCE((SELECT MAX(id) FROM {table}), 1),
        (SELECT COUNT(*) FROM {table}) > 0
    )
    """)
    pg_conn.commit()


def clear_tables(pg_conn):
    cursor = pg_conn.cursor()
    cursor.execute(f"TRUNCATE TABLE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
    pg_conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Migra o banco SQLite local banco.db para PostgreSQL/Supabase."
    )
    parser.add_argument("--sqlite", default=str(ROOT / "banco.db"), help="Caminho do banco SQLite local.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="URL PostgreSQL do Supabase.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Apaga as tabelas do Supabase antes de importar os dados locais.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Informe --database-url ou configure a variável DATABASE_URL.")

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise SystemExit(f"Banco SQLite não encontrado: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = init_postgres_db(args.database_url)

    if args.replace:
        clear_tables(pg_conn)

    total = 0
    for table in TABLES:
        columns, rows = sqlite_rows(sqlite_conn, table)
        imported = upsert_rows(pg_conn, table, columns, rows)
        reset_sequence(pg_conn, table)
        total += imported
        print(f"{table}: {imported} registros migrados")

    print(f"Concluído: {total} registros enviados para o Supabase.")


if __name__ == "__main__":
    main()
