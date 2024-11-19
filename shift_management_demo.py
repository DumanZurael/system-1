from shift_management_system import ShiftManagementSystem, User
from datetime import time

def print_menu():
    """הדפסת תפריט ראשי"""
    print("\n=== מערכת ניהול משמרות - שקדייה ===")
    print("1. הצג לוח משמרות")
    print("2. ניהול עובדים")
    print("3. שמור נתונים")
    print("4. טען נתונים")
    print("0. יציאה")

def print_employee_menu():
    """הדפסת תפריט ניהול עובדים"""
    print("\n=== ניהול עובדים ===")
    print("1. הצג רשימת עובדים")
    print("2. הוסף עובד חדש")
    print("3. ערוך פרטי עובד")
    print("4. מחק עובד")
    print("0. חזור לתפריט ראשי")

def print_schedule(schedule):
    """פונקציה להדפסת לוח המשמרות"""
    for day, shifts in schedule.items():
        print(f"\n{day}:")
        for i, shift in enumerate(shifts):
            print(f"  {'משמרת בוקר' if i == 0 else 'משמרת ערב'}:")
            print(f"    שעות: {shift['start_time']} - {shift['end_time']}")
            employees = shift['employees']
            print(f"    עובדים: {', '.join(employees) if employees else 'לא משובץ'}")

def print_employees(system):
    """הדפסת רשימת העובדים"""
    print("\n=== רשימת עובדים ===")
    for username, user in system.users.items():
        if not user.is_admin:
            print(f"\nשם משתמש: {username}")
            print(f"מספר עובד: {user.employee_number}")
            print(f"שם פרטי: {user.first_name}")
            print(f"שם משפחה: {user.last_name}")
            print(f"ת.ז.: {user.id_number}")
            print(f"טלפון: {user.phone}")
            print(f"אימייל: {user.email}")
            print("-" * 30)

def add_employee(system):
    """הוספת עובד חדש"""
    print("\n=== הוספת עובד חדש ===")
    username = input("שם משתמש: ")
    
    if username in system.users:
        print("שם משתמש כבר קיים במערכת")
        return
    
    employee_number = input("מספר עובד: ")
    first_name = input("שם פרטי: ")
    last_name = input("שם משפחה: ")
    id_number = input("ת.ז.: ")
    phone = input("טלפון: ")
    email = input("אימייל: ")
    
    user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        id_number=id_number,
        employee_number=employee_number
    )
    
    system.users[username] = user
    print("העובד נוסף בהצלחה!")

def edit_employee(system):
    """עריכת פרטי עובד"""
    print("\n=== עריכת פרטי עובד ===")
    username = input("הכנס את שם המשתמש של העובד: ")
    
    if username not in system.users or system.users[username].is_admin:
        print("עובד לא נמצא")
        return
    
    user = system.users[username]
    print(f"\nעריכת פרטים עבור {username}")
    
    user.employee_number = input(f"מספר עובד [{user.employee_number}]: ") or user.employee_number
    user.first_name = input(f"שם פרטי [{user.first_name}]: ") or user.first_name
    user.last_name = input(f"שם משפחה [{user.last_name}]: ") or user.last_name
    user.id_number = input(f"ת.ז. [{user.id_number}]: ") or user.id_number
    user.phone = input(f"טלפון [{user.phone}]: ") or user.phone
    user.email = input(f"אימייל [{user.email}]: ") or user.email
    
    print("הפרטים עודכנו בהצלחה!")

def delete_employee(system):
    """מחיקת עובד"""
    print("\n=== מחיקת עובד ===")
    username = input("הכנס את שם המשתמש של העובד למחיקה: ")
    
    if username not in system.users or system.users[username].is_admin:
        print("עובד לא נמצא")
        return
    
    confirm = input(f"האם אתה בטוח שברצונך למחוק את {username}? (כן/לא): ")
    if confirm.lower() == 'כן':
        del system.users[username]
        print("העובד נמחק בהצלחה!")
    else:
        print("המחיקה בוטלה")

def manage_employees(system):
    """ניהול עובדים"""
    while True:
        print_employee_menu()
        choice = input("בחר אפשרות: ")
        
        if choice == '0':
            break
        elif choice == '1':
            print_employees(system)
        elif choice == '2':
            add_employee(system)
        elif choice == '3':
            edit_employee(system)
        elif choice == '4':
            delete_employee(system)
        else:
            print("אפשרות לא חוקית")

def main():
    system = ShiftManagementSystem()
    
    # יצירת מנהל ראשי
    system.users['admin'] = User('admin', is_admin=True)
    print("\nנוצר חשבון מנהל")
    
    while True:
        print_menu()
        choice = input("בחר אפשרות: ")
        
        if choice == '0':
            break
        elif choice == '1':
            schedule = system.get_weekly_schedule()
            print_schedule(schedule)
        elif choice == '2':
            manage_employees(system)
        elif choice == '3':
            filename = input("הכנס שם קובץ לשמירה: ") or 'schedule.json'
            system.save_to_file(filename)
            print("המידע נשמר בהצלחה!")
        elif choice == '4':
            filename = input("הכנס שם קובץ לטעינה: ") or 'schedule.json'
            try:
                system.load_from_file(filename)
                print("המידע נטען בהצלחה!")
            except FileNotFoundError:
                print("הקובץ לא נמצא")
        else:
            print("אפשרות לא חוקית")

if __name__ == "__main__":
    main()
