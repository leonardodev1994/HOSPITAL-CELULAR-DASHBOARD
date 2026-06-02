import pandas as pd


MARCAS_PADRAO = ["Samsung", "Motorola", "Xiaomi", "iPhone", "LG", "Realme", "Infinix", "Asus", "Outras"]


def preco_sugerido(custo):
    custo = float(custo or 0)
    if custo <= 0:
        return 0.0
    return max(custo * 2, custo + 100)


def lucro_estimado(custo):
    custo = float(custo or 0)
    return preco_sugerido(custo) - custo if custo > 0 else 0.0


def load_catalog_items(conn, search="", marca="", limit=80):
    filters = ["ativo = 1"]
    params = []
    if search.strip():
        term = f"%{search.strip()}%"
        filters.append("(modelo LIKE ? OR marca LIKE ? OR qualidade LIKE ?)")
        params.extend([term, term, term])
    if marca and marca != "Outras":
        filters.append("marca = ?")
        params.append(marca)
    elif marca == "Outras":
        filters.append("(marca IS NULL OR marca = '' OR marca NOT IN (?, ?, ?, ?, ?, ?, ?, ?))")
        params.extend(MARCAS_PADRAO[:-1])

    query = """
    SELECT
        id,
        marca,
        modelo,
        qualidade,
        custo_sem_aro,
        custo_com_aro,
        observacao
    FROM catalogo_pecas
    WHERE """ + " AND ".join(filters) + """
    ORDER BY marca, modelo, qualidade
    LIMIT ?
    """
    return pd.read_sql_query(query, conn, params=tuple(params) + (int(limit),))


def count_catalog_items(conn):
    return pd.read_sql_query(
        "SELECT marca, COUNT(*) AS total FROM catalogo_pecas WHERE ativo = 1 GROUP BY marca",
        conn,
    )


def create_catalog_item(conn, marca, modelo, qualidade, custo_sem_aro, custo_com_aro, observacao=""):
    if not str(modelo or "").strip():
        raise ValueError("Informe o modelo.")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO catalogo_pecas (
        marca,
        modelo,
        qualidade,
        custo_sem_aro,
        custo_com_aro,
        observacao
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(marca or "").strip(),
        str(modelo or "").strip(),
        str(qualidade or "").strip(),
        float(custo_sem_aro or 0),
        float(custo_com_aro or 0),
        str(observacao or "").strip(),
    ))
    conn.commit()


def deactivate_catalog_item(conn, item_id):
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE catalogo_pecas
    SET ativo = 0,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (int(item_id),))
    conn.commit()


def enrich_catalog_df(df):
    if df.empty:
        return df
    result = df.copy()
    result["venda_sem_aro"] = result["custo_sem_aro"].map(preco_sugerido)
    result["lucro_sem_aro"] = result["venda_sem_aro"] - result["custo_sem_aro"].fillna(0)
    result["venda_com_aro"] = result["custo_com_aro"].map(preco_sugerido)
    result["lucro_com_aro"] = result["venda_com_aro"] - result["custo_com_aro"].fillna(0)
    return result
