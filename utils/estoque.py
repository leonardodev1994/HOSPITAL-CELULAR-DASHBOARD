from datetime import datetime

import pandas as pd

from database.database import execute_insert_returning_id
from utils.quiosques import current_quiosque_id, scope_clause, scoped_params


PLANILHA_PADRAO = "/Users/macdeleonardo/Downloads/Controle_Estoque_Peixinho_2.xlsx"


def normalize_text(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def produto_label(row):
    if hasattr(row, "get"):
        produto = row.get("produto")
        modelo = row.get("modelo")
    else:
        produto = getattr(row, "produto", "")
        modelo = getattr(row, "modelo", "")

    produto = normalize_text(produto)
    modelo = normalize_text(modelo)

    if modelo:
        return f"{produto} - {modelo}"
    return produto


def normalize_product_row(row):
    produto = normalize_text(row.get("Produto"))
    modelo = normalize_text(row.get("Modelo"))
    categoria = normalize_text(row.get("Categoria"))

    if produto.lower().startswith("película") or categoria.lower().startswith("pel"):
        produto = "Película 3D"
        modelo = ""
        categoria = "Películas"

    quantidade = pd.to_numeric(row.get("Quantidade"), errors="coerce")
    valor_venda = pd.to_numeric(row.get("Valor Venda"), errors="coerce")
    estoque_minimo = pd.to_numeric(row.get("Estoque Mínimo"), errors="coerce")

    return {
        "produto": produto,
        "modelo": modelo,
        "categoria": categoria,
        "quantidade": 0 if pd.isna(quantidade) else float(quantidade),
        "valor_venda": 0 if pd.isna(valor_venda) else float(valor_venda),
        "estoque_minimo": 0 if pd.isna(estoque_minimo) else float(estoque_minimo),
        "observacao": normalize_text(row.get("Observação")),
    }


def read_inventory_file(path):
    df = pd.read_excel(path, sheet_name="Produtos")
    rows = [normalize_product_row(row) for _, row in df.iterrows()]
    rows = [row for row in rows if row["produto"]]

    normalized = pd.DataFrame(rows)
    if normalized.empty:
        return normalized

    consolidated = (
        normalized.groupby(["produto", "modelo", "categoria"], dropna=False, as_index=False)
        .agg(
            quantidade=("quantidade", "sum"),
            valor_venda=("valor_venda", "max"),
            estoque_minimo=("estoque_minimo", "max"),
            observacao=("observacao", lambda values: " | ".join([v for v in values if v])),
        )
    )

    return consolidated.sort_values(["categoria", "produto", "modelo"]).reset_index(drop=True)


def import_inventory_from_excel(conn, path=PLANILHA_PADRAO):
    df = read_inventory_file(path)
    cursor = conn.cursor()
    imported = 0
    updated = 0

    for row in df.to_dict("records"):
        existing = cursor.execute("""
        SELECT id
        FROM estoque
        WHERE produto = ? AND COALESCE(modelo, '') = COALESCE(?, '')
          AND quiosque_id = ?
        """, (row["produto"], row["modelo"], current_quiosque_id())).fetchone()

        if existing:
            cursor.execute("""
            UPDATE estoque
            SET categoria = ?,
                quantidade = ?,
                valor_venda = ?,
                estoque_minimo = ?,
                observacao = ?,
                ativo = 1,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND quiosque_id = ?
            """, (
                row["categoria"],
                row["quantidade"],
                row["valor_venda"],
                row["estoque_minimo"],
                row["observacao"],
                existing[0],
                current_quiosque_id(),
            ))
            updated += 1
        else:
            cursor.execute("""
            INSERT INTO estoque (
                produto,
                modelo,
                categoria,
                quantidade,
                valor_venda,
                estoque_minimo,
                observacao,
                quiosque_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["produto"],
                row["modelo"],
                row["categoria"],
                row["quantidade"],
                row["valor_venda"],
                row["estoque_minimo"],
                row["observacao"],
                current_quiosque_id(),
            ))
            imported += 1

    conn.commit()
    return imported, updated, len(df)


def add_stock_product(
    conn,
    produto,
    modelo="",
    categoria="",
    quantidade=0,
    valor_venda=0,
    estoque_minimo=0,
    observacao="",
):
    produto = normalize_text(produto)
    modelo = normalize_text(modelo)
    categoria = normalize_text(categoria)
    observacao = normalize_text(observacao)
    quantidade = float(quantidade or 0)
    valor_venda = float(valor_venda or 0)
    estoque_minimo = float(estoque_minimo or 0)

    if not produto:
        raise ValueError("Informe o nome do produto.")

    cursor = conn.cursor()
    existing = cursor.execute("""
    SELECT id, quantidade
    FROM estoque
    WHERE produto = ? AND COALESCE(modelo, '') = COALESCE(?, '')
      AND quiosque_id = ?
    """, (produto, modelo, current_quiosque_id())).fetchone()

    if existing:
        produto_id = existing[0]
        nova_quantidade = float(existing[1] or 0) + quantidade
        cursor.execute("""
        UPDATE estoque
        SET categoria = ?,
            quantidade = ?,
            valor_venda = ?,
            estoque_minimo = ?,
            observacao = ?,
            ativo = 1,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ? AND quiosque_id = ?
        """, (
            categoria,
            nova_quantidade,
            valor_venda,
            estoque_minimo,
            observacao,
            produto_id,
            current_quiosque_id(),
        ))
        conn.commit()
    else:
        produto_id = execute_insert_returning_id(conn, cursor, """
        INSERT INTO estoque (
            produto,
            modelo,
            categoria,
            quantidade,
            valor_venda,
            estoque_minimo,
            observacao,
            quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            produto,
            modelo,
            categoria,
            quantidade,
            valor_venda,
            estoque_minimo,
            observacao,
            current_quiosque_id(),
        ))

    if quantidade > 0:
        register_stock_movement(
            conn,
            produto_id,
            "Entrada",
            quantidade,
            "Cadastro de produto",
        )

    return produto_id, bool(existing)


def load_stock(conn, only_active=True):
    scope, params = scope_clause()
    query = "SELECT * FROM estoque"
    if only_active:
        query += " WHERE ativo = 1"
        if scope:
            query += scope.replace(" WHERE ", " AND ")
    else:
        query += scope
    query += " ORDER BY categoria, produto, modelo"
    return pd.read_sql_query(query, conn, params=params)


def load_stock_movements(conn, limit=50):
    scope, params = scope_clause("m", prefix="WHERE")
    return pd.read_sql_query("""
    SELECT
        m.data,
        e.produto,
        e.modelo,
        e.categoria,
        m.tipo,
        m.quantidade,
        m.motivo,
        m.lancamento_id,
        m.responsavel
    FROM estoque_movimentacoes m
    LEFT JOIN estoque e ON e.id = m.produto_id
    """ + scope + """
    ORDER BY m.id DESC
    LIMIT ?
    """, conn, params=params + (limit,))


def register_stock_movement(conn, produto_id, tipo, quantidade, motivo, lancamento_id=None, responsavel="Sistema"):
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO estoque_movimentacoes (
        produto_id,
        data,
        tipo,
        quantidade,
        motivo,
        lancamento_id,
        responsavel,
        quiosque_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        produto_id,
        datetime.today().strftime("%Y-%m-%d"),
        tipo,
        quantidade,
        motivo,
        lancamento_id,
        responsavel,
        current_quiosque_id(),
    ))
    conn.commit()


