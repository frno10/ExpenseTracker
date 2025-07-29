import csv
import io
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union, BinaryIO
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.colors import HexColor
import xlsxwriter

from ..models.expense import ExpenseTable
from ..models.category import CategoryTable
from ..models.merchant import MerchantTable
from ..core.exceptions import ValidationError, BusinessLogicError


class ExportService:
    """Service for data export and reporting functionality."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== CSV EXPORT OPERATIONS =====
    
    async def export_expenses_csv(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_ids: Optional[List[UUID]] = None,
        merchant_ids: Optional[List[UUID]] = None,
        include_attachments: bool = False,
        include_notes: bool = True,
        custom_fields: Optional[List[str]] = None
    ) -> bytes:
        """Export expenses to CSV format."""
        # Get filtered expenses
        expenses = await self._get_filtered_expenses(
            user_id, date_from, date_to, category_ids, merchant_ids
        )
        
        # Create CSV content
        output = io.StringIO()
        
        # Define CSV headers
        headers = self._get_csv_headers(include_attachments, include_notes, custom_fields)
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # Write expense data
        for expense in expenses:
            row = self._format_expense_for_csv(
                expense, include_attachments, include_notes, custom_fields
            )
            writer.writerow(row)
        
        # Convert to bytes
        csv_content = output.getvalue()
        output.close()
        
        return csv_content.encode('utf-8')
    
    async def export_expenses_excel(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_ids: Optional[List[UUID]] = None,
        merchant_ids: Optional[List[UUID]] = None,
        include_summary: bool = True,
        include_charts: bool = True
    ) -> bytes:
        """Export expenses to Excel format with multiple sheets."""
        # Get filtered expenses
        expenses = await self._get_filtered_expenses(
            user_id, date_from, date_to, category_ids, merchant_ids
        )
        
        # Create Excel workbook in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Create worksheets
        self._create_expenses_worksheet(workbook, expenses)
        
        if include_summary:
            self._create_summary_worksheet(workbook, expenses, date_from, date_to)
        
        if include_charts:
            self._create_charts_worksheet(workbook, expenses)
        
        workbook.close()
        output.seek(0)
        
        return output.read()
    
    # ===== PDF EXPORT OPERATIONS =====
    
    async def export_expenses_pdf(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_ids: Optional[List[UUID]] = None,
        merchant_ids: Optional[List[UUID]] = None,
        report_title: str = "Expense Report",
        include_summary: bool = True,
        include_charts: bool = True,
        group_by_category: bool = False
    ) -> bytes:
        """Export expenses to PDF format with formatting and charts."""
        # Get filtered expenses
        expenses = await self._get_filtered_expenses(
            user_id, date_from, date_to, category_ids, merchant_ids
        )
        
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Add title and metadata
        self._add_pdf_header(story, styles, report_title, date_from, date_to, len(expenses))
        
        # Add summary section
        if include_summary:
            self._add_pdf_summary(story, styles, expenses)
        
        # Add charts
        if include_charts:
            self._add_pdf_charts(story, expenses)
        
        # Add expense details
        if group_by_category:
            self._add_pdf_expenses_by_category(story, styles, expenses)
        else:
            self._add_pdf_expenses_table(story, styles, expenses)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.read()
    
    # ===== TAX EXPORT OPERATIONS =====
    
    async def export_tax_report(
        self,
        user_id: UUID,
        tax_year: int,
        tax_categories: Optional[Dict[str, List[str]]] = None,
        format_type: str = "pdf"
    ) -> bytes:
        """Export tax-focused report with category groupings."""
        # Define date range for tax year
        date_from = date(tax_year, 1, 1)
        date_to = date(tax_year, 12, 31)
        
        # Get expenses for tax year
        expenses = await self._get_filtered_expenses(user_id, date_from, date_to)
        
        # Group expenses by tax categories
        tax_grouped_expenses = self._group_expenses_for_tax(expenses, tax_categories)
        
        if format_type.lower() == "csv":
            return await self._export_tax_csv(tax_grouped_expenses, tax_year)
        elif format_type.lower() == "excel":
            return await self._export_tax_excel(tax_grouped_expenses, tax_year)
        else:  # PDF
            return await self._export_tax_pdf(tax_grouped_expenses, tax_year)
    
    # ===== JSON EXPORT OPERATIONS =====
    
    async def export_expenses_json(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_ids: Optional[List[UUID]] = None,
        merchant_ids: Optional[List[UUID]] = None,
        include_metadata: bool = True
    ) -> bytes:
        """Export expenses to JSON format."""
        # Get filtered expenses
        expenses = await self._get_filtered_expenses(
            user_id, date_from, date_to, category_ids, merchant_ids
        )
        
        # Convert to JSON-serializable format
        export_data = {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": str(user_id),
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "total_expenses": len(expenses),
                "filters_applied": {
                    "category_ids": [str(cid) for cid in category_ids] if category_ids else None,
                    "merchant_ids": [str(mid) for mid in merchant_ids] if merchant_ids else None
                }
            } if include_metadata else None,
            "expenses": []
        }
        
        for expense in expenses:
            expense_data = {
                "id": str(expense.id),
                "amount": float(expense.amount),
                "description": expense.description,
                "notes": expense.notes,
                "expense_date": expense.expense_date.isoformat(),
                "category": {
                    "id": str(expense.category.id) if expense.category else None,
                    "name": expense.category.name if expense.category else None
                },
                "merchant": {
                    "id": str(expense.merchant.id) if expense.merchant else None,
                    "name": expense.merchant.name if expense.merchant else None
                },
                "payment_method": {
                    "id": str(expense.payment_method.id) if expense.payment_method else None,
                    "name": expense.payment_method.name if expense.payment_method else None
                },
                "account": {
                    "id": str(expense.account.id) if expense.account else None,
                    "name": expense.account.name if expense.account else None
                },
                "attachments": [
                    {
                        "id": str(attachment.id),
                        "filename": attachment.original_filename,
                        "type": attachment.attachment_type,
                        "size": attachment.file_size
                    }
                    for attachment in expense.attachments
                ],
                "created_at": expense.created_at.isoformat(),
                "updated_at": expense.updated_at.isoformat()
            }
            export_data["expenses"].append(expense_data)
        
        # Convert to JSON bytes
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        return json_content.encode('utf-8') 
   
    # ===== HELPER METHODS =====
    
    async def _get_filtered_expenses(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_ids: Optional[List[UUID]] = None,
        merchant_ids: Optional[List[UUID]] = None
    ) -> List[ExpenseTable]:
        """Get filtered expenses for export."""
        query = self.db.query(ExpenseTable).filter(
            ExpenseTable.user_id == user_id
        ).options(
            joinedload(ExpenseTable.category),
            joinedload(ExpenseTable.merchant),
            joinedload(ExpenseTable.payment_method),
            joinedload(ExpenseTable.account),
            joinedload(ExpenseTable.attachments)
        )
        
        # Apply date filters
        if date_from:
            query = query.filter(ExpenseTable.expense_date >= date_from)
        
        if date_to:
            query = query.filter(ExpenseTable.expense_date <= date_to)
        
        # Apply category filter
        if category_ids:
            query = query.filter(ExpenseTable.category_id.in_(category_ids))
        
        # Apply merchant filter
        if merchant_ids:
            query = query.filter(ExpenseTable.merchant_id.in_(merchant_ids))
        
        return query.order_by(desc(ExpenseTable.expense_date)).all()
    
    def _get_csv_headers(
        self,
        include_attachments: bool = False,
        include_notes: bool = True,
        custom_fields: Optional[List[str]] = None
    ) -> List[str]:
        """Get CSV headers based on export options."""
        headers = [
            "Date", "Amount", "Description", "Category", "Merchant", 
            "Payment Method", "Account"
        ]
        
        if include_notes:
            headers.append("Notes")
        
        if include_attachments:
            headers.extend(["Attachment Count", "Attachment Files"])
        
        if custom_fields:
            headers.extend(custom_fields)
        
        return headers
    
    def _format_expense_for_csv(
        self,
        expense: ExpenseTable,
        include_attachments: bool = False,
        include_notes: bool = True,
        custom_fields: Optional[List[str]] = None
    ) -> List[str]:
        """Format expense data for CSV row."""
        row = [
            expense.expense_date.strftime("%Y-%m-%d"),
            str(expense.amount),
            expense.description or "",
            expense.category.name if expense.category else "",
            expense.merchant.name if expense.merchant else "",
            expense.payment_method.name if expense.payment_method else "",
            expense.account.name if expense.account else ""
        ]
        
        if include_notes:
            row.append(expense.notes or "")
        
        if include_attachments:
            row.append(str(len(expense.attachments)))
            attachment_files = "; ".join([
                attachment.original_filename 
                for attachment in expense.attachments
            ])
            row.append(attachment_files)
        
        if custom_fields:
            # Add empty values for custom fields (would need implementation)
            row.extend([""] * len(custom_fields))
        
        return row
    
    def _create_expenses_worksheet(self, workbook, expenses: List[ExpenseTable]):
        """Create expenses worksheet in Excel."""
        worksheet = workbook.add_worksheet("Expenses")
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })
        
        cell_format = workbook.add_format({'border': 1})
        
        # Write headers
        headers = ["Date", "Amount", "Description", "Category", "Merchant", "Payment Method", "Account", "Notes"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        for row, expense in enumerate(expenses, 1):
            worksheet.write(row, 0, expense.expense_date, date_format)
            worksheet.write(row, 1, float(expense.amount), currency_format)
            worksheet.write(row, 2, expense.description or "", cell_format)
            worksheet.write(row, 3, expense.category.name if expense.category else "", cell_format)
            worksheet.write(row, 4, expense.merchant.name if expense.merchant else "", cell_format)
            worksheet.write(row, 5, expense.payment_method.name if expense.payment_method else "", cell_format)
            worksheet.write(row, 6, expense.account.name if expense.account else "", cell_format)
            worksheet.write(row, 7, expense.notes or "", cell_format)
        
        # Auto-adjust column widths
        worksheet.set_column('A:A', 12)  # Date
        worksheet.set_column('B:B', 12)  # Amount
        worksheet.set_column('C:C', 30)  # Description
        worksheet.set_column('D:G', 15)  # Category, Merchant, Payment Method, Account
        worksheet.set_column('H:H', 40)  # Notes
    
    def _create_summary_worksheet(self, workbook, expenses: List[ExpenseTable], date_from: Optional[date], date_to: Optional[date]):
        """Create summary worksheet in Excel."""
        worksheet = workbook.add_worksheet("Summary")
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'bg_color': '#D7E4BC'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F2F2F2',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        # Summary statistics
        total_amount = sum(expense.amount for expense in expenses)
        avg_amount = total_amount / len(expenses) if expenses else Decimal('0')
        
        # Write summary
        worksheet.write('A1', 'Expense Report Summary', title_format)
        worksheet.write('A3', 'Report Period:')
        worksheet.write('B3', f"{date_from or 'All time'} to {date_to or 'Present'}")
        worksheet.write('A4', 'Total Expenses:')
        worksheet.write('B4', len(expenses))
        worksheet.write('A5', 'Total Amount:')
        worksheet.write('B5', float(total_amount), currency_format)
        worksheet.write('A6', 'Average Amount:')
        worksheet.write('B6', float(avg_amount), currency_format)
        
        # Category breakdown
        category_totals = {}
        for expense in expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            category_totals[category] = category_totals.get(category, Decimal('0')) + expense.amount
        
        worksheet.write('A8', 'Category Breakdown', header_format)
        worksheet.write('A9', 'Category', header_format)
        worksheet.write('B9', 'Amount', header_format)
        worksheet.write('C9', 'Percentage', header_format)
        
        row = 10
        for category, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total_amount * 100) if total_amount > 0 else 0
            worksheet.write(row, 0, category)
            worksheet.write(row, 1, float(amount), currency_format)
            worksheet.write(row, 2, f"{percentage:.1f}%")
            row += 1
        
        # Auto-adjust column widths
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 12)
    
    def _create_charts_worksheet(self, workbook, expenses: List[ExpenseTable]):
        """Create charts worksheet in Excel."""
        worksheet = workbook.add_worksheet("Charts")
        
        # This would require additional chart creation logic
        # For now, just add a placeholder
        worksheet.write('A1', 'Charts and Visualizations')
        worksheet.write('A3', 'Chart functionality would be implemented here')
        worksheet.write('A4', 'with category pie charts and spending trends')
    
    def _add_pdf_header(self, story, styles, title: str, date_from: Optional[date], date_to: Optional[date], expense_count: int):
        """Add header section to PDF."""
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(title, title_style))
        
        # Report metadata
        metadata_style = styles['Normal']
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", metadata_style))
        story.append(Paragraph(f"<b>Period:</b> {date_from or 'All time'} to {date_to or 'Present'}", metadata_style))
        story.append(Paragraph(f"<b>Total Expenses:</b> {expense_count}", metadata_style))
        story.append(Spacer(1, 20))
    
    def _add_pdf_summary(self, story, styles, expenses: List[ExpenseTable]):
        """Add summary section to PDF."""
        story.append(Paragraph("Summary", styles['Heading2']))
        
        # Calculate summary statistics
        total_amount = sum(expense.amount for expense in expenses)
        avg_amount = total_amount / len(expenses) if expenses else Decimal('0')
        
        # Category breakdown
        category_totals = {}
        for expense in expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            category_totals[category] = category_totals.get(category, Decimal('0')) + expense.amount
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Amount', f"${total_amount:,.2f}"],
            ['Average Amount', f"${avg_amount:,.2f}"],
            ['Number of Expenses', str(len(expenses))]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
    
    def _add_pdf_charts(self, story, expenses: List[ExpenseTable]):
        """Add charts section to PDF."""
        story.append(Paragraph("Category Breakdown", styles['Heading2']))
        
        # Calculate category data for pie chart
        category_totals = {}
        for expense in expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            category_totals[category] = category_totals.get(category, Decimal('0')) + expense.amount
        
        # Create pie chart (simplified version)
        if category_totals:
            # Sort categories by amount
            sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            
            # Create table instead of actual chart for simplicity
            chart_data = [['Category', 'Amount', 'Percentage']]
            total_amount = sum(category_totals.values())
            
            for category, amount in sorted_categories:
                percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                chart_data.append([
                    category,
                    f"${amount:,.2f}",
                    f"{percentage:.1f}%"
                ])
            
            chart_table = Table(chart_data)
            chart_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(chart_table)
            story.append(Spacer(1, 20))
    
    def _add_pdf_expenses_table(self, story, styles, expenses: List[ExpenseTable]):
        """Add expenses table to PDF."""
        story.append(Paragraph("Expense Details", styles['Heading2']))
        
        # Create expenses table
        table_data = [['Date', 'Amount', 'Description', 'Category', 'Merchant']]
        
        for expense in expenses:
            table_data.append([
                expense.expense_date.strftime('%Y-%m-%d'),
                f"${expense.amount:,.2f}",
                expense.description or "",
                expense.category.name if expense.category else "",
                expense.merchant.name if expense.merchant else ""
            ])
        
        expenses_table = Table(table_data)
        expenses_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        
        story.append(expenses_table)
    
    def _add_pdf_expenses_by_category(self, story, styles, expenses: List[ExpenseTable]):
        """Add expenses grouped by category to PDF."""
        # Group expenses by category
        category_groups = {}
        for expense in expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(expense)
        
        # Add each category section
        for category, category_expenses in category_groups.items():
            story.append(Paragraph(f"Category: {category}", styles['Heading3']))
            
            # Category summary
            category_total = sum(expense.amount for expense in category_expenses)
            story.append(Paragraph(f"Total: ${category_total:,.2f} ({len(category_expenses)} expenses)", styles['Normal']))
            
            # Category expenses table
            table_data = [['Date', 'Amount', 'Description', 'Merchant']]
            
            for expense in category_expenses:
                table_data.append([
                    expense.expense_date.strftime('%Y-%m-%d'),
                    f"${expense.amount:,.2f}",
                    expense.description or "",
                    expense.merchant.name if expense.merchant else ""
                ])
            
            category_table = Table(table_data)
            category_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            
            story.append(category_table)
            story.append(Spacer(1, 15))
    
    def _group_expenses_for_tax(
        self, 
        expenses: List[ExpenseTable], 
        tax_categories: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, List[ExpenseTable]]:
        """Group expenses by tax-relevant categories."""
        if not tax_categories:
            # Default tax categories
            tax_categories = {
                "Business Meals": ["Food & Dining", "Restaurants"],
                "Travel": ["Travel", "Transportation", "Hotels"],
                "Office Supplies": ["Office Supplies", "Equipment"],
                "Professional Services": ["Professional Services", "Legal", "Accounting"],
                "Other Business": ["Business", "Professional"]
            }
        
        grouped = {"Uncategorized": []}
        
        for expense in expenses:
            category_name = expense.category.name if expense.category else None
            assigned = False
            
            for tax_category, category_names in tax_categories.items():
                if category_name in category_names:
                    if tax_category not in grouped:
                        grouped[tax_category] = []
                    grouped[tax_category].append(expense)
                    assigned = True
                    break
            
            if not assigned:
                grouped["Uncategorized"].append(expense)
        
        return grouped
    
    async def _export_tax_csv(self, grouped_expenses: Dict[str, List[ExpenseTable]], tax_year: int) -> bytes:
        """Export tax report as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Tax Category", "Date", "Amount", "Description", "Merchant", "Notes"])
        
        # Write grouped expenses
        for tax_category, expenses in grouped_expenses.items():
            for expense in expenses:
                writer.writerow([
                    tax_category,
                    expense.expense_date.strftime("%Y-%m-%d"),
                    str(expense.amount),
                    expense.description or "",
                    expense.merchant.name if expense.merchant else "",
                    expense.notes or ""
                ])
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content.encode('utf-8')
    
    async def _export_tax_excel(self, grouped_expenses: Dict[str, List[ExpenseTable]], tax_year: int) -> bytes:
        """Export tax report as Excel."""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Create summary worksheet
        summary_ws = workbook.add_worksheet("Tax Summary")
        
        # Formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        
        # Write summary
        summary_ws.write('A1', f'Tax Report - {tax_year}', header_format)
        summary_ws.write('A3', 'Tax Category', header_format)
        summary_ws.write('B3', 'Total Amount', header_format)
        summary_ws.write('C3', 'Expense Count', header_format)
        
        row = 4
        grand_total = Decimal('0')
        
        for tax_category, expenses in grouped_expenses.items():
            if expenses:  # Only include categories with expenses
                category_total = sum(expense.amount for expense in expenses)
                grand_total += category_total
                
                summary_ws.write(row, 0, tax_category)
                summary_ws.write(row, 1, float(category_total), currency_format)
                summary_ws.write(row, 2, len(expenses))
                row += 1
        
        # Grand total
        summary_ws.write(row + 1, 0, 'TOTAL', header_format)
        summary_ws.write(row + 1, 1, float(grand_total), currency_format)
        
        # Create detailed worksheets for each category
        for tax_category, expenses in grouped_expenses.items():
            if expenses:  # Only create sheets for categories with expenses
                ws = workbook.add_worksheet(tax_category[:31])  # Excel sheet name limit
                
                # Headers
                headers = ["Date", "Amount", "Description", "Merchant", "Notes"]
                for col, header in enumerate(headers):
                    ws.write(0, col, header, header_format)
                
                # Data
                for row, expense in enumerate(expenses, 1):
                    ws.write(row, 0, expense.expense_date.strftime("%Y-%m-%d"))
                    ws.write(row, 1, float(expense.amount), currency_format)
                    ws.write(row, 2, expense.description or "")
                    ws.write(row, 3, expense.merchant.name if expense.merchant else "")
                    ws.write(row, 4, expense.notes or "")
        
        workbook.close()
        output.seek(0)
        
        return output.read()
    
    async def _export_tax_pdf(self, grouped_expenses: Dict[str, List[ExpenseTable]], tax_year: int) -> bytes:
        """Export tax report as PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'TaxTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f"Tax Report - {tax_year}", title_style))
        
        # Summary
        story.append(Paragraph("Summary by Tax Category", styles['Heading2']))
        
        summary_data = [['Tax Category', 'Total Amount', 'Expense Count']]
        grand_total = Decimal('0')
        
        for tax_category, expenses in grouped_expenses.items():
            if expenses:
                category_total = sum(expense.amount for expense in expenses)
                grand_total += category_total
                summary_data.append([
                    tax_category,
                    f"${category_total:,.2f}",
                    str(len(expenses))
                ])
        
        summary_data.append(['TOTAL', f"${grand_total:,.2f}", ""])
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        ]))
        
        story.append(summary_table)
        story.append(PageBreak())
        
        # Detailed sections
        for tax_category, expenses in grouped_expenses.items():
            if expenses:
                story.append(Paragraph(f"Tax Category: {tax_category}", styles['Heading2']))
                
                category_total = sum(expense.amount for expense in expenses)
                story.append(Paragraph(f"Total: ${category_total:,.2f}", styles['Normal']))
                
                # Expenses table
                table_data = [['Date', 'Amount', 'Description', 'Merchant']]
                
                for expense in expenses:
                    table_data.append([
                        expense.expense_date.strftime('%Y-%m-%d'),
                        f"${expense.amount:,.2f}",
                        expense.description or "",
                        expense.merchant.name if expense.merchant else ""
                    ])
                
                expenses_table = Table(table_data)
                expenses_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 0), (-1, -1), 8)
                ]))
                
                story.append(expenses_table)
                story.append(Spacer(1, 20))
        
        doc.build(story)
        buffer.seek(0)
        
        return buffer.read()