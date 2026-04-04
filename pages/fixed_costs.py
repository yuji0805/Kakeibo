import streamlit as st
from datetime import date

from sheets import get_fixed_costs, save_fixed_cost, update_fixed_cost, delete_fixed_cost
from budget import calc_monthly_fixed_costs

st.header("🔧 固定費設定")

fixed_costs = get_fixed_costs()
current_month = date.today().month
total = calc_monthly_fixed_costs(fixed_costs, current_month)

st.metric("当月の固定費合計", f"¥{total:,}")
st.divider()

# ── 登録済み固定費 ──
if fixed_costs:
    for i, fc in enumerate(fixed_costs):
        amt_val = int(fc.get("月額", 0) or 0)
        kind_val = fc.get("種別", "monthly")
        label = f"{fc['項目名']} — ¥{amt_val:,}（{kind_val}）"

        with st.expander(label):
            with st.form(f"edit_{i}"):
                name = st.text_input("項目名", value=fc["項目名"], key=f"fn_{i}")
                amt = st.number_input(
                    "月額（円）", value=amt_val, min_value=0, step=100, key=f"fa_{i}"
                )
                kind_opts = ["monthly", "annual"]
                kind_idx = kind_opts.index(kind_val) if kind_val in kind_opts else 0
                kind = st.selectbox("種別", kind_opts, index=kind_idx, key=f"fk_{i}")
                bm_val = int(fc.get("計上月") or 1)
                bm = st.number_input(
                    "計上月（annualのみ）",
                    min_value=1,
                    max_value=12,
                    value=bm_val,
                    key=f"fb_{i}",
                )

                if st.form_submit_button("更新", use_container_width=True):
                    update_fixed_cost(
                        i, name, amt, kind, str(bm) if kind == "annual" else ""
                    )
                    st.success("更新しました")
                    st.rerun()

            if st.button("🗑 削除", key=f"del_{i}"):
                delete_fixed_cost(i)
                st.rerun()
else:
    st.info("固定費がまだ登録されていません。")

st.divider()

# ── 固定費を追加 ──
st.subheader("固定費を追加")

with st.form("add_fc"):
    name = st.text_input("項目名")
    amt = st.number_input("月額（円）", min_value=0, step=100, key="new_amt")
    kind = st.selectbox("種別", ["monthly", "annual"], key="new_kind")
    bm = st.number_input(
        "計上月（annualのみ）", min_value=1, max_value=12, value=1, key="new_bm"
    )

    if st.form_submit_button("追加する", use_container_width=True, type="primary"):
        if not name:
            st.error("項目名を入力してください。")
        else:
            save_fixed_cost(name, amt, kind, str(bm) if kind == "annual" else "")
            st.success(f"✅ {name} を追加しました")
            st.rerun()
