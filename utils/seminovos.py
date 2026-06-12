import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from database.database import execute_insert_returning_id
from utils.audit import log_action
from utils.dashboard_ui import moeda
from utils.permissions import has_permission
from utils.quiosques import current_quiosque_id, scope_clause


STATUS_COMPRA = [
    "Em avaliação",
    "Aguardando aprovação",
    "Aprovado para compra",
    "Compra concluída",
    "Recusado",
    "Em estoque",
    "Vendido",
]

STATUS_SEMINOVO = ["Disponível", "Reservado", "Vendido"]

CHECKLIST_ITEMS = [
    "Tela",
    "Touch",
    "Face ID / Biometria",
    "Câmera frontal",
    "Câmera traseira",
    "Alto-falante",
    "Microfone",
    "Wi-Fi",
    "Bluetooth",
    "Chip / rede",
    "Bateria",
    "Conector de carga",
    "Botões",
    "Carcaça",
    "Tampa traseira",
    "iCloud / Conta Google removida",
    "Aparelho restaurado",
    "IMEI conferido",
    "Observações",
]

CHECKLIST_OPTIONS = ["OK", "Com defeito", "Não testado", "Não se aplica", "Trocada"]

ANEXO_TIPOS = [
    "Foto frente",
    "Foto verso",
    "Foto IMEI",
    "Documento do vendedor",
    "Assinatura",
    "PDF termo assinado",
    "Outro",
]


def _user_label(user):
    return "Sistema" if not user else user.get("nome") or user.get("usuario") or "Usuário"


def _json_details(value):
    return json.dumps(value or {}, ensure_ascii=False)


def _history(conn, aparelho_id, user, acao, detalhes=None, quiosque_id=None):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO aparelho_historico (
            aparelho_id, usuario_id, usuario_nome, acao, detalhes, quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            int(aparelho_id),
            None if not user else user.get("id"),
            _user_label(user),
            acao,
            _json_details(detalhes),
            int(quiosque_id or current_quiosque_id(user)),
        ),
    )
    conn.commit()


def can_view_internal_costs(user=None):
    return has_permission("view_profit", user)


