"""PDF report generation for job offer analysis."""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors


def generate_pdf_report(analysis: dict, offer_text: str = None) -> bytes:
    """Generate PDF report from analysis results."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0f1d33'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0f1d33'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Color based on risk level
    label = analysis.get('label', 'Unknown')
    if label == 'Looks Safe':
        score_color = colors.HexColor('#0b7a6b')
    elif label == 'Suspicious':
        score_color = colors.HexColor('#a85d00')
    else:
        score_color = colors.HexColor('#b3261e')
    
    story = []
    
    # Title
    story.append(Paragraph("JobTruth Analysis Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Score section
    score = analysis.get('trust_score', 0)
    story.append(Paragraph("Trust Score", heading_style))
    score_data = [
        ['Score', 'Result', 'Risk Level'],
        [f'{score}/100', label, 'High Risk' if score < 40 else 'Suspicious' if score < 70 else 'Safe']
    ]
    score_table = Table(score_data, colWidths=[1.5*inch, 2*inch, 1.5*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f1d33')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('TEXTCOLOR', (0, 1), (0, 1), score_color),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, 1), 14),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Flags section
    flags = analysis.get('flags', [])
    if flags:
        story.append(Paragraph("Warning Signs Found", heading_style))
        flag_data = [['Impact', 'Reason']]
        for flag in flags:
            impact = flag.get('impact', 0)
            reason = flag.get('reason', '')
            impact_str = f"+{impact}" if impact > 0 else f"{impact}"
            flag_data.append([impact_str, reason[:60]])
        
        flag_table = Table(flag_data, colWidths=[1*inch, 4*inch])
        flag_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f1d33')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f5f8')]),
        ]))
        story.append(flag_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Disclaimer
    story.append(Paragraph("Disclaimer", heading_style))
    story.append(Paragraph(
        "JobTruth shows risk indicators, not proof. Always verify a company on its official website and never pay money to get a job. "
        "This report is for informational purposes only.",
        normal_style
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
