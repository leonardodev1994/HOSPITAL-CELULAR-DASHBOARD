import base64
import csv
import json
import mimetypes
import os
import re
import unicodedata
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from urllib import error, request

import pandas as pd
import streamlit as st

from database.database import ensure_supplier_purchase_schema
from utils.audit import log_action
from utils.auth import current_user
from utils.quiosques import current_quiosque_id, scope_clause


SUPPLIER_PURCHASE_COLUMNS = [
    "data_compra",
    "fornecedor",
    "tipo",
    "modelo",
    "aro",
    "tecnologia",
    "valor",
    "observacao",
    "status_pagamento",
    "valor_pago",
    "data_pagamento",
]

SUPPLIER_PURCHASE_LABELS = {
    "data_compra": "Data",
    "fornecedor": "Fornecedor",
    "tipo": "Tipo",
    "modelo": "Modelo",
    "aro": "Aro",
    "tecnologia": "Tecnologia",
    "valor": "Valor",
    "observacao": "Observação",
    "status_pagamento": "Status pagamento",
    "valor_pago": "Valor pago",
    "data_pagamento": "Data pagamento",
}

PAYMENT_STATUSES = ["Em aberto", "Parcial", "Pago"]
DEFAULT_TYPE_OPTIONS = ["Frontal", "Bateria", "Dock", "Tampa", "Lente", "Flex", "Carcaça", "Câmera", "Conector", "Outro"]
DEFAULT_ARO_OPTIONS = ["Sem Aro", "Com Aro", "Não informado"]
DEFAULT_TECH_OPTIONS = ["Incell", "OLED", "Original", "Compatível", "Não informado"]


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_token(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-zA-Z0-9]+", "", text).upper()


def _clean_text(value):
    return str(value or "").strip()


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
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalize_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    text = _clean_text(value)
    if not text:
        return datetime.today().date().isoformat()

    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return datetime.today().date().isoformat()
    return parsed.date().isoformat()


def _extract_json_payload(text):
    raw = str(text or "").strip()
    if not raw:
        return {}

    fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", raw, flags=re.S)
    if fenced:
        raw = fenced.group(1)
    else:
        start = min([idx for idx in [raw.find("{"), raw.find("[")] if idx >= 0], default=-1)
        end_obj = raw.rfind("}")
        end_arr = raw.rfind("]")
        end = max(end_obj, end_arr)
        if start >= 0 and end > start:
            raw = raw[start:end + 1]

    try:
        return json.loads(raw)
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_supplier_dictionary(_conn):
    ensure_supplier_purchase_schema(_conn)
    return pd.read_sql_query(
        """
        SELECT id, sigla, categoria, valor_expandido, ativo
        FROM compras_fornecedor_siglas
        ORDER BY categoria, sigla
        """,
        _conn,
    )


def dictionary_map(conn):
    df = load_supplier_dictionary(conn)
    mapping = {}
    for row in df.itertuples():
        if not int(row.ativo or 0):
            continue
        mapping[_normalize_token(row.sigla)] = {
            "categoria": _clean_text(row.categoria).lower(),
            "valor": _clean_text(row.valor_expandido),
        }
    return mapping


def update_supplier_dictionary(conn, rows, user):
    ensure_supplier_purchase_schema(conn)
    cursor = conn.cursor()
    saved = 0
    for row in rows:
        sigla = _clean_text(row.get("sigla"))
        categoria = _clean_text(row.get("categoria")).lower()
        valor_expandido = _clean_text(row.get("valor_expandido"))
        ativo = 1 if bool(row.get("ativo", True)) else 0
        if not sigla or not categoria or not valor_expandido:
            continue
        cursor.execute(
            """
            INSERT INTO compras_fornecedor_siglas (sigla, categoria, valor_expandido, ativo, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (sigla) DO UPDATE SET
                categoria = excluded.categoria,
                valor_expandido = excluded.valor_expandido,
                ativo = excluded.ativo,
                updated_at = CURRENT_TIMESTAMP
            """,
            (sigla.upper(), categoria, valor_expandido, ativo),
        )
        saved += 1
    conn.commit()
    load_supplier_dictionary.clear()
    log_action(conn, user, "atualizou_dicionario_compras_fornecedor", "compras_fornecedor_siglas", detalhes={"registros": saved})
    return saved