def create_device_purchase(conn, data, user):
    quiosque_id = int(data.get("quiosque_id") or current_quiosque_id(user))
    cursor = conn.cursor()
    aparelho_id = execute_insert_returning_id(
        conn,
        cursor,
        """
        INSERT INTO aparelho_compras (
            cliente, cpf, telefone, documento, imei, marca, modelo, cor, capacidade,
            estado_fisico, observacoes, data_entrada, valor_sugerido, valor_final,
            forma_pagamento, status, atendente_id, atendente_nome, quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("cliente"),
            data.get("cpf"),
            data.get("telefone"),
            data.get("documento"),
            data.get("imei"),
            data.get("marca"),
            data.get("modelo"),
            data.get("cor"),
            data.get("capacidade"),
            data.get("estado_fisico"),
            data.get("observacoes"),
            str(data.get("data_entrada") or datetime.today().date()),
            float(data.get("valor_sugerido") or 0),
            float(data.get("valor_final") or 0),
            data.get("forma_pagamento"),
            data.get("status") or "Em avaliação",
            None if not user else user.get("id"),
            _user_label(user),
            quiosque_id,
        ),
    )
    _history(conn, aparelho_id, user, "criou_avaliacao", data, quiosque_id)
    log_action(conn, user, "criou_avaliacao_aparelho", "aparelho_compras", aparelho_id, data)
    return aparelho_id


def load_device_purchases(conn, status=None, search="", limit=200):
    scope, params = scope_clause("a", prefix="AND")
    filters = ["1 = 1"]
    query_params = []
    if status and status != "Todos":
        filters.append("a.status = ?")
        query_params.append(status)
    if search.strip():
        filters.append(
            """
            LOWER(COALESCE(a.cliente, '') || ' ' || COALESCE(a.cpf, '') || ' ' ||
                  COALESCE(a.telefone, '') || ' ' || COALESCE(a.imei, '') || ' ' ||
                  COALESCE(a.marca, '') || ' ' || COALESCE(a.modelo, '')) LIKE ?
            """
        )
        query_params.append(f"%{search.strip().lower()}%")

    return pd.read_sql_query(
        f"""
        SELECT a.*, q.nome AS quiosque_nome
        FROM aparelho_compras a
        LEFT JOIN quiosques q ON q.id = a.quiosque_id
        WHERE {' AND '.join(filters)}
        {scope}
        ORDER BY a.id DESC
        LIMIT ?
        """,
        conn,
        params=tuple(query_params) + params + (int(limit),),
    )


def get_device_purchase(conn, aparelho_id):
    df = pd.read_sql_query(
        """
        SELECT a.*, q.nome AS quiosque_nome
        FROM aparelho_compras a
        LEFT JOIN quiosques q ON q.id = a.quiosque_id
        WHERE a.id = ?
        LIMIT 1
        """,
        conn,
        params=(int(aparelho_id),),
    )
    return None if df.empty else df.iloc[0].to_dict()


def update_device_status(conn, aparelho_id, status, user):
    aparelho = get_device_purchase(conn, aparelho_id)
    if not aparelho:
        raise ValueError("Aparelho não encontrado.")

    cursor = conn.cursor()
    extra = ""
    params = [status]
    if status == "Aprovado para compra":
        extra = ", aprovado_por_id = ?, aprovado_por_nome = ?"
        params.extend([None if not user else user.get("id"), _user_label(user)])
    elif status in {"Compra concluída", "Em estoque"}:
        extra = ", concluido_por_id = ?, concluido_por_nome = ?"
        params.extend([None if not user else user.get("id"), _user_label(user)])

    cursor.execute(
        f"""
        UPDATE aparelho_compras
        SET status = ?, atualizado_em = CURRENT_TIMESTAMP {extra}
        WHERE id = ?
        """,
        tuple(params + [int(aparelho_id)]),
    )
    conn.commit()
    _history(conn, aparelho_id, user, "alterou_status", {"status": status}, aparelho.get("quiosque_id"))
    log_action(conn, user, "alterou_status_aparelho", "aparelho_compras", aparelho_id, {"status": status})

    if status in {"Compra concluída", "Em estoque"}:
        ensure_preowned_stock(conn, aparelho_id, user)


def load_checklist(conn, aparelho_id, etapa):
    return pd.read_sql_query(
        """
        SELECT item, valor, observacao
        FROM aparelho_checklists
        WHERE aparelho_id = ? AND etapa = ?
        ORDER BY id
        """,
        conn,
        params=(int(aparelho_id), etapa),
    )


def checklist_dict(conn, aparelho_id, etapa):
    df = load_checklist(conn, aparelho_id, etapa)
    data = {item: {"valor": "Não testado", "observacao": ""} for item in CHECKLIST_ITEMS}
    for row in df.itertuples():
        data[row.item] = {"valor": row.valor or "Não testado", "observacao": row.observacao or ""}
    return data


def save_checklist(conn, aparelho_id, etapa, checklist, user):
    aparelho = get_device_purchase(conn, aparelho_id)
    if not aparelho:
        raise ValueError("Aparelho não encontrado.")

    quiosque_id = int(aparelho.get("quiosque_id") or current_quiosque_id(user))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM aparelho_checklists WHERE aparelho_id = ? AND etapa = ?", (int(aparelho_id), etapa))
    for item, values in checklist.items():
        cursor.execute(
            """
            INSERT INTO aparelho_checklists (
                aparelho_id, etapa, item, valor, observacao, usuario_id, usuario_nome, quiosque_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(aparelho_id),
                etapa,
                item,
                values.get("valor"),
                values.get("observacao"),
                None if not user else user.get("id"),
                _user_label(user),
                quiosque_id,
            ),
        )
    conn.commit()
    _history(conn, aparelho_id, user, f"salvou_checklist_{etapa}", {"itens": len(checklist)}, quiosque_id)
    log_action(conn, user, f"salvou_checklist_{etapa}", "aparelho_compras", aparelho_id, {"itens": len(checklist)})


def checklist_comparison(conn, aparelho_id):
    entrada = checklist_dict(conn, aparelho_id, "entrada")
    saida = checklist_dict(conn, aparelho_id, "saida")
    rows = []
    for item in CHECKLIST_ITEMS:
        entrada_valor = entrada[item]["valor"]
        saida_valor = saida[item]["valor"]
        rows.append(
            {
                "Item": item,
                "Entrada": entrada_valor,
                "Saída": saida_valor,
                "Diferença": "Alterado" if entrada_valor != saida_valor else "Sem mudança",
                "Obs. Entrada": entrada[item].get("observacao", ""),
                "Obs. Saída": saida[item].get("observacao", ""),
            }
        )
    return pd.DataFrame(rows)


