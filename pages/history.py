import streamlit as st
import pandas as pd
from datetime import date

from sheets import get_expenses
from budget import get_prev_month

st.header("📈 履歴")

today = date.today()

c1, c2 = st.columns(2)
with c1:
    sel_year = st.number_input("年", value=today.year, min_value=2020, max_value=2100, key="hy")
with c2:
    sel_month = st.number_input(
        "月", value=today.month, min_value=1, max_value=12, key="hm"
    )

ym = f"{int(sel_year)}-{int(sel_month):02d}"
expenses = get_expenses(ym)

# ── 月の集計 ──
st.subheader(f"{int(sel_year)}年{int(sel_month)}月の支出")

if expenses:
    total = sum(int(e["金額"]) for e in expenses)
    st.metric("合計", f"¥{total:,}")

    # ジャンル別
    by_genre: dict[str, int] = {}
    for e in expenses:
        g = e["ジャンル"]
        by_genre[g] = by_genre.get(g, 0) + int(e["金額"])

    for genre, amt in sorted(by_genre.items(), key=lambda x: -x[1]):
        st.markdown(f"- **{genre}**: ¥{amt:,}")

    st.divider()

    # 明細
    st.subheader("明細")
    for e in sorted(expenses, key=lambda x: str(x["日付"]), reverse=True):
        memo = f" — {e['メモ']}" if e.get("メモ") else ""
        st.markdown(
            f"`{e['日付']}` {e['ジャンル']} **¥{int(e['金額']):,}**{memo}"
        )
else:
    st.info("この月の支出データはありません。")

# ── 月別比較（3ヶ月） ──
st.divider()
st.subheader("月別比較（3ヶ月）")

data: list[dict] = []
y, m = int(sel_year), int(sel_month)
for _ in range(3):
    month_ym = f"{y}-{m:02d}"
    month_expenses = get_expenses(month_ym)
    by_g: dict[str, int] = {}
    for e in month_expenses:
        g = e["ジャンル"]
        by_g[g] = by_g.get(g, 0) + int(e["金額"])
    for genre, amt in by_g.items():
        data.append({"月": month_ym, "ジャンル": genre, "金額": amt})
    y, m = get_prev_month(y, m)

if data:
    df = pd.DataFrame(data)
    pivot = df.pivot_table(index="月", columns="ジャンル", values="金額", fill_value=0)
    pivot = pivot.sort_index()
    st.bar_chart(pivot)
else:
    st.info("比較データがありません。")
