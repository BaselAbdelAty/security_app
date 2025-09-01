import streamlit as st
from login_page import login_page
from main_page import main_page
from sites import sites_page
from employees import employees_page
from attendance import attendance_page

def main():
    if "user" not in st.session_state or st.session_state.user is None:
        login_page()
    else:
        page = st.session_state.get("page", "main")
        if page == "main":
            main_page()
        elif page == "sites":
            sites_page()
        elif page == "employees":
            employees_page()
        elif page == "attendance":
            attendance_page()

if __name__ == "__main__":
    main()