def ensure_exit_checklist_from_entry(conn, aparelho_id, user):
    current = load_checklist(conn, aparelho_id, "saida")
    if not current.empty:
        return
    entrada = checklist_dict(conn, aparelho_id, "entrada")
    save_checklist(conn, aparelho_id, "saida", entrada, user)


def generate_purchase_term_html(aparelho, user):
    return f"""
    <html>
    <head><meta charset="utf-8"><title>Termo de Compra #{aparelho.get('id')}</title></head>
    <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.45;">
        <h1>Hospital do Celular - Termo de Compra de Aparelho</h1>
        <p><strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <h2>Dados do vendedor</h2>
        <p><strong>Nome:</strong> {aparelho.get('cliente') or ''}</p>
        <p><strong>CPF:</strong> {aparelho.get('cpf') or ''} | <strong>Telefone:</strong> {aparelho.get('telefone') or ''}</p>
        <h2>Dados do aparelho</h2>
        <p><strong>IMEI:</strong> {aparelho.get('imei') or ''}</p>
        <p><strong>Marca/Modelo:</strong> {aparelho.get('marca') or ''} {aparelho.get('modelo') or ''}</p>
        <p><strong>Cor/Capacidade:</strong> {aparelho.get('cor') or ''} {aparelho.get('capacidade') or ''}</p>
        <p><strong>Valor final:</strong> {moeda(aparelho.get('valor_final'))} | <strong>Pagamento:</strong> {aparelho.get('forma_pagamento') or ''}</p>
        <h2>Declarações</h2>
        <p>O vendedor declara ser legítimo proprietário do aparelho, confirmando sua procedência legal e ausência de bloqueios, restrições, furto, roubo ou financiamento impeditivo.</p>
        <p>O vendedor autoriza a restauração do aparelho e a exclusão de dados, contas, senhas, iCloud ou Conta Google, quando aplicável.</p>
        <p>O responsável pela avaliação confirma que o aparelho foi recebido conforme checklist técnico vinculado ao cadastro.</p>
        <br><br>
        <p>_____________________________________<br>Assinatura do vendedor</p>
        <br>
        <p>_____________________________________<br>Responsável pela avaliação: {_user_label(user)}</p>
    </body>
    </html>
    """


def save_purchase_term(conn, aparelho_id, user):
    aparelho = get_device_purchase(conn, aparelho_id)
    if not aparelho:
        raise ValueError("Aparelho não encontrado.")
    html = generate_purchase_term_html(aparelho, user)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE aparelho_compras
        SET termo_html = ?, termo_gerado_em = CURRENT_TIMESTAMP, atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (html, int(aparelho_id)),
    )
    conn.commit()
    _history(conn, aparelho_id, user, "gerou_termo_compra", {}, aparelho.get("quiosque_id"))
    log_action(conn, user, "gerou_termo_compra", "aparelho_compras", aparelho_id, {})
    return html


def save_attachment(conn, aparelho_id, uploaded_file, tipo, user):
    aparelho = get_device_purchase(conn, aparelho_id)
    if not aparelho:
        raise ValueError("Aparelho não encontrado.")
    upload_dir = Path("uploads") / "seminovos" / str(aparelho_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
    path.write_bytes(uploaded_file.getbuffer())

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO aparelho_anexos (
            aparelho_id, tipo, nome_arquivo, caminho, mime_type, usuario_id, usuario_nome, quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(aparelho_id),
            tipo,
            safe_name,
            str(path),
            uploaded_file.type,
            None if not user else user.get("id"),
            _user_label(user),
            int(aparelho.get("quiosque_id") or current_quiosque_id(user)),
        ),
    )
    conn.commit()
    _history(conn, aparelho_id, user, "anexou_arquivo", {"tipo": tipo, "arquivo": safe_name}, aparelho.get("quiosque_id"))
    log_action(conn, user, "anexou_arquivo_aparelho", "aparelho_compras", aparelho_id, {"tipo": tipo, "arquivo": safe_name})


def load_attachments(conn, aparelho_id):
    return pd.read_sql_query(
        """
        SELECT *
        FROM aparelho_anexos
        WHERE aparelho_id = ?
        ORDER BY id DESC
        """,
        conn,
        params=(int(aparelho_id),),
    )


