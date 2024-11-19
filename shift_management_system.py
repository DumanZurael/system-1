from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
import json
from collections import OrderedDict

class User:
    def __init__(self, username: str, password: str = None, first_name: str = "", last_name: str = "", 
                 email: str = "", phone: str = "", id_number: str = "", 
                 employee_number: str = "", is_admin: bool = False):
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.id_number = id_number
        self.employee_number = employee_number
        self.is_admin = is_admin
        
    def to_dict(self):
        """המרת המשתמש למילון"""
        return {
            'username': self.username,
            'password': self.password,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'id_number': self.id_number,
            'employee_number': self.employee_number,
            'is_admin': self.is_admin
        }

    @staticmethod
    def from_dict(data):
        """יצירת משתמש ממילון"""
        return User(
            username=data.get('username', ''),
            password=data.get('password', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            id_number=data.get('id_number', ''),
            employee_number=data.get('employee_number', ''),
            is_admin=data.get('is_admin', False)
        )

class Shift:
    def __init__(self, start_time: time, end_time: time):
        self.start_time = start_time
        self.end_time = end_time
        self.employees = []

    def add_employee(self, employee: str):
        if employee not in self.employees:
            self.employees.append(employee)
            return True
        return False

    def remove_employee(self, employee: str):
        if employee in self.employees:
            self.employees.remove(employee)
            return True
        return False

class Permission:
    VIEW_SCHEDULE = 1
    EDIT_SCHEDULE = 2
    MANAGE_EMPLOYEES = 4
    ADMIN = 8

class Role:
    def __init__(self, name, permissions):
        self.name = name
        self.permissions = permissions

ROLES = {
    'viewer': Role('viewer', Permission.VIEW_SCHEDULE),
    'manager': Role('manager', Permission.VIEW_SCHEDULE | Permission.EDIT_SCHEDULE),
    'admin': Role('admin', Permission.VIEW_SCHEDULE | Permission.EDIT_SCHEDULE | 
                          Permission.MANAGE_EMPLOYEES | Permission.ADMIN)
}

class ShiftAppeal:
    """מחלקה המייצגת ערעור על משמרת"""
    def __init__(self, employee: str, day: str, shift_index: int, reason: str):
        self.employee = employee
        self.day = day
        self.shift_index = shift_index
        self.reason = reason
        self.status = 'pending'  # pending, approved, rejected
        self.admin_response = ''
        self.created_at = datetime.now()

    def to_dict(self):
        """המרת הערעור למילון"""
        return {
            'employee': self.employee,
            'day': self.day,
            'shift_index': self.shift_index,
            'reason': self.reason,
            'status': self.status,
            'admin_response': self.admin_response,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        """יצירת ערעור ממילון"""
        appeal = cls(
            data['employee'],
            data['day'],
            data['shift_index'],
            data['reason']
        )
        appeal.status = data['status']
        appeal.admin_response = data['admin_response']
        appeal.created_at = datetime.fromisoformat(data['created_at'])
        return appeal

class ShiftManagementSystem:
    def __init__(self):
        self.users = {}
        self.shifts_history = {}  # מילון לשמירת היסטוריית משמרות
        self.weekly_shifts = {}
        self.appeals = []  # רשימת הערעורים
        self.initialize_shifts()
    
    def get_israel_time(self):
        """קבלת התאריך והשעה הנוכחיים בישראל"""
        try:
            import pytz
            israel_tz = pytz.timezone('Asia/Jerusalem')
            return datetime.now(israel_tz)
        except ImportError:
            # אם אין pytz, נחזיר את הזמן המקומי
            return datetime.now()
    
    def initialize_shifts(self):
        """אתחול מערכת המשמרות עם תאריכים לפי זמן ישראל"""
        israel_today = self.get_israel_time().date()
        
        # התאמה לשבוע הישראלי (0 = יום ראשון)
        israel_weekday = (israel_today.weekday() + 1) % 7  # המרה ללוח השבועי הישראלי
        start_of_week = israel_today - timedelta(days=israel_weekday)
        
        days_hebrew = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
        
        for i in range(7):
            current_date = start_of_week + timedelta(days=i)
            # יצירת מפתח עם התאריך המלא
            formatted_date = current_date.strftime('%d/%m/%Y')
            date_key = f"{days_hebrew[i]} {formatted_date}"
            
            self.weekly_shifts[date_key] = []
            morning_shift = Shift(time(8, 0), time(16, 0))
            evening_shift = Shift(time(16, 0), time(23, 0))
            self.weekly_shifts[date_key].extend([morning_shift, evening_shift])

    def get_weekly_schedule(self, week_offset: int = 0) -> Dict:
        """קבלת לוח המשמרות השבועי לפי זמן ישראל"""
        israel_today = self.get_israel_time().date()
        
        # התאמה לשבוע הישראלי (0 = יום ראשון)
        israel_weekday = (israel_today.weekday() + 1) % 7  # המרה ללוח השבועי הישראלי
        start_of_current_week = israel_today - timedelta(days=israel_weekday)
        target_week = start_of_current_week - timedelta(weeks=week_offset)
        
        schedule = OrderedDict()
        days_hebrew = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
        
        for i in range(7):
            current_date = target_week + timedelta(days=i)
            # יצירת מפתח עם התאריך המלא
            formatted_date = current_date.strftime('%d/%m/%Y')
            date_key = f"{days_hebrew[i]} {formatted_date}"
            
            if date_key in self.shifts_history:
                shifts = self.shifts_history[date_key]
            elif week_offset == 0 and date_key in self.weekly_shifts:
                shifts = self.weekly_shifts[date_key]
            else:
                shifts = []
            
            schedule[date_key] = []
            for shift in shifts:
                schedule[date_key].append({
                    'start_time': shift.start_time.strftime('%H:%M'),
                    'end_time': shift.end_time.strftime('%H:%M'),
                    'employees': shift.employees
                })
        
        return schedule

    def get_hebrew_date(self, date):
        """המרת תאריך לועזי לעברי"""
        try:
            from hebrew_dates import GregorianDate, HebrewDate
            g_date = GregorianDate(date.year, date.month, date.day)
            h_date = HebrewDate.from_gregorian(g_date)
            return h_date.hebrew_date_string()
        except ImportError:
            # אם הספריה לא מותקנת, נחזיר רק את התאריך הלועזי
            return date.strftime('%d/%m/%Y')

    def get_monthly_schedule(self, month_offset: int = 0) -> Dict:
        """קבלת לוח המשמרות החודשי"""
        today = datetime.now().date()
        # מוצאים את היום הראשון בחודש
        first_of_month = today.replace(day=1) - timedelta(days=today.day - 1)
        target_month = first_of_month - timedelta(days=30 * month_offset)
        
        schedule = OrderedDict()
        current_date = target_month
        
        # מחשבים את מספר הימים בחודש
        if target_month.month == 12:
            next_month = target_month.replace(year=target_month.year + 1, month=1)
        else:
            next_month = target_month.replace(month=target_month.month + 1)
        days_in_month = (next_month - target_month).days
        
        days = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
        
        for _ in range(days_in_month):
            date_key = current_date.strftime('%Y-%m-%d')
            day_name = days[current_date.weekday()]
            date_display = f"{day_name} {current_date.strftime('%d/%m')}"
            
            if date_key in self.shifts_history:
                shifts = self.shifts_history[date_key]
            elif month_offset == 0 and date_key in self.weekly_shifts:
                shifts = self.weekly_shifts[date_key]
            else:
                shifts = []
            
            schedule[date_display] = []
            for shift in shifts:
                schedule[date_display].append({
                    'start_time': shift.start_time.strftime('%H:%M'),
                    'end_time': shift.end_time.strftime('%H:%M'),
                    'employees': shift.employees
                })
            
            current_date += timedelta(days=1)
        
        return schedule

    def archive_current_week(self):
        """שמירת המשמרות הנוכחיות בהיסטוריה"""
        for date_key, shifts in self.weekly_shifts.items():
            self.shifts_history[date_key] = shifts.copy()

    def add_user(self, admin_username: str, new_username: str, is_admin: bool = False) -> bool:
        """הוספת משתמש חדש למערכת"""
        if admin_username not in self.users or not self.users[admin_username].is_admin:
            return False
        
        if new_username in self.users:
            return False
            
        self.users[new_username] = User(new_username, is_admin)
        return True
    
    def update_shift_hours(self, admin_username: str, day: str, 
                          shift_index: int, new_start: time, new_end: time) -> bool:
        """עדכון שעות משמרת"""
        if admin_username not in self.users or not self.users[admin_username].is_admin:
            return False
            
        if day not in self.weekly_shifts:
            return False
            
        if shift_index >= len(self.weekly_shifts[day]):
            return False
            
        shift = self.weekly_shifts[day][shift_index]
        shift.start_time = new_start
        shift.end_time = new_end
        return True
    
    def is_employee_available(self, day: str, employee_username: str) -> bool:
        """בדיקה האם העובד זמין ביום מסוים"""
        if day not in self.weekly_shifts:
            return False
        
        # בדיקה אם העובד כבר משובץ באחת המשמרות של אותו יום
        for shift in self.weekly_shifts[day]:
            if employee_username in shift.employees:
                return False
        return True
    
    def assign_shift(self, admin_username: str, day: str, 
                    shift_index: int, employee_username: str) -> bool:
        """שיבוץ עובד למשמרת"""
        if admin_username not in self.users or not self.users[admin_username].is_admin:
            return False
            
        if day not in self.weekly_shifts:
            return False
            
        if shift_index >= len(self.weekly_shifts[day]):
            return False
            
        if employee_username not in self.users:
            return False

        # בדיקה אם העובד כבר משובץ ביום זה
        if not self.is_employee_available(day, employee_username):
            return False
            
        return self.weekly_shifts[day][shift_index].add_employee(employee_username)
    
    def remove_from_shift(self, admin_username: str, day: str,
                         shift_index: int, employee_username: str) -> bool:
        """הסרת עובד ממשמרת"""
        if admin_username not in self.users or not self.users[admin_username].is_admin:
            return False
            
        if day not in self.weekly_shifts:
            return False
            
        if shift_index >= len(self.weekly_shifts[day]):
            return False
            
        return self.weekly_shifts[day][shift_index].remove_employee(employee_username)
    
    def save_to_file(self, filename: str):
        """שמירת נתוני המערכת לקובץ"""
        data = {
            'users': {
                username: user.to_dict() for username, user in self.users.items()
            },
            'shifts': {
                day: [{
                    'start': shift.start_time.strftime('%H:%M'),
                    'end': shift.end_time.strftime('%H:%M'),
                    'employees': shift.employees
                } for shift in shifts]
                for day, shifts in self.weekly_shifts.items()
            },
            'appeals': [
                {
                    'employee': appeal.employee,
                    'day': appeal.day,
                    'shift_index': appeal.shift_index,
                    'reason': appeal.reason,
                    'status': appeal.status,
                    'admin_response': appeal.admin_response,
                    'created_at': appeal.created_at.isoformat()
                }
                for appeal in self.appeals
            ]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filename: str):
        """טעינת נתוני המערכת מקובץ"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # טעינת משתמשים
        self.users = {}
        for username, user_data in data['users'].items():
            self.users[username] = User.from_dict({
                'username': username,
                **user_data
            })
        
        # טעינת משמרות
        self.weekly_shifts = {}
        for day, shifts_data in data.get('shifts', {}).items():
            self.weekly_shifts[day] = []
            for shift_data in shifts_data:
                start = datetime.strptime(shift_data['start'], '%H:%M').time()
                end = datetime.strptime(shift_data['end'], '%H:%M').time()
                shift = Shift(start, end)
                shift.employees = shift_data.get('employees', [])
                self.weekly_shifts[day].append(shift)
        
        # טעינת ערעורים
        self.appeals = []
        for appeal_data in data.get('appeals', []):
            appeal = ShiftAppeal(
                appeal_data['employee'],
                appeal_data['day'],
                appeal_data['shift_index'],
                appeal_data['reason']
            )
            appeal.status = appeal_data['status']
            appeal.admin_response = appeal_data['admin_response']
            appeal.created_at = datetime.fromisoformat(appeal_data['created_at'])
            self.appeals.append(appeal)

    def auto_backup(self):
        """יצירת גיבוי אוטומטי"""
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.save_to_file(f"backups/{backup_filename}")
    
    def create_appeal(self, employee: str, day: str, shift_index: int, reason: str) -> tuple[bool, str]:
        """יצירת ערעור חדש על משמרת"""
        try:
            # בדיקה שהעובד אכן משובץ במשמרת
            if day in self.weekly_shifts:
                shift = self.weekly_shifts[day][shift_index]
                if employee in shift.employees:
                    # בדיקה אם כבר קיים ערעור על משמרת זו
                    for appeal in self.appeals:
                        if (appeal.employee == employee and 
                            appeal.day == day and 
                            appeal.shift_index == shift_index and 
                            appeal.status == 'pending'):
                            return False, "כבר קיים ערעור על משמרת זו"
                    
                    # יצירת ערעור חדש
                    appeal = ShiftAppeal(employee, day, shift_index, reason)
                    self.appeals.append(appeal)
                    print(f"Created new appeal: {employee} for {day}")  # לוג
                    self.save_to_file('schedule.json')  # שמירת השינויים
                    return True, "הערעור נשלח בהצלחה"
            return False, "לא ניתן להגיש ערעור על משמרת זו"
        except Exception as e:
            print(f"Error creating appeal: {str(e)}")  # לוג שגיאה
            return False, f"אירעה שגיאה: {str(e)}"
    
    def handle_appeal(self, appeal_index: int, admin_decision: str, admin_response: str = '') -> bool:
        """טיפול בערעור על ידי מנהל"""
        if 0 <= appeal_index < len(self.appeals):
            appeal = self.appeals[appeal_index]
            appeal.status = admin_decision
            appeal.admin_response = admin_response
            return True
        return False
    
    def get_pending_appeals(self) -> list:
        """קבלת רשימת הערעורים הממתינים"""
        return [appeal for appeal in self.appeals if appeal.status == 'pending']
    
    def get_employee_appeals(self, employee: str) -> list:
        """קבלת רשימת הערעורים של עובד מסוים"""
        return [appeal for appeal in self.appeals if appeal.employee == employee]
    
    def add_notification(self, username: str, message: str, notification_type: str):
        """הוספת התראה למשתמש"""
        if not hasattr(self, 'notifications'):
            self.notifications = {}
        
        if username not in self.notifications:
            self.notifications[username] = []
        
        self.notifications[username].append({
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now(),
            'read': False
        })
    
    def get_user_notifications(self, username: str) -> list:
        """קבלת התראות של משתמש"""
        if not hasattr(self, 'notifications') or username not in self.notifications:
            return []
        return self.notifications[username]
    
    def has_active_appeal(self, employee: str, day: str, shift_index: int) -> tuple[bool, str, str]:
        """בדיקה אם יש ערעור פעיל או נדחה למשמרת"""
        for appeal in self.appeals:
            if (appeal.employee == employee and 
                appeal.day == day and 
                appeal.shift_index == shift_index):
                if appeal.status == 'pending':
                    return True, 'pending', ''
                elif appeal.status == 'rejected':
                    return True, 'rejected', appeal.admin_response
        return False, '', ''

if __name__ == "__main__":
    # אם מריצים את הקובץ הזה ישירות, לא יקר כלום
    # צריך להריץ את shift_management_demo.py
    print("זהו מודול המכיל את הלוגיקה של המערכת.")
    print("כדי להריץ את המערכת, הרץ את הקובץ shift_management_demo.py")
