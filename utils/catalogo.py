from io import BytesIO
import re
import unicodedata

import pandas as pd


MARCAS_PADRAO = ["Samsung", "Motorola", "Xiaomi", "iPhone", "LG", "Realme", "Infinix", "Asus", "Outras"]

CATALOG_IMPORT_COLUMNS = [
    "Marca",
    "Modelo",
    "Qualidade",
    "Custo S/A",
    "Venda S/A",
    "Lucro S/A",
    "Custo C/A",
    "Venda C/A",
    "Lucro C/A",
]

_CATALOG_COLUMN_MAP = {
    "marca": "Marca",
    "modelo": "Modelo",
    "qualidade": "Qualidade",
    "custosa": "Custo S/A",
    "custosemaro": "Custo S/A",
    "vendasa": "Venda S/A",
    "vendasemaro": "Venda S/A",
    "precosa": "Venda S/A",
    "precosemaro": "Venda S/A",
    "valorsa": "Venda S/A",
    "valorsemaro": "Venda S/A",
    "lucrosa": "Lucro S/A",
    "lucrosemaro": "Lucro S/A",
    "custoca": "Custo C/A",
    "custocomaro": "Custo C/A",
    "vendaca": "Venda C/A",
    "vendacomaro": "Venda C/A",
    "precoca": "Venda C/A",
    "precocomaro": "Venda C/A",
    "valorca": "Venda C/A",
    "valorcomaro": "Venda C/A",
    "lucroca": "Lucro C/A",
    "lucrocomaro": "Lucro C/A",
}


def _normalize_column_name(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.strip().lower())


def _catalog_column_from_name(column):
    normalized = _normalize_column_name(column)
    if normalized in _CATALOG_COLUMN_MAP:
        return _CATALOG_COLUMN_MAP[normalized]

    if normalized in {"sa", "semaro"}:
        return "Custo S/A"
    if normalized in {"ca", "comaro"}:
        return "Custo C/A"

    is_cost = any(token in normalized for token in ["custo", "cost"])
    is_sale = any(token in normalized for token in ["venda", "preco", "price", "valor"])
    is_profit = any(token in normalized for token in ["lucro", "profit", "margem"])
    is_without_frame = "sa" in normalized or "semaro" in normalized
    is_with_frame = "ca" in normalized or "comaro" in normalized

    if is_cost and is_without_frame:
        return "Custo S/A"
    if is_sale and is_without_frame:
        return "Venda S/A"
    if is_profit and is_without_frame:
        return "Lucro S/A"
    if is_cost and is_with_frame:
        return "Custo C/A"
    if is_sale and is_with_frame:
        return "Venda C/A"
    if is_profit and is_with_frame:
        return "Lucro C/A"

    return None


def _cell_to_text(value):
    if pd.isna(value):
        return ""
    return str(value or "").strip()


def _normalize_key(marca, modelo, qualidade):
    return (
        str(marca or "").strip().casefold(),
        str(modelo or "").strip().casefold(),
        str(qualidade or "").strip().casefold(),
    )