def load_history(conn, aparelho_id):
    return pd.read_sql_query(
        """
        SELECT data_hora, usuario_nome, acao, detalhes
        FROM aparelho_historico
        WHERE aparelho_id = ?
        ORDER BY data_hora DESC, id DESC
        LIMIT 100
        """,
        conn,
        params=(int(aparelho_id),),
    )


def ensure_preowned_stock(conn, aparelho_id, user):
    aparelho = get_device_purchase(conn, aparelho_id)
    if not aparelho:
        raise ValueError("Aparelho não encontrado.")

    exists = pd.read_sql_query(
        "SELECT id FROM seminovos_estoque WHERE aparelho_id = ? LIMIT 1",
        conn,
        params=(int(aparelho_id),),
    )
    custo_compra = float(aparelho.get("valor_final") or 0)
    valor_venda = round(custo_compra * 1.25, 2) if custo_compra else 0
    quiosque_id = int(aparelho.get("quiosque_id") or current_quiosque_id(user))
    if not exists.empty:
        return int(exists.iloc[0]["id"])

    codigo = f"SN-{int(aparelho_id):05d}"
    cursor = conn.cursor()
    seminovo_id = execute_insert_returning_id(
        conn,
        cursor,
        """
        INSERT INTO seminovos_estoque (
            aparelho_id, codigo_interno, imei, modelo, cor, capacidade, custo_compra,
            custo_reparo, custo_total, valor_venda, lucro_estimado, status, quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(aparelho_id),
            codigo,
            aparelho.get("imei"),
            aparelho.get("modelo"),
            aparelho.get("cor"),
            aparelho.get("capacidade"),
            custo_compra,
            0,
            custo_compra,
            valor_venda,
            valor_venda - custo_compra,
            "Disponível",
            quiosque_id,
        ),
    )
    cursor.execute(
        "UPDATE aparelho_compras SET status = 'Em estoque', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
        (int(aparelho_id),),
    )
    conn.commit()
    _history(conn, aparelho_id, user, "entrou_estoque_seminovo", {"codigo": codigo}, quiosque_id)
    log_action(conn, user, "criou_estoque_seminovo", "seminovos_estoque", seminovo_id, {"aparelho_id": aparelho_id})
    return seminovo_id


def load_preowned_stock(conn, status=None, limit=200):
    scope, params = scope_clause("s", prefix="AND")
    filters = ["1 = 1"]
    query_params = []
    if status and status != "Todos":
        filters.append("s.status = ?")
        query_params.append(status)
    return pd.read_sql_query(
        f"""
        SELECT s.*, a.cliente, q.nome AS quiosque_nome
        FROM seminovos_estoque s
        LEFT JOIN aparelho_compras a ON a.id = s.aparelho_id
        LEFT JOIN quiosques q ON q.id = s.quiosque_id
        WHERE {' AND '.join(filters)}
        {scope}
        ORDER BY s.id DESC
        LIMIT ?
        """,
        conn,
        params=tuple(query_params) + params + (int(limit),),
    )


def update_preowned_stock(conn, seminovo_id, custo_reparo, valor_venda, status, comprador, user):
    row = pd.read_sql_query("SELECT * FROM seminovos_estoque WHERE id = ?", conn, params=(int(seminovo_id),))
    if row.empty:
        raise ValueError("Seminovo não encontrado.")
    item = row.iloc[0]
    custo_compra = float(item.get("custo_compra") or 0)
    custo_total = custo_compra + float(custo_reparo or 0)
    lucro = float(valor_venda or 0) - custo_total
    vendido_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "Vendido" else item.get("vendido_em")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE seminovos_estoque
        SET custo_reparo = ?, custo_total = ?, valor_venda = ?, lucro_estimado = ?,
            status = ?, comprador = ?, vendido_em = ?, atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (float(custo_reparo or 0), custo_total, float(valor_venda or 0), lucro, status, comprador, vendido_em, int(seminovo_id)),
    )
    if status == "Vendido":
        cursor.execute("UPDATE aparelho_compras SET status = 'Vendido', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?", (int(item["aparelho_id"]),))
    conn.commit()
    _history(conn, int(item["aparelho_id"]), user, "atualizou_estoque_seminovo", {"status": status}, item.get("quiosque_id"))
    log_action(
        conn,
        user,
        "atualizou_estoque_seminovo",
        "seminovos_estoque",
        seminovo_id,
        {"status": status, "valor_venda": valor_venda, "custo_reparo": custo_reparo},
    )
