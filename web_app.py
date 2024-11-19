from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, flash
from functools import wraps
import secrets
from shift_management_system import ShiftManagementSystem, User
from datetime import time, datetime
from pdf_generator import create_schedule_pdf
import os

app = Flask(__name__)
system = ShiftManagementSystem()

# יצירת מנהל ראשי עם פרטים קבועים
admin_user = User(
    username='admin',
    password='admin123',  # הגדרת סיסמה קבועה
    first_name='מנהל',
    last_name='ראשי',
    is_admin=True
)

# הוספת המנהל למערכת
system.users['admin'] = admin_user

# הוספת משתמש לדוגמה
demo_user = User(
    username='yossi',
    password='1234',
    first_name='יוסי',
    last_name='כהן',
    email='yossi@example.com',
    phone='0501234567',
    employee_number='1001',
    is_admin=False
)
system.users['yossi'] = demo_user

# שמירת הנתונים
if not os.path.exists('schedule.json'):
    system.save_to_file('schedule.json')
    print("Created new admin account and demo user")
else:
    try:
        system.load_from_file('schedule.json')
        # וידוא שהמנהל קיים עם הסיסמה הנכונה
        if 'admin' not in system.users:
            system.users['admin'] = admin_user
            system.save_to_file('schedule.json')
        elif system.users['admin'].password != 'admin123':
            system.users['admin'].password = 'admin123'
            system.save_to_file('schedule.json')
    except Exception as e:
        print(f"Error loading data: {str(e)}")

# הוספת מפתח סודי לשמירת הסשן
app.secret_key = secrets.token_hex(16)

# פונקציית עזר לבדיקת התחברות
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in system.users and system.users[username].password == password:
            session['username'] = username
            if system.users[username].is_admin:
                return redirect(url_for('index'))
            else:
                return redirect(url_for('user_schedule'))
        else:
            return render_template('login.html', error='שם משתמש או סיסמה שגויים')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/user_schedule')
