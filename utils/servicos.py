import pandas as pd

from utils.quiosques import current_quiosque_id, scope_clause


def normalize_text(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def servico_label(row):
    if hasattr(row, "get"):
        nome = row.get("nome")
        modelo = row.get("modelo")
    else:
        nome = getattr(row, "nome", "")
        modelo = getattr(row, "modelo", "")

    nome = normalize_text(nome)
    modelo = normalize_text(modelo)
    return f"{nome} - {modelo}" if modelo else nome


def load_services(conn, only_active=True, limit=500):
    scope, params = scope_clause("s")
    query = """
    SELECT
        s.*,
        q.nome AS quiosque_nome
    FROM servicos s
    LEFT JOIN quiosques q ON q.id = s.quiosque_id
    """
    if only_active:
        query += " WHERE s.ativo = 1"
        if scope:
            query += scope.replace(" WHERE ", " AND ")
    else:
        query += scope
    query += " ORDER BY s.categoria, s.nome, s.modelo LIMIT ?"
    return pd.read_sql_query(query, conn, params=params + (int(limit),))


def create_service(
    conn,
    nome,
    categoria="",
    modelo="",
    valor_padrao=0,
    custo_estimado=0,
    tempo_estimado="",
    garantia="",
    observacao="",
):
    nome = normalize_text(nome)
    if not nome:
        raise ValueError("Informe o nome do serviço.")

    valor_padrao = float(valor_padrao or 0)
    custo_estimado = float(custo_estimado or 0)
    if valor_padrao < 0 or custo_estimado < 0:
        raise ValueError("Valores não podem ser negativos.")

    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO servicos (
        nome,
        categoria,
        modelo,
        valor_padrao,
        custo_estimado,
        tempo_estimado,
        garantia,
        observacao,
        ativo,
        quiosque_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nome,
        normalize_text(categoria),
        normalize_text(modelo),
        valor_padrao,
        custo_estimado,
        normalize_text(tempo_estimado),
        normalize_text(garantia),
        normalize_text(observacao),
        1,
        current_quiosque_id(),
    ))
    conn.commit()


def update_service(
    conn,
    service_id,
    nome,
    categoria,
    modelo,
    valor_padrao,
    custo_estimado,
    tempo_estimado,
    garantia,
    observacao,
):
    nome = normalize_text(nome)
    if not nome:
        raise ValueError("Informe o nome do serviço.")

    valor_padrao = float(valor_padrao or 0)
    custo_estimado = float(custo_estimado or 0)
    if valor_padrao < 0 or custo_estimado < 0:
        raise ValueError("Valores não podem ser negativos.")

    cursor = conn.cursor()
    cursor.execute("""
    UPDATE servicos
    SET nome = ?,
        categoria = ?,
        modelo = ?,
        valor_padrao = ?,
        custo_estimado = ?,
        tempo_estimado = ?,
        garantia = ?,
        observacao = ?,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (
        nome,
        normalize_text(categoria),
        normalize_text(modelo),
        valor_padrao,
        custo_estimado,
        normalize_text(tempo_estimado),
        normalize_text(garantia),
        normalize_text(observacao),
        int(service_id),
        current_quiosque_id(),
    ))
    conn.commit()


def deactivate_service(conn, service_id):
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE servicos
    SET ativo = 0,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (int(service_id), current_quiosque_id()))
    conn.commit()
