from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from database.database import execute_insert_returning_id
from utils.quiosques import current_quiosque_id, scope_clause, scoped_params


PLANILHA_PADRAO = "/Users/macdeleonardo/Downloads/Controle_Estoque_Peixinho_2.xlsx"

IMPORT_COLUMNS = [
    "codigo",
    "produto",
    "categoria",
    "marca",
    "modelo",
    "quantidade",
    "custo",
    "valor_venda",
    "fornecedor",
    "estoque_minimo",
    "observacao",
    "ativo",
]

IMPORT_TEMPLATE_COLUMNS = {
    "codigo": "Código/SKU",
    "produto": "Nome/Descrição",
    "categoria": "Categoria",
    "marca": "Marca",
    "modelo": "Modelo compatível",
    "quantidade": "Quantidade",
    "custo": "Custo",
    "valor_venda": "Preço de venda",
    "fornecedor": "Fornecedor",
    "estoque_minimo": "Estoque mínimo",
    "observacao": "Observação",
    "ativo": "Status",
}

COLUMN_ALIASES = {
    "codigo": {"codigo", "código", "sku", "código/sku", "codigo/sku", "código do produto", "codigo do produto"},
    "produto": {"produto", "nome", "descrição", "descricao", "nome/descrição", "nome/descricao", "produto/descrição", "produto/descricao"},
    "categoria": {"categoria"},
    "marca": {"marca"},
    "modelo": {"modelo", "modelo compatível", "modelo compativel"},
    "quantidade": {"quantidade", "qtd", "estoque"},
    "custo": {"custo", "preço de custo", "preco de custo", "valor de custo"},
    "valor_venda": {"valor venda", "valor_venda", "preço de venda", "preco de venda", "valor de venda"},
    "fornecedor": {"fornecedor"},
    "estoque_minimo": {"estoque mínimo", "estoque minimo", "mínimo", "minimo"},
    "observacao": {"observação", "observacao", "obs"},
    "ativo": {"ativo", "status"},
}