def _normalize_purchase_row(row, default_supplier="", default_date="", mapping=None, observation_prefix=""):
    mapping = mapping or {}
    supplier = _clean_text(row.get("fornecedor") or default_supplier)
    purchase_date = _normalize_date(row.get("data_compra") or default_date)
    tipo = _clean_text(row.get("tipo"))
    aro = _clean_text(row.get("aro"))
    tecnologia = _clean_text(row.get("tecnologia"))
    modelo = _clean_text(row.get("modelo"))
    observacao = _clean_text(row.get("observacao") or observation_prefix)

    for field_name, current_value in [("tipo", tipo), ("aro", aro), ("tecnologia", tecnologia)]:
        token = _normalize_token(current_value)
        if token and token in mapping and mapping[token]["categoria"] == field_name:
            expanded = mapping[token]["valor"]
            if field_name == "tipo":
                tipo = expanded
            elif field_name == "aro":
                aro = expanded
            else:
                tecnologia = expanded

    return {
        "data_compra": purchase_date,
        "fornecedor": supplier,
        "tipo": tipo or "Outro",
        "modelo": modelo,
        "aro": aro or "Não informado",
        "tecnologia": tecnologia or "Não informado",
        "valor": round(_money_to_float(row.get("valor")), 2),
        "observacao": observacao,
        "status_pagamento": _clean_text(row.get("status_pagamento") or "Em aberto"),
        "valor_pago": round(_money_to_float(row.get("valor_pago")), 2),
        "data_pagamento": _clean_text(row.get("data_pagamento")),
    }


def dataframe_from_rows(rows, conn=None, default_supplier="", default_date="", observation_prefix=""):
    mapping = dictionary_map(conn) if conn is not None else {}
    normalized = []
    for row in rows or []:
        normalized_row = _normalize_purchase_row(
            row,
            default_supplier=default_supplier,
            default_date=default_date,
            mapping=mapping,
            observation_prefix=observation_prefix,
        )
        if not normalized_row["modelo"] and normalized_row["valor"] <= 0:
            continue
        normalized.append(normalized_row)
    if not normalized:
        return pd.DataFrame(columns=SUPPLIER_PURCHASE_COLUMNS)
    return pd.DataFrame(normalized, columns=SUPPLIER_PURCHASE_COLUMNS)


def _line_parser(text, conn=None):
    mapping = dictionary_map(conn) if conn is not None else {}
    rows = []
    supplier = ""
    purchase_date = datetime.today().date().isoformat()

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.casefold()
        if lower.startswith("fornecedor:"):
            supplier = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("data:"):
            purchase_date = _normalize_date(line.split(":", 1)[1].strip())
            continue

        money_match = re.search(r"(\d[\d.,]*)\s*$", line)
        value = _money_to_float(money_match.group(1)) if money_match else 0.0
        body = line[:money_match.start()].strip(" -") if money_match else line
        tokens = [token for token in re.split(r"\s+", body) if token]
        if not tokens:
            continue

        tipo = ""
        aro = ""
        tecnologia = ""
        model_tokens = []
        for token in tokens:
            info = mapping.get(_normalize_token(token))
            if info:
                if info["categoria"] == "tipo" and not tipo:
                    tipo = info["valor"]
                    continue
                if info["categoria"] == "aro" and not aro:
                    aro = info["valor"]
                    continue
                if info["categoria"] == "tecnologia" and not tecnologia:
                    tecnologia = info["valor"]
                    continue
            model_tokens.append(token)

        rows.append(
            {
                "data_compra": purchase_date,
                "fornecedor": supplier,
                "tipo": tipo or "Outro",
                "modelo": " ".join(model_tokens).strip(),
                "aro": aro or "Não informado",
                "tecnologia": tecnologia or "Não informado",
                "valor": value,
                "observacao": "",
                "status_pagamento": "Em aberto",
                "valor_pago": 0.0,
                "data_pagamento": "",
            }
        )
    return dataframe_from_rows(rows, conn=conn, default_supplier=supplier, default_date=purchase_date)


