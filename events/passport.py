"""Event Passport queries and certificate rendering."""
from io import BytesIO
import os
from collections import Counter

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import Event, AttendanceRecord


def attended_events(user):
    """One row per event with both a current registration and a recorded check-in."""
    return Event.objects.filter(
        registrations__user=user, registrations__status='confirmed',
        attendance_sessions__records__user=user, attendance_sessions__records__status='present',
    ).select_related('category', 'organizer').distinct().order_by('-date', '-time', '-pk')


def category_summary(events):
    counts = Counter(event.category.name if event.category else 'Other' for event in events)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))


def certificate_is_valid(certificate):
    reg = certificate.registration
    return (reg.status == 'confirmed' and reg.event.certificates_enabled and reg.event.status != 'cancelled'
            and AttendanceRecord.objects.filter(session__event=reg.event, user=reg.user, status='present').exists())


def pdf_font():
    # Register a Unicode font when available; the core PDF font is a fallback.
    font_candidates = [r'C:\\Windows\\Fonts\\arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                       '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    if 'PassportText' in pdfmetrics.getRegisteredFontNames():
        return 'PassportText'
    for path in font_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('PassportText', path))
                return 'PassportText'
            except (OSError, ValueError):
                continue
    return 'Helvetica'


def certificate_pdf(certificate, verification_url):
    output = BytesIO()
    doc = canvas.Canvas(output, pagesize=landscape(A4))
    width, height = landscape(A4)
    font = pdf_font()
    doc.setTitle('Certificate of Participation')
    doc.setFillColor(colors.HexColor('#f2faff'))
    doc.rect(0, 0, width, height, fill=1, stroke=0)
    doc.setStrokeColor(colors.HexColor('#a9d5e5'))
    doc.setLineWidth(2)
    doc.roundRect(26, 26, width - 52, height - 52, 16, fill=0, stroke=1)
    doc.setFillColor(colors.HexColor('#254e63'))
    doc.setFont(font, 13)
    doc.drawCentredString(width / 2, height - 75, 'EVENTEASE  /  CAMPUS EVENT PASSPORT')
    doc.setFont(font, 30)
    doc.drawCentredString(width / 2, height - 132, 'Certificate of Participation')
    doc.setFillColor(colors.HexColor('#64828d'))
    doc.setFont(font, 13)
    doc.drawCentredString(width / 2, height - 175, 'This certificate is presented to')
    doc.setFillColor(colors.HexColor('#17394f'))
    doc.setFont(font, 27)
    for i, line in enumerate(simpleSplit(certificate.attendee_name, font, 27, width - 130)[:2]):
        doc.drawCentredString(width / 2, height - 218 - i * 34, line)
    doc.setFillColor(colors.HexColor('#64828d'))
    doc.setFont(font, 13)
    doc.drawCentredString(width / 2, height - 292, 'for attending')
    doc.setFillColor(colors.HexColor('#245b70'))
    doc.setFont(font, 20)
    for i, line in enumerate(simpleSplit(certificate.event_title, font, 20, width - 150)[:2]):
        doc.drawCentredString(width / 2, height - 326 - i * 25, line)
    doc.setFillColor(colors.HexColor('#64828d'))
    doc.setFont(font, 12)
    doc.drawCentredString(width / 2, height - 390, certificate.event_date.strftime('%B %d, %Y'))
    qr = qrcode.make(verification_url)
    image = BytesIO()
    qr.save(image, format='PNG')
    image.seek(0)
    doc.drawImage(ImageReader(image), width - 150, 48, width=78, height=78, mask='auto')
    doc.setFont(font, 8)
    doc.drawString(60, 95, 'CERTIFICATE ID')
    doc.setFont(font, 9)
    doc.drawString(60, 79, str(certificate.pk))
    doc.setFont(font, 8)
    doc.drawString(60, 62, 'Scan the QR code or click here to verify this certificate.')
    doc.linkURL(verification_url, (60, 58, 315, 72), relative=0, thickness=0)
    doc.showPage()
    doc.save()
    output.seek(0)
    return output
