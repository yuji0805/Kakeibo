import streamlit as st
from datetime import date

from sheets import (
    get_income_history,
    get_genre_settings,
    get_fixed_costs,
    save_income,
    save_genre_ratios,
)
from budget import calc_base_income, calc_monthly_fixed_costs

st.header("💵 月収・予算設定")

income_history = get_income_history()
genres = get_genre_settings()
fixed_costs = get_fixed_costs()
today = date.today()

# ── 月収入力 ──
st.subheader("月収を入力")

c1, c2 = st.columns(2)
with c1:
    in_year = st.number_input("年", value=today.year, min_value=2020, max_value=2100)
with c2:
    in_month = st.number_input("月", value=today.month, min_value=1, max_value=12)

ym = f"{int(in_year)}-{int(in_month):02d}"
existing = next((int(r["月収"]) for r in income_history if r["年月"] == ym), 0)

with st.form("income_form"):
    amount = st.number_input(f"{ym} の月収（円）", value=existing, min_value=0, step=1000)
    if st.form_submit_button("保存", use_container_width=True, type="primary"):
        save_income(ym, amount)
        st.success(f"✅ {ym} の月収 ¥{amount:,} を保存しました")
        st.rerun()

st.divider()

# ── 基準月収 ──
base = calc_base_income(income_history)
st.metric("基準月収（Q1）", f"¥{base:,}")
if income_history:
    st.caption(f"月収データ {len(income_history)} 件から算出")

st.divider()

# ── ジャンル別予算割合 ──
st.subheader("ジャンル別予算割合")

monthly_fixed = calc_monthly_fixed_costs(fixed_costs, today.month)
base_var = max(base - monthly_fixed, 0)
st.caption(
    f"基準変動費予算: ¥{base_var:,}（基準月収 ¥{base:,} − 固定費 ¥{monthly_fixed:,}）"
)

with st.form("genre_form"):
    updated: list[dict] = []
    core_total = 0.0

    for g in genres:
        name = g["ジャンル名"]
        if name == "その他":
            updated.append({"ジャンル名": name, "割合": 0, "表示順": g["表示順"]})
            continue

        ratio = st.number_input(
            f"{name}（%）",
            value=float(g.get("割合", 0) or 0),
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            key=f"r_{name}",
        )
        preview = int(base_var * ratio / 100)
        st.caption(f"→ 予算目安: ¥{preview:,}")
        core_total += ratio
        updated.append({"ジャンル名": name, "割合": ratio, "表示順": g["表示順"]})

    other_pct = max(100 - core_total, 0)
    other_preview = max(base_var - int(base_var * core_total / 100), 0)
    st.markdown(
        f"**その他: {other_pct:.1f}%（¥{other_preview:,}）** ＋ 前月月収の余剰分"
    )

    if core_total > 100:
        st.error(f"⚠️ コアジャンル合計が100%超です（{core_total:.1f}%）")

    if st.form_submit_button("割合を保存", use_container_width=True, type="primary"):
        if core_total > 100:
            st.error("合計を100%以下に調整してください。")
        else:
            save_genre_ratios(updated)
            st.success("✅ 割合を保存しました")
            st.rerun()

# ── 月収履歴一覧 ──
st.divider()
st.subheader("月収履歴")
if income_history:
    for r in sorted(income_history, key=lambda x: x["年月"], reverse=True):
        st.markdown(f"- **{r['年月']}**: ¥{int(r['月収']):,}")
else:
    st.info("月収データがまだありません。")