def csv_preview(uploaded_file, conn=None):
    data = uploaded_file.getvalue().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(data))
    rows = []
    for row in reader:
        mapped = {}
        for key, value in row.items():
            normalized_key = _normalize_token(key).lower()
            if normalized_key in {"data", "datacompra"}:
                mapped["data_compra"] = value
            elif normalized_key == "fornecedor":
                mapped["fornecedor"] = value
            elif normalized_key == "tipo":
                mapped["tipo"] = value
            elif normalized_key == "modelo":
                mapped["modelo"] = value
            elif normalized_key == "aro":
                mapped["aro"] = value
            elif normalized_key == "tecnologia":
                mapped["tecnologia"] = value
            elif normalized_key == "valor":
                mapped["valor"] = value
            elif normalized_key in {"observacao", "observacaoes"}:
                mapped["observacao"] = value
            elif normalized_key in {"statuspagamento", "status"}:
                mapped["status_pagamento"] = value
            elif normalized_key == "valorpago":
                mapped["valor_pago"] = value
            elif normalized_key == "datapagamento":
                mapped["data_pagamento"] = value
        rows.append(mapped)
    return dataframe_from_rows(rows, conn=conn)


def export_purchases_csv(df):
    export_df = df.copy()
    rename_map = {column: SUPPLIER_PURCHASE_LABELS.get(column, column) for column in export_df.columns}
    export_df = export_df.rename(columns=rename_map)
    return export_df.to_csv(index=False).encode("utf-8-sig")


def _openai_api_key():
    return os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)


def ai_ocr_available():
    return bool(_openai_api_key())


def _image_to_data_url(uploaded_file):
    mime_type = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    payload = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    return f"data:{mime_type};base64,{payload}"


def _openai_extract_file(uploaded_file, conn=None):
    api_key = _openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada.")

    mapping = dictionary_map(conn) if conn is not None else {}
    dictionary_text = "\n".join(
        f"- {key}: {value['valor']} ({value['categoria']})"
        for key, value in sorted(mapping.items())
    )
    prompt = (
        "Você está lendo uma folha manuscrita de fornecedor de peças. "
        "Extraia os itens e devolva somente JSON válido, sem markdown. "
        "Use este formato: "
        "{\"data_compra\":\"YYYY-MM-DD\",\"fornecedor\":\"texto\",\"observacao_geral\":\"texto\",\"itens\":["
        "{\"tipo\":\"\",\"modelo\":\"\",\"aro\":\"\",\"tecnologia\":\"\",\"valor\":0,\"observacao\":\"\"}"
        "]}. "
        "Normalizações esperadas: expanda siglas quando possível. "
        "Dicionário atual:\n"
        f"{dictionary_text or '- sem dicionário configurado'}\n"
        "Se algum campo não estiver claro, deixe string vazia. "
        "Valor deve ser numérico."
    )

    payload = {
        "model": os.getenv("OPENAI_OCR_MODEL", "gpt-5.5"),
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": _image_to_data_url(uploaded_file), "detail": "high"},
                ],
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Falha no OCR com IA: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Falha no OCR com IA: {exc}") from exc

    text = result.get("output_text") or ""
    parsed = _extract_json_payload(text)
    if not parsed:
        raise RuntimeError("A IA respondeu, mas não retornou JSON utilizável.")
    return parsed, text


def preview_from_images(files, conn=None):
    if conn is not None:
        ensure_supplier_purchase_schema(conn)
    aggregated_rows = []
    extracted = []
    fallback_text = []

    for uploaded_file in files or []:
        saved_path = save_uploaded_sheet(uploaded_file)
        parsed, raw_text = _openai_extract_file(uploaded_file, conn=conn)
        supplier = _clean_text(parsed.get("fornecedor"))
        purchase_date = _normalize_date(parsed.get("data_compra"))
        observation = _clean_text(parsed.get("observacao_geral"))
        rows = parsed.get("itens") or []
        df = dataframe_from_rows(rows, conn=conn, default_supplier=supplier, default_date=purchase_date, observation_prefix=observation)
        if df.empty:
            continue
        aggregated_rows.extend(df.to_dict("records"))
        extracted.append(
            {
                "arquivo": saved_path,
                "fornecedor": supplier,
                "data_compra": purchase_date,
                "ocr_bruto": raw_text,
            }
        )
        fallback_text.append(raw_text)

    return dataframe_from_rows(aggregated_rows, conn=conn), extracted, "\n\n".join(fallback_text)