def _money_to_float(value):
    if pd.isna(value) or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    text = (
        text.replace("R$", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
    )
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return 0.0

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif "." in text:
        integer_part, decimal_part = text.rsplit(".", 1)
        if len(decimal_part) == 3 and integer_part.replace("-", "").isdigit():
            text = integer_part + decimal_part

    return float(text)


def _infer_cost(cost, sale, profit):
    cost = float(cost or 0)
    sale = float(sale or 0)
    profit = float(profit or 0)
    if cost > 0:
        return cost
    if sale > 0 and profit > 0:
        inferred = sale - profit
        return inferred if inferred > 0 else 0.0
    return 0.0


def _resolve_price_set(cost, sale, profit):
    cost = _infer_cost(cost, sale, profit)
    sale = float(sale or 0)
    profit = float(profit or 0)

    if cost > 0:
        suggested_sale = preco_sugerido(cost)
        return cost, suggested_sale, suggested_sale - cost

    if sale > 0:
        return 0.0, sale, profit if profit > 0 else 0.0

    return 0.0, 0.0, 0.0


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
        venda_sem_aro,
        lucro_sem_aro,
        custo_com_aro,
        venda_com_aro,
        lucro_com_aro,
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
    venda_sem_aro = preco_sugerido(custo_sem_aro)
    lucro_sem_aro = lucro_estimado(custo_sem_aro)
    venda_com_aro = preco_sugerido(custo_com_aro)
    lucro_com_aro = lucro_estimado(custo_com_aro)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO catalogo_pecas (
        marca,
        modelo,
        qualidade,
        custo_sem_aro,
        venda_sem_aro,
        lucro_sem_aro,
        custo_com_aro,
        venda_com_aro,
        lucro_com_aro,
        observacao
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(marca or "").strip(),
        str(modelo or "").strip(),
        str(qualidade or "").strip(),
        float(custo_sem_aro or 0),
        venda_sem_aro,
        lucro_sem_aro,
        float(custo_com_aro or 0),
        venda_com_aro,
        lucro_com_aro,
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


def catalog_import_template_excel():
    sample = pd.DataFrame([{
        "Marca": "iPhone",
        "Modelo": "iPhone 11",
        "Qualidade": "INCELL",
        "Custo S/A": 120.0,
        "Venda S/A": preco_sugerido(120.0),
        "Lucro S/A": lucro_estimado(120.0),
        "Custo C/A": 180.0,
        "Venda C/A": preco_sugerido(180.0),
        "Lucro C/A": lucro_estimado(180.0),
    }])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="Catalogo")
    output.seek(0)
    return output.getvalue()


def _read_catalog_import_excel(uploaded_file):
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    df = df.dropna(how="all")

    rename_map = {}
    for column in df.columns:
        canonical = _catalog_column_from_name(column)
        if canonical:
            rename_map[column] = canonical

    df = df.rename(columns=rename_map)
    df = df.loc[:, [column in CATALOG_IMPORT_COLUMNS for column in df.columns]]
    if df.columns.duplicated().any():
        collapsed = pd.DataFrame(index=df.index)
        for column in CATALOG_IMPORT_COLUMNS:
            matches = df.loc[:, df.columns == column]
            if matches.empty:
                continue
            collapsed[column] = matches.bfill(axis=1).iloc[:, 0]
        df = collapsed

    missing = [column for column in ["Marca", "Modelo", "Qualidade"] if column not in df.columns]
    if missing:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(missing))

    for column in CATALOG_IMPORT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df[CATALOG_IMPORT_COLUMNS].copy()


def _existing_catalog_keys(conn):
    existing = pd.read_sql_query(
        """
        SELECT id, marca, modelo, qualidade
        FROM catalogo_pecas
        """,
        conn,
    )
    if existing.empty:
        return {}

    return {
        _normalize_key(row.marca, row.modelo, row.qualidade): int(row.id)
        for row in existing.itertuples()
    }


def preview_catalog_import(conn, uploaded_file):
    df = _read_catalog_import_excel(uploaded_file)
    existing = _existing_catalog_keys(conn)
    seen = set()
    rows = []
    summary = {"cadastrar": 0, "atualizar": 0, "ignorar": 0, "erro": 0}

    for index, row in df.iterrows():
        line_number = int(index) + 2
        marca = _cell_to_text(row.get("Marca"))
        modelo = _cell_to_text(row.get("Modelo"))
        qualidade = _cell_to_text(row.get("Qualidade"))
        erro = ""

        if not modelo:
            erro = "Informe o modelo."

        try:
            custo_sem_aro, venda_sem_aro, lucro_sem_aro = _resolve_price_set(
                _money_to_float(row.get("Custo S/A")),
                _money_to_float(row.get("Venda S/A")),
                _money_to_float(row.get("Lucro S/A")),
            )
            custo_com_aro, venda_com_aro, lucro_com_aro = _resolve_price_set(
                _money_to_float(row.get("Custo C/A")),
                _money_to_float(row.get("Venda C/A")),
                _money_to_float(row.get("Lucro C/A")),
            )
        except Exception:
            custo_sem_aro = 0.0
            venda_sem_aro = 0.0
            lucro_sem_aro = 0.0
            custo_com_aro = 0.0
            venda_com_aro = 0.0
            lucro_com_aro = 0.0
            erro = "Custo inválido."

        if custo_sem_aro < 0 or custo_com_aro < 0:
            erro = "Custo não pode ser negativo."

        key = _normalize_key(marca, modelo, qualidade)
        if key == ("", "", ""):
            action = "ignorar"
            summary["ignorar"] += 1
        elif erro:
            action = "erro"
            summary["erro"] += 1
        elif key in seen:
            action = "erro"
            erro = "Duplicado na planilha."
            summary["erro"] += 1
        elif key in existing:
            action = "atualizar"
            summary["atualizar"] += 1
        else:
            action = "cadastrar"
            summary["cadastrar"] += 1

        if action not in {"ignorar", "erro"}:
            seen.add(key)

        rows.append({
            "linha": line_number,
            "acao": action,
            "id_existente": existing.get(key),
            "marca": marca,
            "modelo": modelo,
            "qualidade": qualidade,
            "custo_sem_aro": custo_sem_aro,
            "venda_sem_aro": venda_sem_aro,
            "lucro_sem_aro": lucro_sem_aro,
            "custo_com_aro": custo_com_aro,
            "venda_com_aro": venda_com_aro,
            "lucro_com_aro": lucro_com_aro,
            "erro": erro,
        })

    return pd.DataFrame(rows), summary


