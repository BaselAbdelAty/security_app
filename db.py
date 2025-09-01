# db.py
import gspread
from google.oauth2.service_account import Credentials

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "credentials/securityapp-470301-bde6c80d2155.json", scopes=SCOPE
)

client = gspread.authorize(creds)
SPREADSHEET_NAME = "gis_db"

def get_sheet(sheet_name):
    sh = client.open(SPREADSHEET_NAME)
    return sh.worksheet(sheet_name)

def read_all(sheet_name):
    ws = get_sheet(sheet_name)
    return ws.get_all_records()

def insert_row(sheet_name, row_data):
    ws = get_sheet(sheet_name)
    headers = ws.row_values(1)
    row = [row_data.get(h, "") for h in headers]
    ws.append_row(row)

def find_rows(sheet_name, col_index, keyword):
    ws = get_sheet(sheet_name)
    data = ws.get_all_values()
    header = data[0]
    results = [dict(zip(header, row)) for row in data[1:] if keyword.lower() in row[col_index].lower()]
    return results

def delete_rows(sheet_name, criteria):
    """
    حذف الصفوف من الجدول بناءً على المعايير المحددة
    
    Args:
        sheet_name (str): اسم الورقة
        criteria (dict): معايير الحذف {اسم_الحقل: القيمة}
    
    Returns:
        int: عدد الصفوف المحذوفة
    """
    try:
        ws = get_sheet(sheet_name)
        data = ws.get_all_values()
        headers = data[0]
        
        # الحصول على indices الأعمدة المطلوبة
        col_indices = {}
        for key in criteria.keys():
            if key in headers:
                col_indices[key] = headers.index(key)
        
        if not col_indices:
            return 0  # لا توجد أعمدة تطابق المعايير
        
        # البحث عن الصفوف التي تطابق جميع المعايير
        rows_to_delete = []
        for i, row in enumerate(data[1:], start=2):  # start=2 لأن الصف الأول هو العنوان والصفوف تبدأ من 1 في gspread
            match = True
            for key, value in criteria.items():
                if key in col_indices:
                    col_index = col_indices[key]
                    if col_index < len(row) and str(row[col_index]) != str(value):
                        match = False
                        break
            
            if match:
                rows_to_delete.append(i)
        
        # حذف الصفوف من الأسفل إلى الأعلى لتجنب مشاكل الترتيب
        deleted_count = 0
        for row_index in sorted(rows_to_delete, reverse=True):
            ws.delete_rows(row_index)
            deleted_count += 1
        
        return deleted_count
        
    except Exception as e:
        print(f"Error deleting rows: {e}")
        return 0