@login_required
def user_schedule():
    try:
        username = session['username']
        if username not in system.users:
            return redirect(url_for('login'))
        
        view_type = request.args.get('view', 'week')
        week_offset = int(request.args.get('week_offset', 0))
        
        # קבלת התאריך הנוכחי בישראל
        israel_time = system.get_israel_time()
        current_date = israel_time.strftime('%d/%m/%Y')
        current_time = israel_time.strftime('%H:%M')
        
        if view_type == 'month':
            schedule = system.get_monthly_schedule(week_offset // 4)
        else:
            schedule = system.get_weekly_schedule(week_offset)
        
        user_shifts = {}
        for day, shifts in schedule.items():
            user_shifts[day] = []
            for shift in shifts:
                if username in shift['employees']:
                    user_shifts[day].append(shift)
        
        max_history_weeks = 4
        
        return render_template('user_schedule.html', 
                             user_schedule=user_shifts,
                             system=system,
                             username=username,
                             current_week_offset=week_offset,
                             max_history_weeks=max_history_weeks,
                             view_type=view_type,
                             current_date=current_date,
                             current_time=current_time)
    except Exception as e:
        print(f"Error in user_schedule: {str(e)}")  # לוג השגיאה
        flash('אירעה שגיאה בטעינת לוח המשמרות', 'error')
        return redirect(url_for('login'))

@app.route('/download_user_schedule')
@login_required
def download_user_schedule():
    username = session['username']
    schedule = system.get_weekly_schedule()
    user_shifts = {}
    
    # יצירת לוח משמרות אישי
    for day, shifts in schedule.items():
        user_shifts[day] = []
        for shift in shifts:
            if username in shift['employees']:
                user_shifts[day].append({
                    'start_time': shift['start_time'],
                    'end_time': shift['end_time'],
                    'employees': [username]  # רק העובד הנוכחי
                })
    
    # יצירת שם קובץ ייחודי לעובד
    filename = f"schedule_{username}_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_file = create_schedule_pdf(user_shifts, filename)
    return send_file(pdf_file, as_attachment=True)

# עדכון הראוט הראשי להיות מגן
@app.route('/')
@login_required
def index():
    if not session.get('username') or not system.users[session['username']].is_admin:
        return redirect(url_for('user_schedule'))
    
    view_type = request.args.get('view', 'week')
    week_offset = int(request.args.get('week_offset', 0))
    
    schedule = system.get_weekly_schedule(week_offset)
    
    # שינוי בהכנת רשימת העובדים
    employees = []
    for username, user in system.users.items():
        if not user.is_admin:  # רק עובדים רגילים, לא מנהלים
            employees.append({
                'username': username,
                'display_name': f"{user.first_name} {user.last_name}".strip(),
                'first_name': user.first_name,
                'last_name': user.last_name
            })
    
    # הוספת מספר הערעורים הממתינים
    pending_appeals_count = len(system.get_pending_appeals())
    
    return render_template('index.html',
                         schedule=schedule,
                         employees=employees,  # העברת רשימת העובדים המעודכנת
                         system=system,
                         current_week_offset=week_offset,
                         view_type=view_type,
                         pending_appeals_count=pending_appeals_count)

@app.route('/assign_shift', methods=['POST'])
def assign_shift():
    day = request.form.get('day')
    shift_index = int(request.form.get('shift_index'))
    employee = request.form.get('employee')
    
    # בדיקה אם העובד זמין
    if not system.is_employee_available(day, employee):
        return jsonify({
            'success': False, 
            'message': 'העובד כבר משובץ במשמרת אחרת באותו יום'
        })
    
    success = system.assign_shift('admin', day, shift_index, employee)
    return jsonify({'success': success})

@app.route('/remove_from_shift', methods=['POST'])
def remove_from_shift():
    try:
        day = request.form.get('day')
        shift_index = int(request.form.get('shift_index'))
        employee = request.form.get('employee')
        
        print(f"Removing employee: {employee} from {day}, shift {shift_index}")  # לדיבוג
        
        if not all([day, shift_index is not None, employee]):
            return jsonify({
                'success': False, 
                'message': 'חסרים פרטים להסרת העובד'
            })
        
        success = system.remove_from_shift('admin', day, shift_index, employee)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'העובד הוסר בהצלחה'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'לא ניתן להסיר את העובד מהמשמרת'
            })
            
    except Exception as e:
        print(f"Error removing employee: {str(e)}")  # לדיבוג
        return jsonify({
            'success': False,
            'message': f'אירעה שגיאה בהסרת העובד: {str(e)}'
        })

@app.route('/preview_schedule')
def preview_schedule():
    schedule = system.get_weekly_schedule()
    return render_template('preview.html', schedule=schedule)

@app.route('/download_pdf')
def download_pdf():
    schedule = system.get_weekly_schedule()
    pdf_file = create_schedule_pdf(schedule)
    return send_file(pdf_file, as_attachment=True)

@app.route('/employees')
@login_required
def employees():
    """הצגת דף ניהול עובדים"""
    if not system.users[session['username']].is_admin:
        return redirect(url_for('user_schedule'))
    
    try:
        # מספר הערעורים הממתינים
        pending_appeals_count = len(system.get_pending_appeals())
        
        # העברת אובייקט המערכת לתבנית
        return render_template('employees.html',
                             system=system,
                             active_page='employees',
                             pending_appeals_count=pending_appeals_count)
    except Exception as e:
        print(f"Error in employees route: {str(e)}")  # לוג השגיאה
        flash('אירעה שגיאה בטעינת דף העובדים', 'error')
        return redirect(url_for('index'))

