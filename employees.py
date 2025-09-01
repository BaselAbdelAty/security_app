# employees.py
import streamlit as st
import pandas as pd
import io
from db import read_all, insert_row, get_sheet

def employees_page():
    st.title("👨‍💼 إدارة الموظفين")
    
    # تهيئة حالة الجلسة
    if "emp_data_version" not in st.session_state:
        st.session_state.emp_data_version = 0
    
    # تهيئة متغيرات البحث
    if "search_input" not in st.session_state:
        st.session_state.search_input = ""
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "show_delete_confirm" not in st.session_state:
        st.session_state.show_delete_confirm = False
    if "emps_to_delete" not in st.session_state:
        st.session_state.emps_to_delete = []
    if "show_edit_form" not in st.session_state:
        st.session_state.show_edit_form = False
    if "edit_emp" not in st.session_state:
        st.session_state.edit_emp = None
    
    # 🔹 أزرار التنقل في أعلى الصفحة
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🏠 الرئيسية", use_container_width=True):
            # مسح حالة البحث عند العودة للصفحة الرئيسية
            st.session_state.search_input = ""
            st.session_state.search_results = None
            st.session_state.show_delete_confirm = False
            st.session_state.emps_to_delete = []
            st.session_state.show_edit_form = False
            st.session_state.edit_emp = None
            st.session_state["page"] = "main"
            st.rerun()
    with col2:
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            # مسح حالة البحث عند التحديث
            st.session_state.search_input = ""
            st.session_state.search_results = None
            st.session_state.show_delete_confirm = False
            st.session_state.emps_to_delete = []
            st.session_state.show_edit_form = False
            st.session_state.edit_emp = None
            st.session_state.emp_data_version += 1
            st.rerun()
    with col3:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            # مسح جميع حالات الجلسة عند التسجيل الخروج
            st.session_state["user"] = None
            st.session_state["page"] = "login"
            st.session_state.search_input = ""
            st.session_state.search_results = None
            st.session_state.show_delete_confirm = False
            st.session_state.emps_to_delete = []
            st.session_state.show_edit_form = False
            st.session_state.edit_emp = None
            st.rerun()
    
    # جلب جميع البيانات من Google Sheets
    def load_all_employees():
        return read_all("employees")
    
    # جلب البيانات النشطة فقط
    def load_active_employees():
        all_employees = load_all_employees()
        active_employees = []
        for emp in all_employees:
            if "deleted" not in emp or str(emp.get("deleted", "0")) != "1":
                active_employees.append(emp)
        return active_employees
    
    @st.cache_data(ttl=10, show_spinner="جاري تحميل بيانات الموظفين...")
    def get_cached_employees(version):
        return load_active_employees()
    
    active_employees = get_cached_employees(st.session_state.emp_data_version)
    
    # تحويل البيانات إلى DataFrame مع معالجة الأعمدة المفقودة
    df_data = []
    for emp in active_employees:
        emp_data = {
            "emp_name": emp.get("emp_name", ""),
            "emp_n_id": str(emp.get("emp_n_id", "")),
            "emp_bank": emp.get("emp_bank", ""),
            "emp_acc_num": str(emp.get("emp_acc_num", "")),
            "monthly_salary": emp.get("monthly_salary", 0.0)
        }
        df_data.append(emp_data)
    
    # إنشاء DataFrame مع أعمدة افتراضية إذا كانت غير موجودة
    default_columns = ["emp_name", "emp_n_id", "emp_bank", "emp_acc_num", "monthly_salary"]
    df = pd.DataFrame(df_data, columns=default_columns)
    
    # قسم إضافة موظف جديد
    with st.expander("➕ إضافة موظف جديد", expanded=False):
        with st.form("add_emp_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                emp_name = st.text_input("اسم الموظف *", key="emp_name_input")
                emp_n_id = st.text_input("الرقم القومي *", key="emp_nid_input")
            with col2:
                emp_bank = st.text_input("البنك *", key="emp_bank_input")
                monthly_salary = st.number_input("الراتب الشهري *", min_value=0.0, step=100.0, key="salary_input")
            
            emp_acc_num = st.text_input("رقم الحساب *", key="emp_acc_input")
            
            submitted = st.form_submit_button("إضافة الموظف")
            if submitted:
                if emp_name and emp_n_id and emp_bank and emp_acc_num and monthly_salary:
                    all_employees_data = load_all_employees()
                    
                    n_id_exists = False
                    for emp in all_employees_data:
                        if (str(emp.get("emp_n_id", "")) == emp_n_id and 
                            ("deleted" not in emp or str(emp.get("deleted", "0")) != "1")):
                            n_id_exists = True
                            break
                    
                    if n_id_exists:
                        st.error("❌ الرقم القومي مسجل بالفعل لموظف نشط")
                    else:
                        insert_row("employees", {
                            "emp_name": emp_name,
                            "emp_n_id": emp_n_id,
                            "emp_bank": emp_bank,
                            "emp_acc_num": emp_acc_num,
                            "monthly_salary": monthly_salary,
                            "deleted": "0"
                        })
                        st.session_state.emp_data_version += 1
                        st.success("✅ تم إضافة الموظف بنجاح!")
                        st.rerun()
                else:
                    st.warning("⚠️ يرجى ملء جميع الحقول الإلزامية (*)")

    # قسم البحث عن الموظفين
    st.subheader("🔍 البحث عن الموظفين")
    
    search_col1, search_col2, search_col3 = st.columns([2, 1, 1])
    with search_col1:
        # استخدام القيمة المخزنة في حالة الجلسة
        search_input = st.text_input(
            "ابحث باسم الموظف أو الرقم القومي أو البنك", 
            value=st.session_state.search_input,
            placeholder="اكتب للبحث...", 
            key="search_input_widget"
        )
        # تحديث حالة الجلسة عند تغيير قيمة البحث
        if search_input != st.session_state.search_input:
            st.session_state.search_input = search_input
    
    with search_col2:
        st.write("")
        search_clicked = st.button("🔍 بحث", use_container_width=True, key="search_btn")
    
    with search_col3:
        st.write("")
        # زر تحميل Excel في مكان منفصل
        if not df.empty and len(df) > 0:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='الموظفين', index=False)
            output.seek(0)
            
            st.download_button(
                label="📥تحميل كل الموظفين",
                data=output,
                file_name="الموظفين.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_excel"
            )
        else:
            st.warning("لا توجد بيانات")
    
    # معالجة البحث
    if search_clicked and st.session_state.search_input:
        # التحقق من وجود الأعمدة قبل البحث
        if all(col in df.columns for col in ["emp_name", "emp_n_id", "emp_bank"]):
            try:
                # البحث بأمان مع معالجة القيم الفارغة
                results = df[
                    df["emp_name"].astype(str).str.contains(st.session_state.search_input, case=False, na=False) | 
                    df["emp_n_id"].astype(str).str.contains(st.session_state.search_input, case=False, na=False) |
                    df["emp_bank"].astype(str).str.contains(st.session_state.search_input, case=False, na=False)
                ]
                
                if not results.empty and len(results) > 0:
                    st.session_state.search_results = results
                    st.success(f"تم العثور على {len(results)} موظف")
                else:
                    st.warning("لم يتم العثور على موظفين مطابقين")
                    st.session_state.search_results = None
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء البحث: {str(e)}")
        else:
            st.warning("⚠️ هيكل البيانات غير صحيح. يرجى تحديث الصفحة.")
    
    # عرض نتائج البحث والتحكم فيها
    if st.session_state.search_results is not None and not st.session_state.search_results.empty:
        results = st.session_state.search_results
        
        st.subheader(f"نتائج البحث ({len(results)} موظف)")
        st.dataframe(results, use_container_width=True)
        
        # تحميل نتائج البحث كملف Excel
        output_search = io.BytesIO()
        with pd.ExcelWriter(output_search, engine='openpyxl') as writer:
            results.to_excel(writer, sheet_name='نتائج_البحث', index=False)
        output_search.seek(0)
        
        st.download_button(
            label="📥 تحميل نتائج البحث كExcel",
            data=output_search,
            file_name="نتائج_البحث.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_search_excel"
        )
        
        # قسم التحكم في الموظفين المحددين
        st.subheader("⚙️ التحكم في الموظفين المحددين")
        
        # اختيار موظفين من نتائج البحث
        emp_options = {i: f"{results.iloc[i]['emp_name']} - {results.iloc[i]['emp_n_id']}" for i in range(len(results))}
        selected_emps = st.multiselect(
            "اختر الموظفين للتحكم:",
            options=list(emp_options.keys()),
            format_func=lambda x: emp_options[x],
            key="select_emps"
        )
        
        if selected_emps:
            # أزرار التحكم
            col_edit, col_delete = st.columns(2)
            
            with col_edit:
                if st.button("✏️ تعديل الموظفين المحددين", use_container_width=True, key="edit_selected"):
                    if len(selected_emps) == 1:
                        # إذا تم اختيار موظف واحد فقط، انتقل إلى وضع التعديل
                        selected_emp = results.iloc[selected_emps[0]]
                        st.session_state.edit_emp = selected_emp
                        st.session_state.show_edit_form = True
                        st.rerun()
                    else:
                        st.warning("⚠️ يرجى اختيار موظف واحد فقط للتعديل")
            
            with col_delete:
                if st.button("🗑️ حذف الموظفين المحددين", use_container_width=True, type="secondary", key="delete_selected"):
                    st.session_state.emps_to_delete = [results.iloc[i] for i in selected_emps]
                    st.session_state.show_delete_confirm = True
                    st.rerun()
        
        # نموذج تعديل الموظف
        if st.session_state.show_edit_form and st.session_state.edit_emp is not None:
            selected_emp = st.session_state.edit_emp
            
            st.subheader("✏️ تعديل بيانات الموظف")
            st.write(f"**المعدل:** {selected_emp['emp_name']} - {selected_emp['emp_n_id']}")
            
            with st.form("edit_emp_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_emp_name = st.text_input("اسم الموظف *", value=selected_emp['emp_name'], key="edit_emp_name")
                    new_emp_n_id = st.text_input("الرقم القومي *", value=selected_emp['emp_n_id'], key="edit_emp_nid")
                with col2:
                    new_emp_bank = st.text_input("البنك *", value=selected_emp['emp_bank'], key="edit_emp_bank")
                    new_monthly_salary = st.number_input("الراتب الشهري *", value=float(selected_emp['monthly_salary']), min_value=0.0, step=100.0, key="edit_salary")
                
                new_emp_acc_num = st.text_input("رقم الحساب *", value=selected_emp['emp_acc_num'], key="edit_emp_acc")
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    update_submitted = st.form_submit_button("💾 حفظ التعديلات", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("❌ إلغاء", use_container_width=True):
                        st.session_state.show_edit_form = False
                        st.session_state.edit_emp = None
                        st.rerun()
                
                if update_submitted:
                    if new_emp_name and new_emp_n_id and new_emp_bank and new_emp_acc_num and new_monthly_salary:
                        # الحصول على البيانات الأصلية من Google Sheets
                        all_employees_data = load_all_employees()
                        original_emp_data = None
                        
                        for emp in all_employees_data:
                            if (str(emp.get("emp_n_id", "")) == str(selected_emp["emp_n_id"]) and 
                                str(emp.get("emp_name", "")) == str(selected_emp["emp_name"]) and
                                ("deleted" not in emp or str(emp.get("deleted", "0")) != "1")):
                                original_emp_data = emp
                                break
                        
                        if original_emp_data is None:
                            st.error("❌ لم يتم العثور على الموظف في قاعدة البيانات")
                        else:
                            # التحقق من عدم تكرار الرقم القومي (باستثناء الموظف الحالي)
                            n_id_exists = False
                            for emp in all_employees_data:
                                if (str(emp.get("emp_n_id", "")) == new_emp_n_id and 
                                    str(emp.get("emp_n_id", "")) != str(selected_emp['emp_n_id']) and
                                    ("deleted" not in emp or str(emp.get("deleted", "0")) != "1")):
                                    n_id_exists = True
                                    break
                            
                            if n_id_exists:
                                st.error("❌ الرقم القومي مسجل بالفعل لموظف نشط آخر")
                            else:
                                # البحث عن الصف في Google Sheets وتحديثه
                                ws = get_sheet("employees")
                                data = ws.get_all_values()
                                headers = data[0] if data else []
                                
                                row_number = None
                                for i, row in enumerate(data[1:], start=2):
                                    if (len(row) > 0 and str(row[0]) == str(original_emp_data.get("emp_name", "")) and 
                                        len(row) > 1 and str(row[1]) == str(original_emp_data.get("emp_n_id", "")) and 
                                        len(row) > 2 and str(row[2]) == str(original_emp_data.get("emp_bank", "")) and 
                                        len(row) > 3 and str(row[3]) == str(original_emp_data.get("emp_acc_num", ""))):
                                        row_number = i
                                        break
                                
                                if row_number:
                                    # تحديث البيانات
                                    updated_data = [
                                        new_emp_name,
                                        new_emp_n_id,
                                        new_emp_bank,
                                        new_emp_acc_num,
                                        str(new_monthly_salary)
                                    ]
                                    
                                    # إذا كان هناك أعمدة إضافية (مثل deleted)، نضيفها
                                    if len(headers) > 5:
                                        # الحفاظ على قيمة deleted كما هي
                                        deleted_value = data[row_number-1][5] if len(data[row_number-1]) > 5 else "0"
                                        updated_data.append(deleted_value)
                                    
                                    # تحديث الصف في Google Sheets
                                    start_col = f"A{row_number}"
                                    end_col = f"{chr(64 + len(updated_data))}{row_number}"
                                    ws.update(f"{start_col}:{end_col}", [updated_data])
                                    
                                    st.session_state.emp_data_version += 1
                                    st.success("✅ تم تحديث بيانات الموظف بنجاح!")
                                    
                                    # مسح حالة التعديل
                                    st.session_state.show_edit_form = False
                                    st.session_state.edit_emp = None
                                    st.session_state.search_results = None
                                    st.session_state.search_input = ""
                                    st.rerun()
                                else:
                                    st.error("❌ لم يتم العثور على الموظف في قاعدة البيانات")
                    else:
                        st.warning("⚠️ يرجى ملء جميع الحقول الإلزامية (*)")
        
        # تأكيد الحذف
        if st.session_state.show_delete_confirm and st.session_state.emps_to_delete:
            st.subheader("🗑️ تأكيد الحذف")
            st.warning(f"⚠️ سيتم حذف {len(st.session_state.emps_to_delete)} موظف. هل أنت متأكد؟")
            
            # عرض الموظفين المحددين للحذف
            for i, emp in enumerate(st.session_state.emps_to_delete):
                st.write(f"{i+1}. {emp['emp_name']} - {emp['emp_n_id']} - {emp['emp_bank']}")
            
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("✅ نعم، احذف", type="primary", use_container_width=True, key="confirm_delete"):
                    ws = get_sheet("employees")
                    data = ws.get_all_values()
                    headers = data[0] if data else []
                    
                    # التأكد من وجود عمود deleted
                    if "deleted" not in headers:
                        ws.update_cell(1, len(headers) + 1, "deleted")
                        headers.append("deleted")
                        # إعادة تحميل البيانات بعد إضافة العمود
                        data = ws.get_all_values()
                        headers = data[0]
                    
                    deleted_col_index = headers.index("deleted") + 1
                    deleted_count = 0
                    
                    # الحصول على جميع البيانات من الجدول
                    all_employees_data = load_all_employees()
                    
                    for emp_to_delete in st.session_state.emps_to_delete:
                        # البحث عن الموظف في Google Sheets باستخدام البيانات الحقيقية
                        row_found = False
                        for i, row in enumerate(data[1:], start=2):
                            # المقارنة بجميع الحقول للتأكد من تطابق الموظف
                            try:
                                name_match = len(row) > 0 and str(row[0]) == str(emp_to_delete.get("emp_name", ""))
                                nid_match = len(row) > 1 and str(row[1]) == str(emp_to_delete.get("emp_n_id", ""))
                                bank_match = len(row) > 2 and str(row[2]) == str(emp_to_delete.get("emp_bank", ""))
                                acc_match = len(row) > 3 and str(row[3]) == str(emp_to_delete.get("emp_acc_num", ""))
                                
                                if name_match and nid_match and bank_match and acc_match:
                                    # التحقق من أن الموظف غير محذوف مسبقاً
                                    is_deleted = False
                                    if "deleted" in headers:
                                        deleted_idx = headers.index("deleted")
                                        if len(row) > deleted_idx and str(row[deleted_idx]) == "1":
                                            is_deleted = True
                                    
                                    if not is_deleted:
                                        # تحديث عمود deleted إلى "1"
                                        ws.update_cell(i, deleted_col_index, "1")
                                        deleted_count += 1
                                        row_found = True
                                        st.success(f"✓ تم حذف: {emp_to_delete['emp_name']}")
                                        break
                            except Exception as e:
                                st.error(f"خطأ أثناء معالجة الصف {i}: {str(e)}")
                                continue
                        
                        if not row_found:
                            st.warning(f"⚠️ لم يتم العثور على الموظف: {emp_to_delete['emp_name']} في الجدول أو هو محذوف بالفعل")
                    
                    if deleted_count > 0:
                        st.session_state.emp_data_version += 1
                        st.success(f"✅ تم حذف {deleted_count} موظف بنجاح!")
                        
                        # مسح حالة الحذف والبحث
                        st.session_state.show_delete_confirm = False
                        st.session_state.emps_to_delete = []
                        st.session_state.search_results = None
                        st.session_state.search_input = ""
                        st.rerun()
                    else:
                        st.error("❌ لم يتم حذف أي موظف. قد يكونوا محذوفين بالفعل أو غير موجودين في قاعدة البيانات")
            
            with col_cancel:
                if st.button("❌ إلغاء", use_container_width=True, key="cancel_delete"):
                    st.session_state.show_delete_confirm = False
                    st.session_state.emps_to_delete = []
                    st.rerun()

# تشغيل الصفحة
if __name__ == "__main__":
    employees_page()