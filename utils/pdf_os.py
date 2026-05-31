from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


RED = colors.HexColor("#E63946")
DARK = colors.HexColor("#111827")
GRAY = colors.HexColor("#4B5563")
LIGHT_GRAY = colors.HexColor("#E5E7EB")
SECTION_BG = colors.HexColor("#F3F4F6")


def _text(value):
    if value is None:
        return ""
    return str(value)


def _money(value):
    try:
        return f"R$ {float(value):.2f}"
    except (TypeError, ValueError):
        return "R$ 0.00"


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AppTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=DARK,
        alignment=TA_LEFT,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="Muted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=GRAY,
    ))
    styles.add(ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=DARK,
        spaceBefore=8,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=GRAY,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="Value",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name="ValueBold",
        parent=styles["Value"],
        fontName="Helvetica-Bold",
    ))
    return styles


def _p(text, style):
    safe = _text(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe.replace("\n", "<br/>"), style)


def _logo():
    logo_path = Path("assets/branding/tx_logo_icon.png")

    if not logo_path.exists():
        return ""

    image = Image(str(logo_path), width=27 * mm, height=27 * mm)
    image.hAlign = "LEFT"
    return image


def _field(label, value, styles):
    return [
        _p(label.upper(), styles["Label"]),
        _p(value or "-", styles["Value"]),
    ]


def _section(title, styles):
    table = Table(
        [[_p(title, styles["Section"])]],
        colWidths=[174 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SECTION_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )
    return table


def _info_table(rows, widths):
    return Table(
        rows,
        colWidths=widths,
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, LIGHT_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]),
    )


def _signature_image(path):
    if not path:
        return ""

    image_path = Path(str(path))
    if not image_path.exists() or image_path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    image = Image(str(image_path), width=76 * mm, height=18 * mm)
    image.hAlign = "CENTER"
    return image


def _signature_table(styles, assinatura_cliente=None):
    assinatura = _signature_image(assinatura_cliente)
    return Table(
        [
            [assinatura, ""],
            [_p("Assinatura do cliente", styles["Muted"]), _p("Responsável pela loja", styles["Muted"])],
        ],
        colWidths=[84 * mm, 84 * mm],
        rowHeights=[20 * mm, 8 * mm],
        style=TableStyle([
            ("LINEBELOW", (0, 0), (0, 0), 0.8, DARK),
            ("LINEBELOW", (1, 0), (1, 0), 0.8, DARK),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]),
    )


def generate_os_pdf(os_data):
    buffer = BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title=f"OS #{_text(os_data.get('id')).zfill(5)}",
    )

    os_number = _text(os_data.get("id")).zfill(5)
    story = []

    header = Table(
        [[
            _logo(),
            [
                _p("Hospital do Celular", styles["AppTitle"]),
                _p("Ordem de Serviço", styles["Muted"]),
            ],
            [
                _p(f"<b>OS #{os_number}</b>", styles["ValueBold"]),
                _p(_text(os_data.get("data")), styles["Muted"]),
            ],
        ]],
        colWidths=[32 * mm, 91 * mm, 45 * mm],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("BOX", (2, 0), (2, 0), 1.2, RED),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (2, 0), (2, 0), 8),
            ("BOTTOMPADDING", (2, 0), (2, 0), 8),
        ]),
    )
    story.extend([header, Spacer(1, 10 * mm)])

    story.append(_section("Dados do atendimento", styles))
    story.append(_info_table([[
        _field("Atendente", os_data.get("atendente"), styles),
        _field("Loja", os_data.get("loja"), styles),
        _field("Status", os_data.get("status"), styles),
    ]], [58 * mm, 58 * mm, 58 * mm]))

    story.append(_section("Cliente", styles))
    story.append(_info_table([[
        _field("Nome", os_data.get("cliente"), styles),
        _field("CPF", os_data.get("cpf"), styles),
        _field("Telefone", os_data.get("telefone"), styles),
    ], [
        _field("Endereço", os_data.get("endereco"), styles),
        "",
        "",
    ]], [74 * mm, 45 * mm, 55 * mm]))

    story.append(_section("Aparelho", styles))
    story.append(_info_table([[
        _field("Marca", os_data.get("marca"), styles),
        _field("Modelo", os_data.get("modelo"), styles),
        _field("IMEI", os_data.get("imei"), styles),
    ], [
        _field("Senha", os_data.get("senha"), styles),
        "",
        "",
    ]], [55 * mm, 60 * mm, 59 * mm]))

    story.append(_section("Serviço", styles))
    story.append(_info_table([[
        _field("Defeito relatado", os_data.get("defeito"), styles),
    ], [
        _field("Serviço realizado", os_data.get("servico"), styles),
    ], [
        _field("Valor", _money(os_data.get("valor")), styles),
    ], [
        _field("Garantia", os_data.get("garantia"), styles),
    ], [
        _field("Observações", os_data.get("observacoes"), styles),
    ]], [174 * mm]))

    story.extend([
        Spacer(1, 18 * mm),
        _signature_table(styles, os_data.get("assinatura_saida") or os_data.get("assinatura_entrada")),
        Spacer(1, 5 * mm),
        _p("Documento gerado pelo sistema Hospital do Celular.", styles["Muted"]),
    ])

    doc.build(story)
    return buffer.getvalue()
