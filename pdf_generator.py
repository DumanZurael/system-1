from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os

try:
    # ניסיון להשתמש בפונט עברי אם קיים
    hebrew_font_path = "fonts/ArialHB.ttf"
    if os.path.exists(hebrew_font_path):
        pdfmetrics.registerFont(TTFont('Hebrew', hebrew_font_path))
        DEFAULT_FONT = 'Hebrew'
    else:
        # אם אין פונט עברי, נשתמש בפונט ברירת מחדל
        DEFAULT_FONT = 'Helvetica'
except:
    DEFAULT_FONT = 'Helvetica'

def create_schedule_pdf(schedule, filename="schedule.pdf"):
    """יצירת קובץ PDF של לוח המשמרות"""
    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont(DEFAULT_FONT, 14)
    
    # כותרת
    c.drawString(50, 800, "Weekly Schedule - Shkedia")
    
    y_position = 750
    for day, shifts in schedule.items():
        # כותרת היום
        c.setFont(DEFAULT_FONT, 12)
        c.drawString(50, y_position, f"{day}:")
        y_position -= 20
        
        for i, shift in enumerate(shifts):
            shift_type = "Morning Shift" if i == 0 else "Evening Shift"
            c.setFont(DEFAULT_FONT, 10)
            # פרטי המשמרת
            c.drawString(70, y_position, 
                        f"{shift_type}: {shift['start_time']} - {shift['end_time']}")
            
            # רשימת העובדים
            employees_str = ", ".join(shift['employees']) if shift['employees'] else "Not assigned"
            c.drawString(70, y_position - 15, f"Employees: {employees_str}")
            
            y_position -= 40
            
        y_position -= 10
        
        # מעבר לעמוד חדש אם אין מספיק מקום
        if y_position < 50:
            c.showPage()
            c.setFont(DEFAULT_FONT, 14)
            y_position = 750
    
    c.save()
    return filename 