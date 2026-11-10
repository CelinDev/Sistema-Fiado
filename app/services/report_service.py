from datetime import datetime
from pathlib import Path
from typing import List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config.settings import settings
from app.database.connection import db_manager
from app.database.models import Customer, Debt, DebtStatus, Payment
from app.database.repositories import CustomerRepository, DebtRepository, PaymentRepository
from app.utils.formatters import (
    format_cpf,
    format_currency,
    format_date,
    format_datetime,
    format_phone,
)


class ReportService:
    def __init__(self, db_session_factory=None):
        self.session_factory = db_session_factory or db_manager.session_scope

    # ==========================================
    # 1. EXTRATO INDIVIDUAL DO CLIENTE (PDF)
    # ==========================================
    def generate_customer_statement_pdf(self, customer_id: int) -> Path:
        with self.session_factory() as session:
            cust_repo = CustomerRepository(session)
            customer = cust_repo.get_with_details(customer_id)
            if not customer:
                raise ValueError("Cliente não encontrado.")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extrato_{customer.name.replace(' ', '_').lower()}_{timestamp}.pdf"
            output_path = settings.export_dir / filename

            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "TitleStyle",
                parent=styles["Heading1"],
                fontSize=20,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=4,
            )
            subtitle_style = ParagraphStyle(
                "SubtitleStyle",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#64748B"),
                spaceAfter=14,
            )
            section_style = ParagraphStyle(
                "SectionStyle",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#059669"),
                spaceBefore=12,
                spaceAfter=6,
            )

            elements = []

            # Cabeçalho
            elements.append(Paragraph("<b>FIADO MANAGER</b> - Extrato Financeiro", title_style))
            elements.append(
                Paragraph(
                    f"Emissão: {datetime.now().strftime('%d/%m/%Y às %H:%M')} | Documento de Controle Interno",
                    subtitle_style,
                )
            )
            elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#059669"), spaceAfter=14))

            # Dados do Cliente
            cust_info = [
                [Paragraph("<b>Cliente:</b>", styles["Normal"]), Paragraph(customer.name, styles["Normal"])],
                [Paragraph("<b>Telefone:</b>", styles["Normal"]), Paragraph(format_phone(customer.phone) if customer.phone else "-", styles["Normal"])],
                [Paragraph("<b>CPF:</b>", styles["Normal"]), Paragraph(format_cpf(customer.cpf) if customer.cpf else "-", styles["Normal"])],
                [Paragraph("<b>Endereço:</b>", styles["Normal"]), Paragraph(customer.address or "-", styles["Normal"])],
            ]
            t_cust = Table(cust_info, colWidths=[90, 430])
            t_cust.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]))
            elements.append(t_cust)
            elements.append(Spacer(1, 12))

            # Resumo Financeiro
            kpis = [
                ["TOTAL COMPRADO", "TOTAL JÁ PAGO", "SALDO DEVEDOR ATUAL"],
                [
                    format_currency(customer.total_purchases_cents),
                    format_currency(customer.total_paid_cents),
                    format_currency(customer.current_debt_cents),
                ],
            ]
            t_kpis = Table(kpis, colWidths=[173, 173, 174])
            t_kpis.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (1, 1), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#FEE2E2") if customer.current_debt_cents > 0 else colors.HexColor("#D1FAE5")),
                ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#DC2626") if customer.current_debt_cents > 0 else colors.HexColor("#059669")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(t_kpis)
            elements.append(Spacer(1, 14))

            # Tabela de Dívidas / Compras
            elements.append(Paragraph("Compras Fiadas Registradas", section_style))
            open_debts = [d for d in customer.debts if d.status != DebtStatus.CANCELLED.value]
            debt_table_data = [["Data", "Descrição", "Vencimento", "Valor Original", "Saldo Restante", "Situação"]]
            for d in open_debts:
                debt_table_data.append([
                    format_date(d.created_at),
                    d.description[:28],
                    format_date(d.due_date),
                    format_currency(d.original_amount_cents),
                    format_currency(d.remaining_cents),
                    d.status,
                ])

            if len(debt_table_data) > 1:
                t_debts = Table(debt_table_data, colWidths=[65, 145, 75, 75, 85, 75])
                t_debts.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("ALIGN", (3, 0), (4, -1), "RIGHT"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                elements.append(t_debts)
            else:
                elements.append(Paragraph("Nenhuma compra registrada.", styles["Normal"]))

            elements.append(Spacer(1, 14))

            # Tabela de Pagamentos
            elements.append(Paragraph("Histórico de Pagamentos Recebidos", section_style))
            payments = sorted(customer.payments, key=lambda p: p.payment_date, reverse=True)
            pay_table_data = [["Data / Hora", "Forma", "Valor Recebido", "Referência", "Situação"]]
            for p in payments:
                pay_table_data.append([
                    format_datetime(p.payment_date),
                    p.payment_method,
                    format_currency(p.amount_cents),
                    f"Fiado #{p.debt_id}" if p.debt_id else "Abatimento Geral",
                    "ESTORNADO" if p.is_cancelled else "CONFIRMADO",
                ])

            if len(pay_table_data) > 1:
                t_pays = Table(pay_table_data, colWidths=[110, 90, 95, 125, 100])
                t_pays.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                elements.append(t_pays)
            else:
                elements.append(Paragraph("Nenhum pagamento registrado.", styles["Normal"]))

            doc.build(elements)
            return output_path

    # ==========================================
    # 2. RELATÓRIO DE CLIENTES (EXCEL)
    # ==========================================
    def export_customers_excel(self, only_with_debt: bool = False) -> Path:
        with self.session_factory() as session:
            cust_repo = CustomerRepository(session)
            customers = cust_repo.get_all_with_debts()
            if only_with_debt:
                customers = [c for c in customers if c.current_debt_cents > 0]

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Clientes"

            headers = ["ID", "Nome do Cliente", "Telefone", "CPF", "Total Comprado (R$)", "Total Já Pago (R$)", "Saldo Devedor Atual (R$)", "Status"]
            ws.append(headers)

            header_fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center" if col_idx in [1, 3, 4, 8] else "left")

            thin_border = Border(
                left=Side(style="thin", color="E2E8F0"),
                right=Side(style="thin", color="E2E8F0"),
                top=Side(style="thin", color="E2E8F0"),
                bottom=Side(style="thin", color="E2E8F0"),
            )

            for c in customers:
                row_data = [
                    c.id,
                    c.name,
                    format_phone(c.phone) if c.phone else "",
                    format_cpf(c.cpf) if c.cpf else "",
                    c.total_purchases_cents / 100.0,
                    c.total_paid_cents / 100.0,
                    c.current_debt_cents / 100.0,
                    "COM DÉBITO" if c.current_debt_cents > 0 else "QUITADO",
                ]
                ws.append(row_data)
                curr_row = ws.max_row
                for col_idx in range(1, len(headers) + 1):
                    cell = ws.cell(row=curr_row, column=col_idx)
                    cell.border = thin_border
                    if col_idx in [5, 6, 7]:
                        cell.number_format = 'R$ #,##0.00'

            # Ajuste automático de largura das colunas
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = col[0].column_letter
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_clientes_{timestamp}.xlsx"
            out_file = settings.export_dir / filename
            wb.save(out_file)
            return out_file

    # ==========================================
    # 3. RELATÓRIO DE DÍVIDAS VENCIDAS (PDF)
    # ==========================================
    def export_overdue_debts_pdf(self) -> Path:
        with self.session_factory() as session:
            debt_repo = DebtRepository(session)
            overdue_debts = debt_repo.get_overdue_debts()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_dividas_vencidas_{timestamp}.pdf"
            output_path = settings.export_dir / filename

            doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#DC2626"), spaceAfter=4)
            elements = [
                Paragraph("<b>FIADO MANAGER</b> - Relatório de Dívidas Vencidas", title_style),
                Paragraph(f"Posição em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles["Normal"]),
                Spacer(1, 12),
            ]

            total_overdue = sum(d.remaining_cents for d in overdue_debts)
            elements.append(Paragraph(f"<b>Total Vencido em Aberto:</b> {format_currency(total_overdue)} ({len(overdue_debts)} títulos)", styles["Heading3"]))
            elements.append(Spacer(1, 10))

            table_data = [["Cliente", "Telefone", "Descrição", "Data Compra", "Vencimento", "Saldo Devedor"]]
            for d in overdue_debts:
                table_data.append([
                    d.customer.name[:25] if d.customer else "-",
                    format_phone(d.customer.phone) if d.customer and d.customer.phone else "-",
                    d.description[:25],
                    format_date(d.created_at),
                    format_date(d.due_date),
                    format_currency(d.remaining_cents),
                ])

            if len(table_data) > 1:
                t = Table(table_data, colWidths=[120, 85, 125, 60, 65, 65])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEE2E2")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ALIGN", (5, 0), (5, -1), "RIGHT"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                elements.append(t)
            else:
                elements.append(Paragraph("Nenhuma dívida vencida encontrada.", styles["Normal"]))

            doc.build(elements)
            return output_path

    # ==========================================
    # 4. EXPORTAÇÃO DE PAGAMENTOS (EXCEL)
    # ==========================================
    def export_payments_excel(self) -> Path:
        with self.session_factory() as session:
            pay_repo = PaymentRepository(session)
            payments = pay_repo.get_recent_payments(limit=1000)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Pagamentos"

            headers = ["ID", "Data / Hora", "Cliente", "Telefone", "Valor (R$)", "Forma de Pagamento", "Dívida Ref", "Situação"]
            ws.append(headers)

            header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font

            for p in payments:
                ws.append([
                    p.id,
                    p.payment_date.strftime("%d/%m/%Y %H:%M"),
                    p.customer.name if p.customer else "",
                    format_phone(p.customer.phone) if p.customer and p.customer.phone else "",
                    p.amount_cents / 100.0,
                    p.payment_method,
                    f"Fiado #{p.debt_id}" if p.debt_id else "Abatimento Geral",
                    "ESTORNADO" if p.is_cancelled else "CONFIRMADO",
                ])
                ws.cell(row=ws.max_row, column=5).number_format = 'R$ #,##0.00'

            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = col[0].column_letter
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_pagamentos_{timestamp}.xlsx"
            out_file = settings.export_dir / filename
            wb.save(out_file)
            return out_file

    # ==========================================
    # 5. COMPROVANTES TÉRMICOS (80mm / 58mm)
    # ==========================================
    def generate_thermal_receipt_pdf(
        self,
        receipt_type: str,  # "DEBT" ou "PAYMENT"
        record_id: int,
        paper_width_mm: int = 80,  # 80 ou 58
    ) -> Path:
        """
        Gera cupom térmico não-fiscal em PDF pronto para impressoras de 80mm ou 58mm.
        receipt_type: 'DEBT' para compra fiada, 'PAYMENT' para pagamento/baixa.
        """
        from reportlab.lib.units import mm

        width_pt = (80 if paper_width_mm >= 70 else 58) * mm
        left_margin = 4 * mm
        right_margin = 4 * mm
        usable_width = width_pt - (left_margin + right_margin)

        with self.session_factory() as session:
            cust_repo = CustomerRepository(session)
            debt_repo = DebtRepository(session)
            pay_repo = PaymentRepository(session)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cupom_{receipt_type.lower()}_{record_id}_{timestamp}.pdf"
            output_path = settings.export_dir / filename

            styles = getSampleStyleSheet()
            center_bold = ParagraphStyle("CB", parent=styles["Normal"], alignment=1, fontSize=9, leading=11, fontName="Helvetica-Bold")
            center_normal = ParagraphStyle("CN", parent=styles["Normal"], alignment=1, fontSize=8, leading=10, fontName="Helvetica")
            left_normal = ParagraphStyle("LN", parent=styles["Normal"], alignment=0, fontSize=8, leading=10, fontName="Helvetica")
            left_bold = ParagraphStyle("LB", parent=styles["Normal"], alignment=0, fontSize=8, leading=10, fontName="Helvetica-Bold")
            right_bold = ParagraphStyle("RB", parent=styles["Normal"], alignment=2, fontSize=9, leading=11, fontName="Helvetica-Bold")

            elements = []

            # Cabeçalho da Empresa / Estabelecimento
            elements.append(Paragraph("<b>*** FIADO MANAGER ***</b>", center_bold))
            elements.append(Paragraph("CONTROLE INTERNO DE CREDITO", center_normal))
            elements.append(Paragraph("NAO TEM VALOR FISCAL", center_normal))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=4, spaceAfter=4))

            if receipt_type == "DEBT":
                debt = debt_repo.get_by_id(record_id)
                if not debt:
                    raise ValueError("Fiado não encontrado.")
                customer = cust_repo.get_with_details(debt.customer_id)

                elements.append(Paragraph("<b>COMPROVANTE DE COMPRA A PRAZO</b>", center_bold))
                elements.append(Paragraph(f"Data: {format_datetime(debt.created_at)}", center_normal))
                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceBefore=3, spaceAfter=4))

                elements.append(Paragraph(f"<b>CLIENTE:</b> {customer.name}", left_normal))
                if customer.phone:
                    elements.append(Paragraph(f"Fone: {format_phone(customer.phone)}", left_normal))
                if customer.cpf:
                    elements.append(Paragraph(f"CPF: {format_cpf(customer.cpf)}", left_normal))

                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceBefore=3, spaceAfter=4))
                elements.append(Paragraph(f"<b>DESCRICAO:</b>", left_bold))
                elements.append(Paragraph(f"{debt.description}", left_normal))
                if debt.due_date:
                    elements.append(Paragraph(f"Vencimento: {format_date(debt.due_date)}", left_normal))

                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceBefore=3, spaceAfter=4))
                elements.append(Paragraph(f"VALOR DESTA COMPRA: {format_currency(debt.original_amount_cents)}", right_bold))
                elements.append(Paragraph(f"SALDO DEVEDOR ATUAL: {format_currency(customer.current_debt_cents)}", right_bold))
                if customer.credit_limit_cents:
                    disponivel = max(0, customer.credit_limit_cents - customer.current_debt_cents)
                    elements.append(Paragraph(f"Limite Disponivel: {format_currency(disponivel)}", center_normal))

            else:  # PAYMENT
                payment = pay_repo.get_by_id(record_id)
                if not payment:
                    raise ValueError("Pagamento não encontrado.")
                customer = cust_repo.get_with_details(payment.customer_id)

                elements.append(Paragraph("<b>RECIBO DE PAGAMENTO</b>", center_bold))
                elements.append(Paragraph(f"Data: {format_datetime(payment.payment_date)}", center_normal))
                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceBefore=3, spaceAfter=4))

                elements.append(Paragraph(f"<b>CLIENTE:</b> {customer.name}", left_normal))
                if customer.phone:
                    elements.append(Paragraph(f"Fone: {format_phone(customer.phone)}", left_normal))

                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceBefore=3, spaceAfter=4))
                elements.append(Paragraph(f"Forma: {payment.payment_method}", left_normal))
                if payment.debt_id:
                    elements.append(Paragraph(f"Referencia: Fiado #{payment.debt_id}", left_normal))
                else:
                    elements.append(Paragraph("Referencia: Abatimento Geral", left_normal))

                elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceBefore=3, spaceAfter=4))
                elements.append(Paragraph(f"VALOR RECEBIDO: {format_currency(payment.amount_cents)}", right_bold))
                elements.append(Paragraph(f"SALDO RESTANTE: {format_currency(customer.current_debt_cents)}", right_bold))

            # Rodapé com Linha de Assinatura
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("___________________________________", center_normal))
            elements.append(Paragraph("Assinatura do Cliente", center_normal))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("Obrigado pela preferencia!", center_bold))

            # Cria documento com altura flexível para o cupom térmico
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=(width_pt, 180 * mm),
                leftMargin=left_margin,
                rightMargin=right_margin,
                topMargin=4 * mm,
                bottomMargin=4 * mm,
            )
            doc.build(elements)
            return output_path


report_service = ReportService()
