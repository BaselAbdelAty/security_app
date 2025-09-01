# sites.py
import streamlit as st
import pandas as pd
from db import read_all, insert_row, get_sheet

def sites_page():
    st.title("📍 إدارة المواقع")
    
    # 🔹 أزرار التنقل في أعلى الصفحة
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🏠 الرئيسية", use_container_width=True):
            st.session_state["page"] = "main"
            st.rerun()
    with col2:
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            # مسح التخزين المؤقت بالكامل
            st.cache_data.clear()
            if "data_version" in st.session_state:
                st.session_state.data_version += 1
            st.rerun()
    with col3:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["page"] = "login"
            st.rerun()
    
    # جلب البيانات من Google Sheets (المواقع غير المحذوفة فقط)
    def load_active_sites_data():
        all_sites = read_all("sites")
        # تصفية المواقع غير المحذوفة (حيث deleted != 1 أو غير موجود)
        active_sites = []
        for site in all_sites:
            # إذا لم يكن عمود deleted موجوداً أو قيمته ليست 1
            if "deleted" not in site or str(site.get("deleted", "0")) != "1":
                active_sites.append(site)
        return active_sites
    
    # استخدام التخزين المؤقت ولكن مع مفتاح يتغير عند التحديث
    if "data_version" not in st.session_state:
        st.session_state.data_version = 0
        
    @st.cache_data(ttl=10, show_spinner="جاري تحميل البيانات...")  # تقليل وقت التخزين المؤقت
    def get_cached_sites(version):
        return load_active_sites_data()
    
    active_sites = get_cached_sites(st.session_state.data_version)
    df = pd.DataFrame(active_sites)
    
    # قسم إضافة موقع جديد
    with st.expander("➕ إضافة موقع جديد", expanded=False):
        with st.form("add_site_form"):
            col1, col2 = st.columns(2)
            with col1:
                site = st.text_input("اسم الموقع *")
                client = st.text_input("اسم العميل *")
            with col2:
                location = st.text_input("الموقع *")
                address = st.text_input("العنوان *")
            
            submitted = st.form_submit_button("إضافة الموقع")
            if submitted:
                if site and client and location and address:
                    # إضافة عمود deleted بالقيمة 0 للمواقع الجديدة
                    insert_row("sites", {
                        "site": site,
                        "client": client,
                        "location": location,
                        "address": address,
                        "deleted": "0"
                    })
                    # زيادة رقم الإصدار لإجبار إعادة تحميل البيانات
                    st.session_state.data_version += 1
                    st.success("✅ تم إضافة الموقع بنجاح!")
                    st.rerun()
                else:
                    st.warning("⚠️ يرجى ملء جميع الحقول الإلزامية (*)")
    
    # قسم البحث
    st.subheader("🔍 البحث في المواقع")
    search_input = st.text_input("ابحث باسم الموقع أو العميل", placeholder="اكتب للبحث...")
    
    if search_input:
        results = df[df["site"].str.contains(search_input, case=False, na=False) | 
                    df["client"].str.contains(search_input, case=False, na=False)]
        if results.empty:
            st.info("ℹ️ لم يتم العثور على نتائج مطابقة")
        else:
            st.dataframe(results, use_container_width=True)
    
    # قسم عرض وتعديل جميع المواقع
    st.subheader("📋 جميع المواقع")
    
    if not df.empty:
        # استخدام data_editor للتعديل (بدون عرض عمود deleted)
        columns_to_show = [col for col in ["site", "client", "location", "address"] if col in df.columns]
        edited_df = st.data_editor(
            df[columns_to_show],
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "site": st.column_config.TextColumn("اسم الموقع", width="medium", required=True),
                "client": st.column_config.TextColumn("العميل", width="medium", required=True),
                "location": st.column_config.TextColumn("الموقع", width="medium", required=True),
                "address": st.column_config.TextColumn("العنوان", width="large", required=True)
            },
            key="sites_editor"
        )
        
        # أزرار الحفظ والحذف
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 حفظ التعديلات", use_container_width=True):
                ws = get_sheet("sites")
                data = ws.get_all_values()
                headers = data[0]
                
                # تحديث كل صف تم تعديله
                for index, row in edited_df.iterrows():
                    original_row = df.iloc[index]
                    if not row.equals(original_row[columns_to_show]):
                        # البحث عن الصف في البيانات الأصلية
                        row_idx = None
                        for i, sheet_row in enumerate(data[1:], start=2):
                            if (sheet_row[0] == original_row["site"] and 
                                sheet_row[1] == original_row["client"] and 
                                sheet_row[2] == original_row["location"] and 
                                sheet_row[3] == original_row["address"]):
                                row_idx = i
                                break
                        
                        if row_idx:
                            # تحديث الصف في Google Sheet
                            updated_row = [row[col] if col in row else "" for col in headers]
                            ws.update(f"A{row_idx}:{chr(64 + len(headers))}{row_idx}", [updated_row])
                
                # زيادة رقم الإصدار لإجبار إعادة تحميل البيانات
                st.session_state.data_version += 1
                st.success("✅ تم حفظ التعديلات بنجاح!")
                st.rerun()
        
        with col2:
            # قسم حذف المواقع
            if not df.empty:
                site_options = {i: f"{df.loc[i, 'site']} - {df.loc[i, 'client']}" for i in df.index}
                sites_to_delete = st.multiselect(
                    "اختر المواقع للحذف:",
                    options=list(site_options.keys()),
                    format_func=lambda x: site_options[x]
                )
                
                if sites_to_delete:
                    st.warning("⚠️ سيتم حذف المواقع المحددة. يمكن استعادتها لاحقاً.")
                    
                    # استخدام زر واحد للحذف مع التأكيد
                    if st.button("🗑️ تأكيد الحذف", type="primary", use_container_width=True):
                        ws = get_sheet("sites")
                        data = ws.get_all_values()
                        headers = data[0]
                        
                        # تحديد موقع عمود deleted إذا كان موجوداً
                        deleted_col_index = headers.index("deleted") + 1 if "deleted" in headers else None
                        
                        # إذا لم يكن عمود deleted موجوداً، نضيفه أولاً
                        if deleted_col_index is None:
                            # إضافة عمود deleted في النهاية
                            ws.update_cell(1, len(headers) + 1, "deleted")
                            deleted_col_index = len(headers) + 1
                        
                        # تحديث قيمة deleted إلى "1" للمواقع المحددة
                        for index in sites_to_delete:
                            site_data = df.iloc[index]
                            row_number = None
                            
                            # البحث عن الصف المناسب في البيانات
                            for i, row in enumerate(data[1:], start=2):
                                if (row[0] == site_data["site"] and 
                                    row[1] == site_data["client"] and 
                                    row[2] == site_data["location"] and 
                                    row[3] == site_data["address"]):
                                    row_number = i
                                    break
                            
                            if row_number:
                                # تحديث قيمة العمود deleted إلى "1"
                                ws.update_cell(row_number, deleted_col_index, "1")
                        
                        # زيادة رقم الإصدار وإعادة تحميل الصفحة
                        st.session_state.data_version += 1
                        st.success("✅ تم حذف المواقع المحددة بنجاح!")
                        st.rerun()
    else:
        st.info("ℹ️ لا توجد مواقع متاحة حالياً. يمكنك إضافة مواقع جديدة باستخدام نموذج الإضافة أعلاه.")