def reduce_stock(conn, produto_id, quantidade, lancamento_id=None):
    cursor = conn.cursor()
    produto = cursor.execute(
        "SELECT quantidade FROM estoque WHERE id = ? AND quiosque_id = ?",
        (produto_id, current_quiosque_id()),
    ).fetchone()

    if not produto:
        raise ValueError("Produto não encontrado no estoque.")

    quantidade_atual = float(produto[0] or 0)
    nova_quantidade = quantidade_atual - float(quantidade)

    if nova_quantidade < 0:
        raise ValueError("Quantidade em estoque insuficiente.")

    cursor.execute("""
    UPDATE estoque
    SET quantidade = ?, atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (nova_quantidade, produto_id, current_quiosque_id()))
    conn.commit()

    register_stock_movement(
        conn,
        produto_id,
        "Saída",
        quantidade,
        "Venda em lançamento",
        lancamento_id=lancamento_id,
    )


def restore_stock(conn, produto_id, quantidade, lancamento_id=None, motivo="Venda removida"):
    if not produto_id or not quantidade:
        return

    cursor = conn.cursor()
    produto = cursor.execute(
        "SELECT quantidade FROM estoque WHERE id = ? AND quiosque_id = ?",
        (produto_id, current_quiosque_id()),
    ).fetchone()

    if not produto:
        return

    nova_quantidade = float(produto[0] or 0) + float(quantidade)
    cursor.execute("""
    UPDATE estoque
    SET quantidade = ?, atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (nova_quantidade, produto_id, current_quiosque_id()))
    conn.commit()

    register_stock_movement(
        conn,
        produto_id,
        "Estorno",
        quantidade,
        motivo,
        lancamento_id=lancamento_id,
    )


def adjust_stock(conn, produto_id, quantidade, valor_venda, estoque_minimo, observacao):
    cursor = conn.cursor()
    atual = cursor.execute(
        "SELECT quantidade FROM estoque WHERE id = ? AND quiosque_id = ?",
        (produto_id, current_quiosque_id()),
    ).fetchone()
    quantidade_anterior = float(atual[0] or 0) if atual else 0
    diferenca = float(quantidade) - quantidade_anterior

    cursor.execute("""
    UPDATE estoque
    SET quantidade = ?,
        valor_venda = ?,
        estoque_minimo = ?,
        observacao = ?,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (quantidade, valor_venda, estoque_minimo, observacao, produto_id, current_quiosque_id()))
    conn.commit()

    if diferenca != 0:
        register_stock_movement(
            conn,
            produto_id,
            "Ajuste",
            diferenca,
            "Ajuste manual de estoque",
        )