def apply_catalog_import(conn, preview_df, filename="", user=None):
    cursor = conn.cursor()
    result = {"cadastrados": 0, "atualizados": 0, "ignorados": 0}
    user_name = (user or {}).get("usuario") or (user or {}).get("nome") or "sistema"
    observation = f"Importado da planilha {filename} por {user_name}".strip()

    for row in preview_df.itertuples():
        if row.acao == "ignorar":
            result["ignorados"] += 1
            continue
        if row.acao == "erro":
            continue

        if row.acao == "atualizar" and getattr(row, "id_existente", None):
            cursor.execute("""
            UPDATE catalogo_pecas
            SET marca = ?,
                modelo = ?,
                qualidade = ?,
                custo_sem_aro = ?,
                venda_sem_aro = ?,
                lucro_sem_aro = ?,
                custo_com_aro = ?,
                venda_com_aro = ?,
                lucro_com_aro = ?,
                observacao = ?,
                ativo = 1,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (
                row.marca,
                row.modelo,
                row.qualidade,
                float(row.custo_sem_aro or 0),
                float(row.venda_sem_aro or 0),
                float(row.lucro_sem_aro or 0),
                float(row.custo_com_aro or 0),
                float(row.venda_com_aro or 0),
                float(row.lucro_com_aro or 0),
                observation,
                int(row.id_existente),
            ))
            result["atualizados"] += 1
            continue

        cursor.execute("""
        INSERT INTO catalogo_pecas (
            marca,
            modelo,
            qualidade,
            custo_sem_aro,
            venda_sem_aro,
            lucro_sem_aro,
            custo_com_aro,
            venda_com_aro,
            lucro_com_aro,
            observacao
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.marca,
            row.modelo,
            row.qualidade,
            float(row.custo_sem_aro or 0),
            float(row.venda_sem_aro or 0),
            float(row.lucro_sem_aro or 0),
            float(row.custo_com_aro or 0),
            float(row.venda_com_aro or 0),
            float(row.lucro_com_aro or 0),
            observation,
        ))
        result["cadastrados"] += 1

    conn.commit()
    return result


def enrich_catalog_df(df):
    if df.empty:
        return df
    result = df.copy()
    for column in [
        "custo_sem_aro",
        "venda_sem_aro",
        "lucro_sem_aro",
        "custo_com_aro",
        "venda_com_aro",
        "lucro_com_aro",
    ]:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)

    calculated_sale_without_frame = result["custo_sem_aro"].map(preco_sugerido)
    result["venda_sem_aro"] = result["venda_sem_aro"].where(result["venda_sem_aro"] > 0, calculated_sale_without_frame)
    result["lucro_sem_aro"] = result["lucro_sem_aro"].where(
        result["lucro_sem_aro"] > 0,
        result["venda_sem_aro"] - result["custo_sem_aro"],
    )

    calculated_sale_with_frame = result["custo_com_aro"].map(preco_sugerido)
    result["venda_com_aro"] = result["venda_com_aro"].where(result["venda_com_aro"] > 0, calculated_sale_with_frame)
    result["lucro_com_aro"] = result["lucro_com_aro"].where(
        result["lucro_com_aro"] > 0,
        result["venda_com_aro"] - result["custo_com_aro"],
    )
    return result