def normalize_text(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def _normalize_header(value):
    return normalize_text(value).lower()


def _column_map(columns):
    normalized = {_normalize_header(column): column for column in columns}
    result = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                result[field] = normalized[alias]
                break
    return result


def _to_float(value, default=0):
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return default
    return float(number)


def _active_value(value):
    text = normalize_text(value).lower()
    if not text:
        return 1
    if text in {"ativo", "sim", "s", "yes", "1", "true", "ok"}:
        return 1
    if text in {"inativo", "não", "nao", "n", "no", "0", "false"}:
        return 0
    return 1


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
    produto = normalize_text(row.get("Produto") or row.get("Nome/Descrição"))
    modelo = normalize_text(row.get("Modelo") or row.get("Modelo compatível"))
    categoria = normalize_text(row.get("Categoria"))

    if produto.lower().startswith("película") or categoria.lower().startswith("pel"):
        produto = "Película 3D"
        modelo = ""
        categoria = "Películas"

    quantidade = pd.to_numeric(row.get("Quantidade"), errors="coerce")
    valor_venda = pd.to_numeric(row.get("Valor Venda"), errors="coerce")
    estoque_minimo = pd.to_numeric(row.get("Estoque Mínimo"), errors="coerce")

    return {
        "codigo": normalize_text(row.get("Código/SKU") or row.get("Codigo") or row.get("SKU")),
        "produto": produto,
        "modelo": modelo,
        "categoria": categoria,
        "marca": normalize_text(row.get("Marca")),
        "quantidade": 0 if pd.isna(quantidade) else float(quantidade),
        "custo": _to_float(row.get("Custo"), 0),
        "valor_venda": 0 if pd.isna(valor_venda) else float(valor_venda),
        "estoque_minimo": 0 if pd.isna(estoque_minimo) else float(estoque_minimo),
        "fornecedor": normalize_text(row.get("Fornecedor")),
        "observacao": normalize_text(row.get("Observação")),
        "ativo": _active_value(row.get("Status") or row.get("Ativo")),
    }


def read_inventory_file(path):
    df = pd.read_excel(path, sheet_name="Produtos")
    rows = [normalize_product_row(row) for _, row in df.iterrows()]
    rows = [row for row in rows if row["produto"]]

    normalized = pd.DataFrame(rows)
    if normalized.empty:
        return normalized

    consolidated = (
        normalized.groupby(["codigo", "produto", "modelo", "categoria", "marca", "fornecedor"], dropna=False, as_index=False)
        .agg(
            quantidade=("quantidade", "sum"),
            custo=("custo", "max"),
            valor_venda=("valor_venda", "max"),
            estoque_minimo=("estoque_minimo", "max"),
            observacao=("observacao", lambda values: " | ".join([v for v in values if v])),
            ativo=("ativo", "max"),
        )
    )

    return consolidated.sort_values(["categoria", "produto", "modelo"]).reset_index(drop=True)


def import_inventory_from_excel(conn, path=PLANILHA_PADRAO):
    df = read_inventory_file(path)
    cursor = conn.cursor()
    imported = 0
    updated = 0

    for row in df.to_dict("records"):
        existing = _find_existing_product(cursor, row, current_quiosque_id())

        if existing:
            cursor.execute("""
            UPDATE estoque
            SET categoria = ?,
                codigo = ?,
                marca = ?,
                quantidade = ?,
                custo = ?,
                valor_venda = ?,
                fornecedor = ?,
                estoque_minimo = ?,
                observacao = ?,
                ativo = 1,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND quiosque_id = ?
            """, (
                row["categoria"],
                row["codigo"],
                row["marca"],
                row["quantidade"],
                row["custo"],
                row["valor_venda"],
                row["fornecedor"],
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
                codigo,
                marca,
                quantidade,
                custo,
                valor_venda,
                fornecedor,
                estoque_minimo,
                observacao,
                ativo,
                quiosque_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["produto"],
                row["modelo"],
                row["categoria"],
                row["codigo"],
                row["marca"],
                row["quantidade"],
                row["custo"],
                row["valor_venda"],
                row["fornecedor"],
                row["estoque_minimo"],
                row["observacao"],
                row["ativo"],
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
    codigo="",
    marca="",
    custo=0,
    fornecedor="",
):
    produto = normalize_text(produto)
    modelo = normalize_text(modelo)
    categoria = normalize_text(categoria)
    observacao = normalize_text(observacao)
    codigo = normalize_text(codigo)
    marca = normalize_text(marca)
    fornecedor = normalize_text(fornecedor)
    quantidade = float(quantidade or 0)
    valor_venda = float(valor_venda or 0)
    estoque_minimo = float(estoque_minimo or 0)
    custo = float(custo or 0)

    if not produto:
        raise ValueError("Informe o nome do produto.")
    if quantidade < 0 or valor_venda < 0 or estoque_minimo < 0 or custo < 0:
        raise ValueError("Quantidade, custo e valores não podem ser negativos.")

    cursor = conn.cursor()
    if codigo:
        existing = cursor.execute("""
        SELECT id, quantidade
        FROM estoque
        WHERE codigo = ? AND quiosque_id = ?
        """, (codigo, current_quiosque_id())).fetchone()
    else:
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
        SET produto = ?,
            modelo = ?,
            categoria = ?,
            codigo = ?,
            marca = ?,
            quantidade = ?,
            custo = ?,
            valor_venda = ?,
            fornecedor = ?,
            estoque_minimo = ?,
            observacao = ?,
            ativo = 1,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ? AND quiosque_id = ?
        """, (
            produto,
            modelo,
            categoria,
            codigo,
            marca,
            nova_quantidade,
            custo,
            valor_venda,
            fornecedor,
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
            codigo,
            marca,
            quantidade,
            custo,
            valor_venda,
            fornecedor,
            estoque_minimo,
            observacao,
            quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            produto,
            modelo,
            categoria,
            codigo,
            marca,
            quantidade,
            custo,
            valor_venda,
            fornecedor,
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
    scope, params = scope_clause("e")
    query = """
    SELECT
        e.*,
        q.nome AS quiosque_nome
    FROM estoque e
    LEFT JOIN quiosques q ON q.id = e.quiosque_id
    """
    if only_active:
        query += " WHERE e.ativo = 1"
        if scope:
            query += scope.replace(" WHERE ", " AND ")
    else:
        query += scope
    query += " ORDER BY e.categoria, e.produto, e.modelo"
    return pd.read_sql_query(query, conn, params=params)


@st.cache_data(show_spinner=False, ttl=120)
def export_stock_to_excel(df_stock):
    export = df_stock.copy()
    if export.empty:
        export = pd.DataFrame(columns=[
            "codigo", "produto", "categoria", "marca", "modelo", "quantidade",
            "custo", "valor_venda", "fornecedor", "quiosque_id", "ativo",
            "criado_em", "atualizado_em",
        ])

    export["Status"] = export.get("ativo", 1).map({1: "Ativo", 0: "Inativo"}).fillna("Ativo")
    export["Quiosque/Unidade"] = export.get("quiosque_nome", export.get("quiosque_id", ""))
    columns = {
        "codigo": "Código/SKU",
        "produto": "Nome/Descrição",
        "categoria": "Categoria",
        "marca": "Marca",
        "modelo": "Modelo compatível",
        "quantidade": "Quantidade",
        "custo": "Custo",
        "valor_venda": "Preço de venda",
        "fornecedor": "Fornecedor",
        "Quiosque/Unidade": "Quiosque/Unidade",
        "Status": "Status",
        "criado_em": "Data de cadastro",
        "atualizado_em": "Última atualização",
        "observacao": "Observação",
    }
    for column in columns:
        if column not in export.columns:
            export[column] = ""

    output = BytesIO()
    export[list(columns.keys())].rename(columns=columns).to_excel(output, index=False, sheet_name="Estoque")
    output.seek(0)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def import_template_excel():
    sample = pd.DataFrame([{
        "Código/SKU": "SKU-001",
        "Nome/Descrição": "Película 3D",
        "Categoria": "Películas",
        "Marca": "",
        "Modelo compatível": "iPhone 15",
        "Quantidade": 10,
        "Custo": 5.0,
        "Preço de venda": 15.0,
        "Fornecedor": "Fornecedor exemplo",
        "Estoque mínimo": 2,
        "Observação": "",
        "Status": "Ativo",
    }])
    output = BytesIO()
    sample.to_excel(output, index=False, sheet_name="Produtos")
    output.seek(0)
    return output.getvalue()


def _read_import_dataframe(file):
    try:
        return pd.read_excel(file, sheet_name="Produtos")
    except ValueError:
        return pd.read_excel(file)


def _normalize_import_rows(file):
    df = _read_import_dataframe(file)
    mapping = _column_map(df.columns)
    rows = []
    for index, raw in df.iterrows():
        row = {field: raw.get(source) if source else None for field, source in mapping.items()}
        normalized = {
            "linha": int(index) + 2,
            "codigo": normalize_text(row.get("codigo")),
            "produto": normalize_text(row.get("produto")),
            "categoria": normalize_text(row.get("categoria")),
            "marca": normalize_text(row.get("marca")),
            "modelo": normalize_text(row.get("modelo")),
            "quantidade": _to_float(row.get("quantidade"), 0),
            "custo": _to_float(row.get("custo"), 0),
            "valor_venda": _to_float(row.get("valor_venda"), 0),
            "fornecedor": normalize_text(row.get("fornecedor")),
            "estoque_minimo": _to_float(row.get("estoque_minimo"), 0),
            "observacao": normalize_text(row.get("observacao")),
            "ativo": _active_value(row.get("ativo")),
        }
        if not any(normalized.get(field) for field in ["codigo", "produto", "categoria", "marca", "modelo", "fornecedor", "observacao"]) and normalized["quantidade"] == 0 and normalized["valor_venda"] == 0:
            normalized["acao"] = "Ignorar"
            normalized["erro"] = "Linha vazia"
        else:
            normalized["acao"] = ""
            normalized["erro"] = ""
        rows.append(normalized)
    return rows


def _find_existing_product(cursor, row, quiosque_id):
    if row.get("codigo"):
        existing = cursor.execute("""
        SELECT id
        FROM estoque
        WHERE codigo = ? AND quiosque_id = ?
        LIMIT 1
        """, (row["codigo"], quiosque_id)).fetchone()
        if existing:
            return existing

    return cursor.execute("""
    SELECT id
    FROM estoque
    WHERE produto = ? AND COALESCE(modelo, '') = COALESCE(?, '')
      AND quiosque_id = ?
    LIMIT 1
    """, (row["produto"], row["modelo"], quiosque_id)).fetchone()


def preview_inventory_import(conn, file, user=None):
    rows = _normalize_import_rows(file)
    cursor = conn.cursor()
    quiosque_id = current_quiosque_id(user)
    summary = {"cadastrar": 0, "atualizar": 0, "ignorar": 0, "erro": 0}

    for row in rows:
        if row["acao"] == "Ignorar":
            summary["ignorar"] += 1
            continue
        errors = []
        if not row["produto"]:
            errors.append("Nome/Descrição é obrigatório")
        if row["quantidade"] < 0:
            errors.append("Quantidade não pode ser negativa")
        if row["custo"] < 0:
            errors.append("Custo não pode ser negativo")
        if row["valor_venda"] < 0:
            errors.append("Preço de venda não pode ser negativo")
        if row["estoque_minimo"] < 0:
            errors.append("Estoque mínimo não pode ser negativo")

        if errors:
            row["acao"] = "Erro"
            row["erro"] = "; ".join(errors)
            summary["erro"] += 1
            continue

        existing = _find_existing_product(cursor, row, quiosque_id)
        row["acao"] = "Atualizar" if existing else "Cadastrar"
        row["erro"] = ""
        summary["atualizar" if existing else "cadastrar"] += 1

    preview = pd.DataFrame(rows)
    return preview, summary


def apply_inventory_import(conn, preview_df, filename="", user=None):
    cursor = conn.cursor()
    quiosque_id = current_quiosque_id(user)
    summary = {"cadastrados": 0, "atualizados": 0, "ignorados": 0, "erros": 0}

    for row in preview_df.to_dict("records"):
        action = row.get("acao")
        if action == "Ignorar":
            summary["ignorados"] += 1
            continue
        if action == "Erro":
            summary["erros"] += 1
            continue

        existing = _find_existing_product(cursor, row, quiosque_id)
        params = (
            row.get("codigo") or "",
            row.get("produto") or "",
            row.get("categoria") or "",
            row.get("marca") or "",
            row.get("modelo") or "",
            float(row.get("quantidade") or 0),
            float(row.get("custo") or 0),
            float(row.get("valor_venda") or 0),
            row.get("fornecedor") or "",
            float(row.get("estoque_minimo") or 0),
            row.get("observacao") or "",
            int(row.get("ativo") or 1),
        )

        if existing:
            cursor.execute("""
            UPDATE estoque
            SET codigo = ?,
                produto = ?,
                categoria = ?,
                marca = ?,
                modelo = ?,
                quantidade = ?,
                custo = ?,
                valor_venda = ?,
                fornecedor = ?,
                estoque_minimo = ?,
                observacao = ?,
                ativo = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND quiosque_id = ?
            """, params + (existing[0], quiosque_id))
            summary["atualizados"] += 1
        else:
            cursor.execute("""
            INSERT INTO estoque (
                codigo,
                produto,
                categoria,
                marca,
                modelo,
                quantidade,
                custo,
                valor_venda,
                fornecedor,
                estoque_minimo,
                observacao,
                ativo,
                quiosque_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, params + (quiosque_id,))
            summary["cadastrados"] += 1

    cursor.execute("""
    INSERT INTO estoque_importacoes (
        usuario_id,
        usuario_nome,
        arquivo,
        cadastrados,
        atualizados,
        ignorados,
        erros,
        quiosque_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        None if not user else user.get("id"),
        None if not user else user.get("nome"),
        filename,
        summary["cadastrados"],
        summary["atualizados"],
        summary["ignorados"],
        summary["erros"],
        quiosque_id,
    ))
    conn.commit()
    return summary


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


def update_stock_product(
    conn,
    produto_id,
    produto,
    modelo,
    categoria,
    quantidade,
    valor_venda,
    estoque_minimo,
    observacao,
    codigo="",
    marca="",
    custo=0,
    fornecedor="",
):
    produto = normalize_text(produto)
    if not produto:
        raise ValueError("Informe o nome do produto.")

    quantidade = float(quantidade or 0)
    valor_venda = float(valor_venda or 0)
    estoque_minimo = float(estoque_minimo or 0)
    custo = float(custo or 0)
    if quantidade < 0 or valor_venda < 0 or estoque_minimo < 0 or custo < 0:
        raise ValueError("Quantidade, custo e valores não podem ser negativos.")

    cursor = conn.cursor()
    atual = cursor.execute(
        "SELECT quantidade FROM estoque WHERE id = ? AND quiosque_id = ?",
        (produto_id, current_quiosque_id()),
    ).fetchone()
    quantidade_anterior = float(atual[0] or 0) if atual else 0
    diferenca = quantidade - quantidade_anterior

    cursor.execute("""
    UPDATE estoque
    SET codigo = ?,
        produto = ?,
        modelo = ?,
        categoria = ?,
        marca = ?,
        quantidade = ?,
        custo = ?,
        valor_venda = ?,
        fornecedor = ?,
        estoque_minimo = ?,
        observacao = ?,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (
        normalize_text(codigo),
        produto,
        normalize_text(modelo),
        normalize_text(categoria),
        normalize_text(marca),
        quantidade,
        custo,
        valor_venda,
        normalize_text(fornecedor),
        estoque_minimo,
        normalize_text(observacao),
        produto_id,
        current_quiosque_id(),
    ))
    conn.commit()

    if diferenca != 0:
        register_stock_movement(
            conn,
            produto_id,
            "Ajuste",
            diferenca,
            "Edição de produto",
        )


def deactivate_stock_product(conn, produto_id):
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE estoque
    SET ativo = 0,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (produto_id, current_quiosque_id()))
    conn.commit()
