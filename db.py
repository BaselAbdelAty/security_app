# db.py
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import json

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    """
    الحصول على بيانات الاعتماد من Streamlit Secrets أو الملف المحلي
    """
    try:
        # المحاولة الأولى: استخدام Streamlit Secrets (للاستخدام على Streamlit Cloud)
        if 'GOOGLE_CREDS_JSON' in st.secrets:
            creds_json = st.secrets['GOOGLE_CREDS_JSON']
            
            # إذا كانت البيانات كـ JSON string، نحولها إلى dictionary
            if isinstance(creds_json, str):
                creds_dict = json.loads(creds_json)
            else:
                creds_dict = creds_json
                
            return Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            
    except Exception as e:
        st.error(f"❌ خطأ في تحميل بيانات الاعتماد من Secrets: {str(e)}")
    
    try:
        # المحاولة الثانية: استخدام الملف المحلي (للاستخدام المحلي)
        return Credentials.from_service_account_file(
            "credentials/securityapp-470301-bde6c80d2155.json", 
            scopes=SCOPE
        )
    except Exception as e:
        st.error("""
        ❌ فشل في تحميل بيانات الاعتماد!
        
        أسباب محتملة:
        1. لم يتم إعداد Secrets في Streamlit Cloud
        2. ملف credentials غير موجود محلياً
        3. بيانات الاعتماد غير صحيحة
        
        راجع الإعدادات وحاول مرة أخرى.
        """)
        raise e

# تهيئة العميل
try:
    creds = get_credentials()
    client = gspread.authorize(creds)
    SPREADSHEET_NAME = "gis_db"
except Exception as e:
    st.error(f"❌ فشل في تهيئة الاتصال بـ Google Sheets: {str(e)}")
    client = None
    SPREADSHEET_NAME = None

def get_sheet(sheet_name):
    if client is None:
        st.error("❌ العميل غير مهيء. لا يمكن الوصول إلى Google Sheets.")
        return None
    try:
        sh = client.open(SPREADSHEET_NAME)
        return sh.worksheet(sheet_name)
    except Exception as e:
        st.error(f"❌ خطأ في الوصول إلى الورقة '{sheet_name}': {str(e)}")
        return None

def read_all(sheet_name):
    ws = get_sheet(sheet_name)
    if ws is None:
        return []
    try:
        return ws.get_all_records()
    except Exception as e:
        st.error(f"❌ خطأ في قراءة البيانات من '{sheet_name}': {str(e)}")
        return []

def insert_row(sheet_name, row_data):
    ws = get_sheet(sheet_name)
    if ws is None:
        return False
    try:
        headers = ws.row_values(1)
        row = [row_data.get(h, "") for h in headers]
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في إضافة صف إلى '{sheet_name}': {str(e)}")
        return False

def find_rows(sheet_name, col_index, keyword):
    ws = get_sheet(sheet_name)
    if ws is None:
        return []
    try:
        data = ws.get_all_values()
        header = data[0]
        results = [dict(zip(header, row)) for row in data[1:] if keyword.lower() in row[col_index].lower()]
        return results
    except Exception as e:
        st.error(f"❌ خطأ في البحث في '{sheet_name}': {str(e)}")
        return []

def delete_rows(sheet_name, criteria):
    """
    حذف الصفوف من الجدول بناءً على المعايير المحددة
    
    Args:
        sheet_name (str): اسم الورقة
        criteria (dict): معايير الحذف {اسم_الحقل: القيمة}
    
    Returns:
        int: عدد الصفوف المحذوفة
    """
    ws = get_sheet(sheet_name)
    if ws is None:
        return 0
        
    try:
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
        st.error(f"❌ خطأ في حذف الصفوف: {str(e)}")
        return 0