def save_uploaded_sheet(uploaded_file):
    upload_dir = Path("uploads") / "compras_fornecedor"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name.replace("/", "-").replace("\\", "-")
    path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def import_supplier_purchases(conn, preview_df, extracted_meta=None, user=None, create_expenses=True):
    ensure_supplier_purchase_schema(conn)
    if preview_df is None or preview_df.empty:
        return {"compras": 0, "despesas": 0, "total": 0.0}

    user = user or current_user()
    cursor = conn.cursor()
    extracted_meta = extracted_meta or []
    fallback_file = extracted_meta[0]["arquivo"] if extracted_meta else ""
    fallback_ocr = extracted_meta[0]["ocr_bruto"] if extracted_meta else ""
    total = 0.0
    purchases_count = 0
    expense_count = 0

    for row in preview_df.to_dict("records"):
        normalized = _normalize_purchase_row(row)
        if normalized["valor"] <= 0:
            continue
        normalized["valor_pago"] = min(normalized["valor"], normalized["valor_pago"])
        if normalized["valor_pago"] >= normalized["valor"] and normalized["valor"] > 0:
            normalized["status_pagamento"] = "Pago"
        elif normalized["valor_pago"] > 0:
            normalized["status_pagamento"] = "Parcial"
        else:
            normalized["status_pagamento"] = "Em aberto"
        if normalized["status_pagamento"] == "Pago" and not normalized["data_pagamento"]:
            normalized["data_pagamento"] = datetime.today().date().isoformat()

        params = (
            normalized["data_compra"],
            normalized["fornecedor"],
            normalized["tipo"],
            normalized["modelo"],
            normalized["aro"],
            normalized["tecnologia"],
            normalized["valor"],
            normalized["valor_pago"],
            normalized["data_pagamento"] or None,
            normalized["observacao"],
            normalized["status_pagamento"],
            fallback_file,
            fallback_ocr,
            current_quiosque_id(user),
        )
        if getattr(conn, "backend", "sqlite") == "postgres":
            compra_id = cursor.execute(
                """
                INSERT INTO compras_fornecedor (
                    data_compra, fornecedor, tipo, modelo, aro, tecnologia, valor,
                    valor_pago, data_pagamento, observacao, status_pagamento, arquivo_origem,
                    ocr_bruto, quiosque_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                params,
            ).fetchone()[0]
        else:
            cursor.execute(
                """
                INSERT INTO compras_fornecedor (
                    data_compra, fornecedor, tipo, modelo, aro, tecnologia, valor,
                    valor_pago, data_pagamento, observacao, status_pagamento, arquivo_origem,
                    ocr_bruto, quiosque_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                params,
            )
            compra_id = cursor.lastrowid

        despesa_id = None
        if create_expenses:
            descricao = "Compra fornecedor"
            details = " | ".join(part for part in [normalized["fornecedor"], normalized["tipo"], normalized["modelo"], normalized["tecnologia"]] if part)
            if details:
                descricao = f"{descricao} - {details}"
            despesa_params = (
                normalized["data_compra"],
                descricao,
                normalized["valor"],
                current_quiosque_id(user),
                normalized["fornecedor"],
                "compras_fornecedor",
                compra_id,
            )
            if getattr(conn, "backend", "sqlite") == "postgres":
                despesa_id = cursor.execute(
                    """
                    INSERT INTO despesas (data, descricao, valor, quiosque_id, fornecedor, origem, compra_fornecedor_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                    """,
                    despesa_params,
                ).fetchone()[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO despesas (data, descricao, valor, quiosque_id, fornecedor, origem, compra_fornecedor_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    despesa_params,
                )
                despesa_id = cursor.lastrowid
            expense_count += 1

        if compra_id is not None and despesa_id is not None:
            cursor.execute(
                "UPDATE compras_fornecedor SET despesa_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (despesa_id, compra_id),
            )

        total += normalized["valor"]
        purchases_count += 1

    conn.commit()
    log_action(
        conn,
        user,
        "importou_compras_fornecedor",
        "compras_fornecedor",
        detalhes={
            "compras": purchases_count,
            "despesas": expense_count,
            "total": total,
            "quiosque_id": current_quiosque_id(user),
        },
    )
    return {"compras": purchases_count, "despesas": expense_count, "total": total}


def load_supplier_purchases(conn, fornecedor="", status_pagamento="", limit=400):
    ensure_supplier_purchase_schema(conn)
    where_scope, params_scope = scope_clause("c")
    filters = []
    params = []
    if fornecedor:
        filters.append("LOWER(COALESCE(c.fornecedor, '')) LIKE ?")
        params.append(f"%{fornecedor.strip().lower()}%")
    if status_pagamento:
        filters.append("COALESCE(c.status_pagamento, 'Em aberto') = ?")
        params.append(status_pagamento)
    where_filters = ""
    if filters:
        where_filters = " AND " + " AND ".join(filters)

    return pd.read_sql_query(
        f"""
        SELECT
            c.id,
            c.data_compra,
            c.fornecedor,
            c.tipo,
            c.modelo,
            c.aro,
            c.tecnologia,
            c.valor,
            c.valor_pago,
            c.data_pagamento,
            c.observacao,
            c.status_pagamento,
            c.arquivo_origem,
            c.created_at,
            c.updated_at,
            c.quiosque_id
        FROM compras_fornecedor c
        {where_scope if where_scope else "WHERE 1 = 1"}
        {where_filters}
        ORDER BY c.data_compra DESC, c.id DESC
        LIMIT ?
        """,
        conn,
        params=params_scope + tuple(params) + (int(limit),),
    )


def load_supplier_summary(conn):
    ensure_supplier_purchase_schema(conn)
    where_scope, params_scope = scope_clause("c")
    return pd.read_sql_query(
        f"""
        SELECT
            COALESCE(SUM(c.valor), 0) AS total_comprado,
            COALESCE(SUM(c.valor_pago), 0) AS total_pago,
            COALESCE(SUM(c.valor - c.valor_pago), 0) AS saldo_devedor,
            COUNT(*) AS quantidade
        FROM compras_fornecedor c
        {where_scope}
        """,
        conn,
        params=params_scope,
    )


def load_supplier_history(conn):
    ensure_supplier_purchase_schema(conn)
    where_scope, params_scope = scope_clause("c")
    return pd.read_sql_query(
        f"""
        SELECT
            COALESCE(c.fornecedor, 'Sem fornecedor') AS fornecedor,
            COUNT(*) AS quantidade,
            COALESCE(SUM(c.valor), 0) AS total_comprado,
            COALESCE(SUM(c.valor_pago), 0) AS total_pago,
            COALESCE(SUM(c.valor - c.valor_pago), 0) AS saldo_devedor,
            MAX(c.data_compra) AS ultima_compra
        FROM compras_fornecedor c
        {where_scope}
        GROUP BY COALESCE(c.fornecedor, 'Sem fornecedor')
        ORDER BY total_comprado DESC, fornecedor ASC
        """,
        conn,
        params=params_scope,
    )


def update_purchase_payment(conn, compra_id, status_pagamento, valor_pago, data_pagamento, observacao, user=None):
    ensure_supplier_purchase_schema(conn)
    user = user or current_user()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT id, valor, valor_pago, status_pagamento, data_pagamento, observacao
        FROM compras_fornecedor
        WHERE id = ?
        """,
        (int(compra_id),),
    ).fetchone()
    if not row:
        raise ValueError("Compra não encontrada.")

    valor_total = float(row[1] or 0)
    valor_pago = min(max(_money_to_float(valor_pago), 0.0), valor_total)
    if valor_pago >= valor_total and valor_total > 0:
        status_pagamento = "Pago"
    elif valor_pago > 0:
        status_pagamento = "Parcial"
    else:
        status_pagamento = "Em aberto"

    data_pagamento = _clean_text(data_pagamento)
    if status_pagamento == "Pago" and not data_pagamento:
        data_pagamento = datetime.today().date().isoformat()
    if status_pagamento == "Em aberto":
        data_pagamento = ""

    cursor.execute(
        """
        UPDATE compras_fornecedor
        SET valor_pago = ?, status_pagamento = ?, data_pagamento = ?, observacao = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (valor_pago, status_pagamento, data_pagamento or None, _clean_text(observacao), int(compra_id)),
    )
    conn.commit()
    log_action(
        conn,
        user,
        "atualizou_pagamento_compra_fornecedor",
        "compras_fornecedor",
        int(compra_id),
        {
            "valor_total": valor_total,
            "valor_pago": valor_pago,
            "status_pagamento": status_pagamento,
            "data_pagamento": data_pagamento,
        },
    )


def payments_overview(df):
    if df.empty:
        return {"total_comprado": 0.0, "total_pago": 0.0, "saldo_devedor": 0.0}
    total_comprado = float(df["valor"].sum())
    total_pago = float(df["valor_pago"].sum())
    return {
        "total_comprado": total_comprado,
        "total_pago": total_pago,
        "saldo_devedor": total_comprado - total_pago,
    }


def preview_from_text(text, conn=None):
    return _line_parser(text, conn=conn)
