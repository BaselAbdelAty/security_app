import streamlit as st

def main_page():
    st.title("🏠 الصفحة الرئيسية")

    user = st.session_state.get("user", {})
    st.write(f"👤 المستخدم الحالي: {user.get('username')}")

    if st.button("📍 إدارة المواقع"):
            st.session_state["page"] = "sites"

    if st.button("👨‍💼 إدارة الموظفين"):
        st.session_state["page"] = "employees"
        
    if st.button("🗓️ إدارة الحضور"):
        st.session_state["page"] = "attendance"  

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        st.success("✅ تم تسجيل الخروج")
        st.rerun()
