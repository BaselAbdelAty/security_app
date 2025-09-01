import streamlit as st
from db import read_all

def login_page():
    st.title("🔐 Security App - Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = read_all("users")
        user_found = None
        for u in users:
            if u["email"] == email and u["password"] == password:
                user_found = u
                break
        
        if user_found:
            st.session_state.user = {"username": user_found["username"], "email": user_found["email"]}
            st.session_state.page = "main"
            st.success(f"✅ Welcome {user_found['username']}")
            st.rerun()
        else:
            st.error("❌ Invalid email or password")
