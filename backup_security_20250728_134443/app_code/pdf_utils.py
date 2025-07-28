"""
Utilitários para geração e formatação de PDFs
"""
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
import io

def create_pdf_styles():
    """Cria estilos padrão para PDFs"""
    styles = getSampleStyleSheet()
    
    # Estilo para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Estilo para células da tabela
    cell_style = ParagraphStyle(
        'TableCell',
        fontSize=9,
        alignment=TA_CENTER,
        wordWrap='CJK',
        leftIndent=2,
        rightIndent=2,
        spaceBefore=2,
        spaceAfter=2
    )
    
    # Estilo para texto longo
    long_text_style = ParagraphStyle(
        'LongText',
        fontSize=8,
        alignment=TA_LEFT,
        wordWrap='CJK',
        leftIndent=4,
        rightIndent=4,
        spaceBefore=1,
        spaceAfter=1
    )
    
    return {
        'title': title_style,
        'cell': cell_style,
        'long_text': long_text_style,
        'normal': styles['Normal']
    }

def create_table_with_wrapping(data, col_widths=None, styles=None):
    """Cria tabela com quebra de linha automática"""
    if not styles:
        styles = create_pdf_styles()
    
    # Converter dados para Paragraphs quando necessário
    processed_data = []
    for row in data:
        processed_row = []
        for i, cell in enumerate(row):
            if isinstance(cell, str):
                # Usar estilo apropriado baseado no tamanho do texto
                style = styles['long_text'] if len(cell) > 50 else styles['cell']
                processed_row.append(Paragraph(cell, style))
            else:
                processed_row.append(cell)
        processed_data.append(processed_row)
    
    # Criar tabela
    table = Table(processed_data, colWidths=col_widths, repeatRows=1)
    
    # Aplicar estilo
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return table

def format_hours(hours):
    """Formata horas decimais para HH:MM"""
    if hours is None:
        return "00:00"
    
    total_hours = int(hours)
    minutes = int((hours - total_hours) * 60)
    return f"{total_hours:02d}:{minutes:02d}"
