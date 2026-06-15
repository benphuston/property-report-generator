#!/usr/bin/env python3
"""
Property Intelligence Report Generator
Generates branded PDF reports with property data and LMR eligibility
Deploy to Railway.app or similar serverless platform
"""

from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
import base64
import io
import os
from functools import wraps

app = Flask(__name__)

# Ground & Co branding colors
FOREST_GREEN = '#1C3B2C'
WARM_SAND = '#EDE8DC'

# Simple API key validation
API_KEY = os.getenv('API_KEY', 'dev-key-change-in-production')

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/generate-report', methods=['POST'])
def generate_report():
    """
    Generate a property intelligence report PDF

    Expected JSON payload:
    {
        "address": "123 Main Street, Sydney NSW 2000",
        "latitude": "-33.8688",
        "longitude": "151.2093",
        "eligibleForLMR": "Yes",
        "zone": "B2 Local Centre",
        "suburb": "Sydney",
        "postcode": "2000",
        "state": "NSW"
    }
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ['address', 'latitude', 'longitude', 'eligibleForLMR', 'zone', 'suburb', 'postcode', 'state']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({'success': False, 'error': f'Missing fields: {", ".join(missing)}'}), 400

        # Generate PDF
        pdf_bytes = _generate_pdf(data)

        # Encode to base64 for Make.com
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        return jsonify({
            'success': True,
            'pdf': pdf_base64,
            'filename': f"Property_Report_{data['postcode']}_{datetime.now().strftime('%Y%m%d')}.pdf",
            'size': len(pdf_bytes),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        app.logger.error(f"Report generation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _generate_pdf(data):
    """Generate PDF content and return bytes"""

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=FOREST_GREEN,
        spaceAfter=0.1*inch,
        spaceBefore=0.1*inch,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor='#666666',
        spaceAfter=0.3*inch,
        fontName='Helvetica'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=FOREST_GREEN,
        spaceAfter=0.15*inch,
        spaceBefore=0.15*inch,
        fontName='Helvetica-Bold'
    )

    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=FOREST_GREEN,
        spaceAfter=0.1*inch,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        textColor='#333333'
    )

    # === PAGE 1: HEADER & PROPERTY DETAILS ===

    # Title
    story.append(Paragraph("Property Intelligence Report", title_style))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%d %B %Y')}", subtitle_style))
    story.append(Spacer(1, 0.2*inch))

    # Property Details Table
    story.append(Paragraph("Property Details", heading_style))

    details_data = [
        ['Address:', data.get('address', 'N/A')],
        ['Suburb:', data.get('suburb', 'N/A')],
        ['Postcode:', data.get('postcode', 'N/A')],
        ['State:', data.get('state', 'N/A')],
        ['Coordinates:', f"{data.get('latitude', 'N/A')}, {data.get('longitude', 'N/A')}"]
    ]

    details_table = Table(details_data, colWidths=[1.5*inch, 4*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), WARM_SAND),
        ('TEXTCOLOR', (0, 0), (-1, -1), '#333333'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), ['white', '#F5F5F5']),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
    ]))

    story.append(details_table)
    story.append(Spacer(1, 0.3*inch))

    # === LMR ELIGIBILITY ===

    story.append(Paragraph("LMR (Low and Mid Rise) Housing Eligibility", heading_style))

    lmr_status = data.get('eligibleForLMR', 'Unknown')
    lmr_color = colors.HexColor('#2EAD36') if lmr_status == 'Yes' else colors.HexColor('#D32F2F')

    lmr_data = [
        ['Eligible for LMR Housing:', lmr_status],
        ['Planning Zone:', data.get('zone', 'N/A')]
    ]

    lmr_table = Table(lmr_data, colWidths=[2.2*inch, 3.3*inch])
    lmr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), WARM_SAND),
        ('TEXTCOLOR', (0, 0), (0, -1), '#333333'),
        ('TEXTCOLOR', (1, 0), (1, 0), lmr_color),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), ['white', '#F5F5F5']),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
    ]))

    story.append(lmr_table)
    story.append(Spacer(1, 0.3*inch))

    # === PLANNING ZONE INFORMATION ===

    story.append(Paragraph("Planning Zone Information", heading_style))

    zone = data.get('zone', 'General')
    zone_info = _get_zone_description(zone)
    story.append(Paragraph(zone_info, body_style))
    story.append(Spacer(1, 0.2*inch))

    # === WHAT THIS MEANS ===

    story.append(Paragraph("What This Means for Development", heading_style))

    if lmr_status == 'Yes':
        meaning = """
        <b>Positive Finding:</b> This property falls within an LMR (Low and Mid Rise) Housing catchment zone.
        This designation indicates that the NSW Government has identified the area as suitable for increased residential density
        through low and mid-rise development. Projects on this site may be eligible for streamlined assessment under the
        Housing SEPP, which can significantly reduce planning timeframes. This is often a positive signal for development feasibility.
        <br/><br/>
        <b>Key Implications:</b>
        <br/>• Eligible projects may bypass standard DA assessment
        <br/>• Faster approval pathway (typically 40-90 days vs. 12+ months)
        <br/>• Must comply with all applicable standards and controls
        <br/>• Strong housing demand support in the area
        """
    else:
        meaning = """
        <b>Standard Zone:</b> This property is not within an LMR Housing catchment zone. Development on this site may be subject
        to standard planning assessment processes under standard DAs or other applicable pathways. This does not necessarily mean
        development is more difficult—it simply means the project would follow the conventional assessment path.
        <br/><br/>
        <b>Key Implications:</b>
        <br/>• Standard DA assessment applies
        <br/>• Longer assessment timeframe expected
        <br/>• Compliance with standard local controls
        <br/>• May have heritage or other constraints
        """

    story.append(Paragraph(meaning, body_style))
    story.append(Spacer(1, 0.3*inch))

    # === PAGE BREAK ===
    story.append(PageBreak())

    # === PAGE 2: NEXT STEPS ===

    story.append(Paragraph("Next Steps for Development", heading_style))
    story.append(Spacer(1, 0.15*inch))

    next_steps = [
        ('1. Detailed Due Diligence',
         'Engage with a planning consultant to review the full planning controls, building codes, site constraints, '
         'and development potential. This is critical for understanding feasibility and timeline.'),

        ('2. Preliminary Design',
         'Develop concept designs that demonstrate compliance with applicable zoning, FSR, height limits, '
         'and other development standards. This shows viability to council and stakeholders.'),

        ('3. Stakeholder Engagement',
         'Understand local community concerns and engage early with council officers. Pre-lodgement consultation '
         'can significantly smooth the approval process and identify issues early.'),

        ('4. Environmental & Heritage Assessment',
         'Conduct any required studies including Aboriginal heritage, ecology, contaminated land, flooding, '
         'and traffic impact. These are essential for the DA.'),

        ('5. Pre-lodgement Meeting',
         'Meet with council planning team before formal DA lodgement to discuss your proposal, get feedback, '
         'and identify any critical issues that need addressing.'),

        ('6. Financial Planning',
         'Consider development costs, financing options, timeline expectations, and return on investment. '
         'Consult with quantity surveyors and financial advisors.'),
    ]

    for step_num, (title, desc) in enumerate(next_steps, 1):
        story.append(Paragraph(title, section_heading_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 0.15*inch))

    story.append(Spacer(1, 0.2*inch))

    # === CONTACT & DISCLAIMER ===

    story.append(Paragraph("Questions?", heading_style))

    contact_text = """
    For more information about this property or to discuss potential development opportunities,
    visit <b>ground.com.au</b> or contact our team.
    <br/><br/>
    <b>Disclaimer:</b> This report is for informational purposes only and does not constitute legal or planning advice.
    While we have used publicly available data sources (NSW Government spatial data, council planning information),
    the accuracy and completeness of this information cannot be guaranteed. Always consult with qualified planning
    professionals, lawyers, and other specialists before making development decisions or investments.
    The planning and zoning information in this report should be verified with the relevant local council
    and may change over time.
    <br/><br/>
    <font size=8>Report Generated: {date} | Property: {address} | Data Sources: NSW Spatial Services</font>
    """.format(
        date=datetime.now().strftime('%d %B %Y at %H:%M'),
        address=data.get('address', 'N/A')
    )

    story.append(Paragraph(contact_text, body_style))

    # Build PDF
    doc.build(story)

    return pdf_buffer.getvalue()

def _get_zone_description(zone):
    """Return description for common NSW planning zones"""

    zone_descriptions = {
        'B2 Local Centre': 'B2 Local Centre zones are intended for mixed-use development including shops, offices, and residential.',
        'B3 Commercial Core': 'B3 Commercial Core zones are intended for high-density commercial development.',
        'B4 Mixed Use': 'B4 Mixed Use zones encourage a mix of residential, retail, entertainment, and cultural uses.',
        'R1 General Residential': 'R1 General Residential zones are for low-density residential development.',
        'R2 Low Density Residential': 'R2 Low Density Residential zones are for low-rise residential development.',
        'R3 Medium Density Residential': 'R3 Medium Density Residential zones are for medium-density housing.',
        'R4 High Density Residential': 'R4 High Density Residential zones are for high-density residential development.',
        'SP2 Infrastructure': 'SP2 Infrastructure zones are for essential services and public facilities.',
    }

    for zone_key, description in zone_descriptions.items():
        if zone_key.lower() in zone.lower():
            return description

    return f"{zone} is a planning zone with specific development controls. Consult with your planning consultant for detailed requirements."

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Development
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