@app.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not system.users[session['username']].is_admin:
        return redirect(url_for('user_schedule'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        if username in system.users:
            flash('שם משתמש כבר קיים במערכת', 'error')
            return redirect(url_for('employees'))
        
        # יצירת משתמש חדש עם סיסמה
        password = request.form.get('password', '1234')  # אם לא הוזנה סיסמה, ברירת מחדל היא 1234
        user = User(
            username=username,
            password=password,  # הגדרת הסיסמה
            first_name=request.form.get('first_name', ''),
            last_name=request.form.get('last_name', ''),
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            employee_number=request.form.get('employee_number', ''),
            is_admin=False
        )
        
        system.users[username] = user
        system.save_to_file('schedule.json')  # שמירת השינויים
        flash(f'העובד נוסף בהצלחה. שם משתמש: {username}, סיסמה: {password}', 'success')
        return redirect(url_for('employees'))
    
    pending_appeals_count = len(system.get_pending_appeals())
    return render_template('add_employee.html', 
                         active_page='employees',
                         pending_appeals_count=pending_appeals_count)

@app.route('/edit_employee/<username>', methods=['GET', 'POST'])
@login_required
def edit_employee(username):
    if not system.users[session['username']].is_admin:
        return redirect(url_for('user_schedule'))
    
    if request.method == 'POST':
        try:
            user = system.users[username]
            # אם לא הוזנה סיסמה חדשה, נשאיר את הקיימת
            new_password = request.form.get('password')
            if new_password and new_password != 'None':
                user.password = new_password
            user.first_name = request.form.get('first_name', user.first_name)
            user.last_name = request.form.get('last_name', user.last_name)
            user.employee_number = request.form.get('employee_number', user.employee_number)
            user.phone = request.form.get('phone', user.phone)
            user.email = request.form.get('email', user.email)
            
            system.save_to_file('schedule.json')
            flash('פרטי העובד עודכנו בהצלחה', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            print(f"Error updating employee: {str(e)}")
            flash('אירעה שגיאה בעדכון פרטי העובד', 'error')
            return redirect(url_for('employees'))
    
    user = system.users.get(username)
    if not user:
        flash('העובד לא נמצא', 'error')
        return redirect(url_for('employees'))
    
    # אם אין סיסמה, נגדיר סיסמת ברירת מחדל
    if not user.password or user.password == 'None':
        user.password = '1234'
        system.save_to_file('schedule.json')
    
    pending_appeals_count = len(system.get_pending_appeals())
    return render_template('edit_employee.html', 
                         user=user,
                         active_page='employees',
                         pending_appeals_count=pending_appeals_count)

@app.route('/delete_employee/<username>', methods=['POST'])
@login_required
def delete_employee(username):
    """מחיקת עובד לפי שם משתמש"""
    if not system.users[session['username']].is_admin:
        return jsonify({'success': False, 'message': 'אין הרשאה'}), 403
    
    try:
        if username in system.users and not system.users[username].is_admin:
            # הסרת העובד מכל המשמרות
            for day, shifts in system.weekly_shifts.items():
                for shift in shifts:
                    if username in shift.employees:
                        shift.remove_employee(username)
            
            # מחיקת העובד מהמערכת
            del system.users[username]
            system.save_to_file('schedule.json')
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'העובד לא נמצא'}), 404
    except Exception as e:
        print(f"Error deleting employee: {str(e)}")
        return jsonify({'success': False, 'message': 'אירעה שגיאה במחיקת העובד'}), 500

@app.route('/get_employee/<username>')
def get_employee(username):
    if username in system.users:
        user = system.users[username]
        return jsonify({
            'username': username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'employee_number': user.employee_number,
            'phone': user.phone,
            'email': user.email,
            'id_number': user.id_number,
            'display_name': f"{user.first_name} {user.last_name}".strip()
        })
    return jsonify({'error': 'עובד לא נמצא'})

@app.route('/save_employee', methods=['POST'])
def save_employee():
    try:
        data = request.json
        username = data.get('username')
        
        # אם יש username, זה עריכה של עובד קיים
        if username and username in system.users:
            user = system.users[username]
        else:
            # יצירת עובד חדש
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            username = f"{first_name}_{last_name}"  # צירת שם משתמש מהשם המלא
            
            if username in system.users:
                return jsonify({
                    'success': False,
                    'message': 'עובד עם שם זה כבר קיי במערכת'
                })
            
            # יצירת משתמש חדש כעובד רגיל (לא מנהל)
            user = User(
                username=username,
                is_admin=False,  # עובד רגיל
                first_name=first_name,
                last_name=last_name,
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                id_number=data.get('id_number', ''),
                employee_number=data.get('employee_number', '')
            )
            system.users[username] = user
        
        # עדכון פרטי העובד
        user.employee_number = data.get('employee_number', '')
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
        user.id_number = data.get('id_number', '')
        user.phone = data.get('phone', '')
        user.email = data.get('email', '')
        
        # שמירת המידע לקובץ אחרי כל שינוי
        system.save_to_file('schedule.json')
        
        return jsonify({
            'success': True,
            'message': 'העובד נשמר בהצלחה'
        })
        
    except Exception as e:
        print(f"Error saving employee: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'אירעה שגיאה בשמירת העובד: {str(e)}'
        })

