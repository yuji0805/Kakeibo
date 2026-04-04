import streamlit as st
from datetime import date

from sheets import get_genre_settings, save_expense

st.header("💰 支出入力")

genres = get_genre_settings()
genre_names = [g["ジャンル名"] for g in genres]

with st.form("expense_form"):
    expense_date = st.date_input("日付", value=date.today())
    amount = st.number_input("金額（円）", min_value=0, value=0, step=1)
    genre = st.selectbox("ジャンル", genre_names)
    memo = st.text_input("メモ（任意）")

    if st.form_submit_button("記録する", use_container_width=True, type="primary"):
        if amount <= 0:
            st.error("金額を入力してください。")
        else:
            save_expense(expense_date.strftime("%Y-%m-%d"), amount, genre, memo)
            st.success(f"✅ {genre} ¥{amount:,} を記録しました！")
            st.balloons()
