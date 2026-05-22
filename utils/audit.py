import json


def log_action(conn, user, acao, entidade, entidade_id=None, detalhes=None):
    cursor = conn.cursor()
    detalhes_texto = json.dumps(detalhes or {}, ensure_ascii=False)

    cursor.execute("""
    INSERT INTO auditoria (
        usuario_id,
        usuario_nome,
        acao,
        entidade,
        entidade_id,
        detalhes
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        None if not user else user.get("id"),
        "Sistema" if not user else user.get("nome"),
        acao,
        entidade,
        entidade_id,
        detalhes_texto,
    ))
    conn.commit()
