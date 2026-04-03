from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime
import io

class AuditReportGenerator:
    @staticmethod
    def generate_monthly_bias_report(audit_summary: dict) -> bytes:
        """
        Generates a monthly bias audit PDF report.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"Monthly Bias & Fairness Audit Report - {datetime.now().strftime('%B %Y')}", styles['Title']))
        elements.append(Spacer(1, 12))

        # Executive Summary
        elements.append(Paragraph("Executive Summary", styles['Heading2']))
        summary_text = f"Total screenings conducted: {audit_summary.get('total_screenings', 0)}. " \
                       f"Overall bias risk detected: {audit_summary.get('overall_risk', 'LOW')}. "
        elements.append(Paragraph(summary_text, styles['Normal']))
        elements.append(Spacer(1, 12))

        # Flagged Decisions Table
        elements.append(Paragraph("Flagged Feedback & Bias Exceptions", styles['Heading3']))
        data = [["Category", "Frequency", "Impact Level"]]
        for flag, count in audit_summary.get("flag_frequency", {}).items():
            data.append([flag, str(count), "MED"])
        
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 24))

        # Recommendations
        elements.append(Paragraph("Recommendations for Improvement", styles['Heading2']))
        recs = audit_summary.get("recommendations", [
            "Increase anonymization usage for early-stage screening.",
            "Regularly update the skills ontology to include emerging synonyms."
        ])
        for r in recs:
            elements.append(Paragraph(f"• {r}", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
