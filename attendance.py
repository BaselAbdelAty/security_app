# attendance.py
import streamlit as st
from datetime import date, datetime
from db import read_all, insert_row, delete_rows
import pandas as pd
from io import BytesIO

def attendance_page():
    st.title("🗓️ إدارة الحضور")
    
    # تهيئة حالة الجلسة
    if "attendance_records" not in st.session_state:
        st.session_state.attendance_records = [{}]  # بيان واحد فارغ في البداية
    
    if "att_date" not in st.session_state:
        st.session_state.att_date = date.today()
    
    if "site" not in st.session_state:
        st.session_state.site = ""
    
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0
    
    # تهيئة حالة البحث
    if "search_performed" not in st.session_state:
        st.session_state.search_performed = False
    
    if "search_criteria" not in st.session_state:
        st.session_state.search_criteria = {}
    
    # تهيئة حالة الحذف
    if "delete_success" not in st.session_state:
        st.session_state.delete_success = False
    
    # 🔹 أزرار التنقل في أعلى الصفحة
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🏠 الرئيسية", use_container_width=True):
            # مسح حالة البحث عند العودة للصفحة الرئيسية
            st.session_state.search_performed = False
            st.session_state.search_criteria = {}
            st.session_state["page"] = "main"
            st.rerun()
    with col2:
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            # زيادة مفتاح النموذج لإجبار إعادة التحميل
            st.session_state.form_key += 1
            st.session_state.attendance_records = [{}]
            st.session_state.att_date = date.today()
            st.session_state.site = ""
            # مسح حالة البحث عند التحديث
            st.session_state.search_performed = False
            st.session_state.search_criteria = {}
            st.rerun()
    with col3:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            # مسح حالة البحث عند تسجيل الخروج
            st.session_state.search_performed = False
            st.session_state.search_criteria = {}
            st.session_state["user"] = None
            st.session_state["page"] = "login"
            st.rerun()
    
    # جلب البيانات المرجعية من Google Sheets مع التخزين المؤقت
    @st.cache_data(ttl=300)  # تخزين لمدة 5 دقائق
    def load_reference_data():
        sites = read_all("sites")
        employees = read_all("employees")
        shifts = read_all("shifts")
        att_parameters = read_all("att_parameters")
        positions = read_all("positions")
        
        return sites, employees, shifts, att_parameters, positions
    
    # جلب البيانات
    sites, employees, shifts, att_parameters, positions = load_reference_data()
    
    # تحضير القوائم للاختيار
    site_options = [""] + [site.get("site", "") for site in sites if site.get("site")]
    employee_options = [""] + [emp.get("emp_name", "") for emp in employees if emp.get("emp_name")]
    shift_options = [""] + [shift.get("shift", "") for shift in shifts if shift.get("shift")]
    att_options = [""] + [param.get("symbol", "") for param in att_parameters if param.get("symbol")]
    position_options = [""] + [pos.get("pos_ar", "") for pos in positions if pos.get("pos_ar")]
    
    # قسم حذف بيانات الحضور
    st.subheader("🗑️ حذف سجلات الحضور")
    
    with st.expander("خيارات الحذف", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # الحذف بالموقع
            delete_site = st.selectbox(
                "📍 الموقع *", 
                options=site_options,
                key="delete_site"
            )
            
            # الحذف بالتاريخ - إجباري
            delete_date = st.date_input(
                "📅 التاريخ *",
                value=None,
                key="delete_date"
            )
            
        with col2:
            # الحذف باسم الموظف
            delete_employee = st.selectbox(
                "👨‍💼 الموظف *", 
                options=employee_options,
                key="delete_employee"
            )
            
            # الحذف بالوردية
            delete_shift = st.selectbox(
                "⏰ الوردية *", 
                options=shift_options,
                key="delete_shift"
            )
        
        # زر الحذف
        if st.button("🗑️ حذف السجلات", key="delete_button", type="secondary", use_container_width=True):
            # التحقق من أن جميع الحقول مملوءة
            if not all([delete_site, delete_date, delete_employee, delete_shift]):
                st.error("❌ يرجى ملء جميع الحقول الإجبارية (*)")
            else:
                # بناء معايير الحذف
                delete_criteria = {
                    "site": delete_site,
                    "date": str(delete_date),
                    "name": delete_employee,
                    "shift": delete_shift
                }
                
                try:
                    # حذف السجلات من قاعدة البيانات
                    deleted_count = delete_rows("attendance", delete_criteria)
                    
                    if deleted_count > 0:
                        st.success(f"✅ تم حذف {deleted_count} سجل حضور بنجاح!")
                        st.session_state.delete_success = True
                    else:
                        st.info("ℹ️ لم يتم العثور على سجلات تطابق معايير الحذف")
                        st.session_state.delete_success = False
                        
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء الحذف: {str(e)}")
                    st.session_state.delete_success = False
    
    # قسم البحث في بيانات الحضور
    st.subheader("🔍 البحث في سجلات الحضور")
    
    with st.expander("خيارات البحث", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # البحث بالموقع
            search_site = st.selectbox(
                "📍 الموقع", 
                options=site_options,
                key="search_site"
            )
            
            # البحث بالتاريخ (من) - إجباري
            search_date_from = st.date_input(
                "📅 من تاريخ *",
                value=None,
                key="search_date_from"
            )
            
        with col2:
            # البحث باسم الموظف
            search_employee = st.selectbox(
                "👨‍💼 الموظف", 
                options=employee_options,
                key="search_employee"
            )
            
            # البحث بالتاريخ (إلى) - إجباري
            search_date_to = st.date_input(
                "📅 إلى تاريخ *",
                value=None,
                key="search_date_to"
            )
        
        # البحث بالوردية
        search_shift = st.selectbox(
            "⏰ الوردية", 
            options=shift_options,
            key="search_shift"
        )
        
        # زر البحث
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🔍 بحث", key="search_button", use_container_width=True):
                # التحقق من أن حقول التاريخ مملوءة
                if not search_date_from or not search_date_to:
                    st.error("❌ يرجى تحديد تاريخ البداية والنهاية للبحث")
                elif search_date_from > search_date_to:
                    st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
                else:
                    # بناء معايير البحث
                    search_criteria = {}
                    if search_site:
                        search_criteria["site"] = search_site
                    if search_employee:
                        search_criteria["name"] = search_employee
                    if search_shift:
                        search_criteria["shift"] = search_shift
                    
                    # إضافة التواريخ الإجبارية
                    search_criteria["date_from"] = str(search_date_from)
                    search_criteria["date_to"] = str(search_date_to)
                    
                    # تخزين معايير البحث في حالة الجلسة
                    st.session_state.search_criteria = search_criteria
                    st.session_state.search_performed = True
                    st.rerun()
        
        with col2:
            if st.button("🧹 مسح البحث", key="clear_search", use_container_width=True):
                st.session_state.search_performed = False
                st.session_state.search_criteria = {}
                st.rerun()
    
    # عرض نتائج البحث إذا تم إجراء بحث
    if st.session_state.get("search_performed", False):
        st.subheader("📊 نتائج البحث")
        
        # جلب بيانات الحضور بناءً على معايير البحث
        all_attendance = read_all("attendance")
        
        # تصفية البيانات بناءً على معايير البحث
        filtered_data = []
        for record in all_attendance:
            # تطبيق معايير البحث
            match = True
            
            # البحث بالموقع
            if "site" in st.session_state.search_criteria:
                if record.get("site") != st.session_state.search_criteria["site"]:
                    match = False
            
            # البحث باسم الموظف
            if "name" in st.session_state.search_criteria:
                if record.get("name") != st.session_state.search_criteria["name"]:
                    match = False
            
            # البحث بالوردية
            if "shift" in st.session_state.search_criteria:
                if record.get("shift") != st.session_state.search_criteria["shift"]:
                    match = False
            
            # البحث بنطاق التاريخ (إجباري)
            record_date = record.get("date")
            if record_date:
                try:
                    record_date_obj = datetime.strptime(record_date, "%Y-%m-%d").date()
                    
                    # التحقق من تاريخ "من" (إجباري)
                    date_from = datetime.strptime(st.session_state.search_criteria["date_from"], "%Y-%m-%d").date()
                    if record_date_obj < date_from:
                        match = False
                    
                    # التحقق من تاريخ "إلى" (إجباري)
                    date_to = datetime.strptime(st.session_state.search_criteria["date_to"], "%Y-%m-%d").date()
                    if record_date_obj > date_to:
                        match = False
                except:
                    match = False
            else:
                match = False
            
            if match:
                filtered_data.append(record)
        
        # عرض نتائج البحث
        if filtered_data:
            st.success(f"تم العثور على {len(filtered_data)} سجل حضور")
            
            # تحويل البيانات إلى DataFrame لعرضها بشكل جدولي
            df = pd.DataFrame(filtered_data)
            
            # إعادة ترتيب الأعمدة لعرضها بشكل منظم
            desired_columns = ["date", "site", "shift", "name", "position", "att", "notes"]
            available_columns = [col for col in desired_columns if col in df.columns]
            
            # عرض البيانات
            st.dataframe(df[available_columns], use_container_width=True)
            
            # خيارات التصدير
            col1, col2 = st.columns(2)
            
            with col1:
                # تصدير كملف CSV
                csv = df[available_columns].to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 تحميل كملف CSV",
                    data=csv,
                    file_name="نتائج_البحث_الحضور.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # تصدير كملف Excel - الطريقة الصحيحة
                try:
                    # إنشاء كائن BytesIO للكتابة فيه
                    output = BytesIO()
                    
                    # استخدام ExcelWriter لإنشاء ملف Excel
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df[available_columns].to_excel(writer, index=False, sheet_name='نتائج البحث')
                    
                    # الحصول على البيانات كبايتس
                    excel_data = output.getvalue()
                    
                    # زر التحميل
                    st.download_button(
                        label="📥 تحميل كملف Excel",
                        data=excel_data,
                        file_name="نتائج_البحث_الحضور.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"❌ حدث خطأ في إنشاء ملف Excel: {str(e)}")
                    st.info("يرجى التأكد من تثبيت المكتبات المطلوبة: pip install openpyxl")
        else:
            st.warning("⚠️ لم يتم العثور على نتائج تطابق معايير البحث")
            
            # عرض معايير البحث المستخدمة
            st.info("معايير البحث المستخدمة:")
            criteria_text = ""
            if "site" in st.session_state.search_criteria:
                criteria_text += f"- الموقع: {st.session_state.search_criteria['site']}\n"
            if "name" in st.session_state.search_criteria:
                criteria_text += f"- الموظف: {st.session_state.search_criteria['name']}\n"
            if "shift" in st.session_state.search_criteria:
                criteria_text += f"- الوردية: {st.session_state.search_criteria['shift']}\n"
            if "date_from" in st.session_state.search_criteria:
                criteria_text += f"- من تاريخ: {st.session_state.search_criteria['date_from']}\n"
            if "date_to" in st.session_state.search_criteria:
                criteria_text += f"- إلى تاريخ: {st.session_state.search_criteria['date_to']}\n"
            
            if criteria_text:
                st.text(criteria_text)
    
    # قسم إضافة سجل حضور جديد
    st.subheader("➕ إضافة سجلات حضور جديدة")
    
    # الحقول الثابتة (التاريخ والموقع)
    col1, col2 = st.columns(2)
    
    with col1:
        # تاريخ الحضور - إصلاح المشكلة
        att_date = st.date_input(
            "📅 التاريخ *", 
            value=st.session_state.att_date, 
            key=f"att_date_{st.session_state.form_key}"
        )
        # تحديث حالة الجلسة فور تغيير التاريخ
        st.session_state.att_date = att_date
    
    with col2:
        # الموقع
        if site_options:
            site = st.selectbox(
                "📍 الموقع *", 
                options=site_options, 
                key=f"site_{st.session_state.form_key}", 
                index=site_options.index(st.session_state.site) if st.session_state.site in site_options else 0
            )
            # تحديث حالة الجلسة فور تغيير الموقع
            st.session_state.site = site
        else:
            st.warning("⚠️ لا توجد مواقع متاحة. يرجى إضافة مواقع أولاً.")
            site = None
    
    # إضافة سجلات الحضور
    st.subheader("👥 بيانات حضور الموظفين")
    
    # استخدام مفتاح النموذج لتجنب مشاكل التخزين المؤقت
    for i in range(len(st.session_state.attendance_records)):
        record = st.session_state.attendance_records[i] if i < len(st.session_state.attendance_records) else {}
        
        st.markdown(f"### 📝 بيان الحضور #{i+1}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # الوردية
            if shift_options:
                # الحصول على القيمة الحالية من السجل
                current_shift = record.get("shift", "")
                shift_index = shift_options.index(current_shift) if current_shift in shift_options else 0
                
                shift = st.selectbox(
                    "⏰ الوردية *", 
                    options=shift_options, 
                    key=f"shift_{i}_{st.session_state.form_key}",
                    index=shift_index
                )
            else:
                st.warning("⚠️ لا توجد ورديات متاحة.")
                shift = None
        
        with col2:
            # الموظف
            if employee_options:
                # الحصول على القيمة الحالية من السجل
                current_emp = record.get("name", "")
                emp_index = employee_options.index(current_emp) if current_emp in employee_options else 0
                
                emp_name = st.selectbox(
                    "👨‍💼 الموظف *", 
                    options=employee_options, 
                    key=f"emp_{i}_{st.session_state.form_key}",
                    index=emp_index
                )
            else:
                st.warning("⚠️ لا توجد موظفين متاحين.")
                emp_name = None
        
        with col3:
            # حالة الحضور
            if att_options:
                # الحصول على القيمة الحالية من السجل
                current_att = record.get("att", "")
                att_index = att_options.index(current_att) if current_att in att_options else 0
                
                att_status = st.selectbox(
                    "✅ حالة الحضور *", 
                    options=att_options, 
                    key=f"att_{i}_{st.session_state.form_key}",
                    index=att_index
                )
            else:
                st.warning("⚠️ لا توجد حالات حضور متاحة.")
                att_status = None
        
        col4, col5 = st.columns([2, 1])
        
        with col4:
            # الوظيفة
            if position_options:
                # الحصول على القيمة الحالية من السجل
                current_pos = record.get("position", "")
                pos_index = position_options.index(current_pos) if current_pos in position_options else 0
                
                position = st.selectbox(
                    "💼 الوظيفة *", 
                    options=position_options, 
                    key=f"pos_{i}_{st.session_state.form_key}",
                    index=pos_index
                )
            else:
                st.warning("⚠️ لا توجد وظائف متاحة.")
                position = None
        
        with col5:
            # زر حذف البيان (ماعدا البيان الأول)
            if i > 0:
                if st.button("🗑️ حذف", key=f"delete_{i}_{st.session_state.form_key}", use_container_width=True):
                    # حذف البيان المحدد فقط
                    st.session_state.attendance_records.pop(i)
                    st.rerun()
        
        # الملاحظات
        current_notes = record.get("notes", "")
        notes = st.text_area(
            "📝 الملاحظات (اختياري)", 
            value=current_notes,
            max_chars=100, 
            placeholder="أدخل ملاحظات هنا (حد أقصى 100 حرف)...",
            key=f"notes_{i}_{st.session_state.form_key}"
        )
        
        # تحديث البيانات في السجل
        st.session_state.attendance_records[i] = {
            "shift": shift,
            "name": emp_name,
            "att": att_status,
            "position": position,
            "notes": notes
        }
        
        st.markdown("---")
    
    # أزرار التحكم
    col_add, col_submit, col_clear = st.columns(3)
    
    with col_add:
        if st.button("➕ إضافة بيان جديد", use_container_width=True, key=f"add_{st.session_state.form_key}"):
            # إضافة بيان جديد فارغ
            st.session_state.attendance_records.append({})
            st.rerun()
    
    with col_clear:
        if st.button("🧹 مسح الكل", use_container_width=True, key=f"clear_{st.session_state.form_key}"):
            # مسح جميع البيانات وزيادة مفتاح النموذج
            st.session_state.attendance_records = [{}]
            st.session_state.form_key += 1
            st.rerun()
    
    with col_submit:
        if st.button("🚀 إرسال إلى قاعدة البيانات", type="primary", use_container_width=True, key=f"submit_{st.session_state.form_key}"):
            # التحقق من صحة البيانات
            valid_records = True
            error_messages = []
            
            # التحقق من الحقول الثابتة أولاً
            if not st.session_state.att_date:
                error_messages.append("التاريخ مطلوب")
                valid_records = False
            
            if not st.session_state.site:
                error_messages.append("الموقع مطلوب")
                valid_records = False
            
            # التحقق من السجلات
            records_to_save = []
            for i, record in enumerate(st.session_state.attendance_records):
                if record and any(record.values()):  # فقط السجلات التي تحتوي على بيانات
                    if not all([record.get("shift"), record.get("name"), record.get("att"), record.get("position")]):
                        error_messages.append(f"بيان #{i+1} يحتوي على حقول ناقصة")
                        valid_records = False
                    else:
                        records_to_save.append(record)
            
            if not valid_records:
                for error in error_messages:
                    st.error(f"❌ {error}")
            elif not records_to_save:
                st.warning("⚠️ لا توجد بيانات لحفظها")
            else:
                # إرسال البيانات إلى قاعدة البيانات
                success_count = 0
                failed_count = 0
                
                for i, record in enumerate(records_to_save):
                    try:
                        # البحث عن الموظف المحدد للحصول على بياناته الكاملة
                        selected_employee = None
                        for emp in employees:
                            if emp.get("emp_name") == record.get("name"):
                                selected_employee = emp
                                break
                        
                        if selected_employee:
                            # إدخال البيانات في جدول الحضور
                            attendance_data = {
                                "date": str(st.session_state.att_date),
                                "site": st.session_state.site,
                                "shift": record.get("shift"),
                                "name": record.get("name"),
                                "att": record.get("att"),
                                "position": record.get("position"),
                                "notes": record.get("notes", ""),
                                "emp_n_id": selected_employee.get("emp_n_id", ""),
                                "emp_bank": selected_employee.get("emp_bank", "")
                            }
                            
                            insert_row("attendance", attendance_data)
                            success_count += 1
                        else:
                            failed_count += 1
                            st.error(f"❌ لم يتم العثور على بيانات الموظف: {record.get('name')}")
                    except Exception as e:
                        failed_count += 1
                        st.error(f"❌ خطأ في حفظ بيان #{i+1}: {str(e)}")
                
                if success_count > 0:
                    st.success(f"✅ تم حفظ {success_count} بيان حضور بنجاح!")
                    
                    # مسح جميع البيانات بعد الحفظ الناجح
                    st.session_state.attendance_records = [{}]  # بيان واحد فارغ
                    st.session_state.form_key += 1  # زيادة المفتاح لإجبار إعادة التحميل
                    
                    st.rerun()
                
                if failed_count > 0:
                    st.warning(f"⚠️ فشل في حفظ {failed_count} بيان")

# تشغيل الصفحة
if __name__ == "__main__":
    attendance_page()