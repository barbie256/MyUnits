from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Receipt


def format_receipt_value(value: object) -> str:
    if value is None:
        return "N/A"

    if isinstance(value, Decimal):
        return f"{value:,.2f}"

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    return str(value)


def build_receipt_pdf(receipt: Receipt, recorded_by: str) -> bytes:
    pdf_buffer = BytesIO()
    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    receipt_rows = [
        ("Receipt Number", receipt.receipt_number),
        ("Tenant Name", receipt.tenant_name),
        ("Property Name", receipt.property_name),
        ("Unit Name", receipt.unit_name),
        ("Amount Paid", receipt.amount_paid),
        ("Payment Method", receipt.payment_method),
        ("Payment Date", receipt.payment_date),
        ("Month Paid For", receipt.month_paid_for),
        ("Total Available For Month", receipt.total_available_for_month),
        ("Balance After Payment", receipt.balance_after_payment),
        ("Credit Amount", receipt.credit_amount),
        ("Payment Status", receipt.payment_status),
        ("Recorded By", recorded_by),
        ("Created At", receipt.created_at),
    ]
    table_data = [[
        Paragraph("<b>Field</b>", styles["Normal"]),
        Paragraph("<b>Details</b>", styles["Normal"]),
    ]]
    table_data.extend(
        [
            [
                Paragraph(label, styles["Normal"]),
                Paragraph(format_receipt_value(value), styles["Normal"]),
            ]
            for label, value in receipt_rows
        ]
    )

    details_table = Table(table_data, colWidths=[2.4 * inch, 3.9 * inch])
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EC")),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F4F7FA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story = [
        Paragraph("MyUnits", styles["Title"]),
        Paragraph("Official Payment Receipt", styles["Heading2"]),
        Spacer(1, 0.25 * inch),
        details_table,
        Spacer(1, 0.3 * inch),
        Paragraph("Thank you for using MyUnits.", styles["Normal"]),
    ]
    document.build(story)

    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