def get_employee_color(employee):
    """מחזיר צבע לפי שם העובד"""
    colors = {
        'yossi': '#007bff',  # כחול
        'rachel': '#28a745',  # ירוק
        'moshe': '#dc3545',   # אדום
        'sara': '#6f42c1'     # סגול
    }
    return colors.get(employee, '#6c757d')  # אפור כירת מחדל

@app.context_processor
def utility_processor():
    return dict(get_employee_color=get_employee_color)

@app.route('/create_appeal', methods=['POST'])
@login_required
def create_appeal():
    try:
        day = request.form.get('day')
        shift_index = int(request.form.get('shift_index'))
        reason = request.form.get('reason')
        employee = session['username']
        
        # בדיקה אם יש ערעור קיים או נדחה
        has_appeal, status, response = system.has_active_appeal(employee, day, shift_index)
        
        if has_appeal:
            if status == 'pending':
                flash('כבר קיים ערעור פעיל על משמרת זו. נא להמתין לתשובת המנהל.', 'error')
            elif status == 'rejected':
                flash(f'הערעור על משמרת זו כבר נדחה. סיבה: {response}', 'error')
            return redirect(url_for('user_schedule'))
        
        success, message = system.create_appeal(employee, day, shift_index, reason)
        
        if success:
            flash('הערעור נשלח בהצלחה. המנהל יבחן את בקשתך בהקדם.', 'success')
        else:
            flash(message, 'error')
            
        return redirect(url_for('user_schedule'))
    except Exception as e:
        flash('אירעה שגיאה בשליחת הערעור', 'error')
        return redirect(url_for('user_schedule'))

@app.route('/handle_appeal', methods=['POST'])
@login_required
def handle_appeal():
    """טיפול בערעור על ידי מנהל"""
    if not system.users[session['username']].is_admin:
        return jsonify({'success': False, 'message': 'אין הרשאה'})
    
    try:
        data = request.json
        appeal_index = data.get('appeal_index')
        decision = data.get('decision')
        response = data.get('response', '')
        
        # מציאת הערעור הספציפי
        appeals = system.get_pending_appeals()
        if 0 <= appeal_index < len(appeals):
            appeal = appeals[appeal_index]
            appeal.status = decision
            appeal.admin_response = response
            
            # שמירת השינויים
            system.save_to_file('schedule.json')
            
            # אם הערעור אושר, הסרת העובד מהמשמרת
            if decision == 'approved':
                day = appeal.day
                shift_index = appeal.shift_index
                employee = appeal.employee
                if day in system.weekly_shifts:
                    shift = system.weekly_shifts[day][shift_index]
                    if employee in shift.employees:
                        shift.employees.remove(employee)
                        system.save_to_file('schedule.json')
            
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'message': 'ערעור לא נמצא'})
        
    except Exception as e:
        print(f"Error handling appeal: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/appeals')
@login_required
def view_appeals():
    if not system.users[session['username']].is_admin:
        return redirect(url_for('user_schedule'))
    
    # מיון הערעורים לפי תאריך (חדש לישן)
    sorted_appeals = sorted(system.appeals, key=lambda x: x.created_at, reverse=True)
    
    # סינון רק ערעורים פעילים (ממתינים)
    active_appeals = [appeal for appeal in sorted_appeals if appeal.status == 'pending']
    
    # הדפסת לוג לדיבוג
    print(f"Found {len(active_appeals)} active appeals")
    for appeal in active_appeals:
        print(f"Appeal from {appeal.employee} for {appeal.day}")
    
    pending_appeals_count = len(active_appeals)
    return render_template('appeals.html',  # שינוי מ-admin_appeals.html ל-appeals.html
                         appeals=active_appeals,
                         active_page='appeals',
                         pending_appeals_count=pending_appeals_count,
                         system=system)  # העברת אובייקט המערכת לתבנית

if __name__ == '__main__':
    app.run(debug=True) 