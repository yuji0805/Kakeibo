import streamlit as st
import calendar
from datetime import date

from sheets import get_income_history, get_fixed_costs, get_genre_settings, get_expenses, get_budget_adjustments, save_budget_adjustments
from budget import (
    calc_base_income,
    calc_monthly_fixed_costs,
    calc_genre_budgets,
    calc_pace_status,
    get_prev_month,
)

STATUS_EMOJI = {"余裕": "🟢", "適正": "🟢", "注意": "🟡", "使いすぎ": "🔴", "超過": "🔴⚠️", "—": ""}

today = date.today()
year, month = today.year, today.month
total_days = calendar.monthrange(year, month)[1]
current_day = today.day
year_month = f"{year}-{month:02d}"
prev_y, prev_m = get_prev_month(year, month)
prev_ym = f"{prev_y}-{prev_m:02d}"

# ── データ取得 ──
income_history = get_income_history()
fixed_costs = get_fixed_costs()
genres = get_genre_settings()
expenses = get_expenses(year_month)

# ── 計算 ──
base_income = calc_base_income(income_history)
monthly_fixed = calc_monthly_fixed_costs(fixed_costs, month)

prev_income = None
for r in income_history:
    if r["年月"] == prev_ym:
        prev_income = int(r["月収"])
        break

budgets = calc_genre_budgets(base_income, monthly_fixed, genres, prev_income)

# ── 予算微調整（スプレッドシート保存 + セッション管理）──
ADJUST_KEY = "budget_adjustments"
if ADJUST_KEY not in st.session_state:
    st.session_state[ADJUST_KEY] = get_budget_adjustments(year_month)
adjustments: dict[str, int] = st.session_state[ADJUST_KEY]

# 調整を予算に反映
adjusted_budgets = dict(budgets)
total_adj = sum(v for k, v in adjustments.items() if k != "その他")
for name, adj in adjustments.items():
    if name != "その他":
        adjusted_budgets[name] = adjusted_budgets.get(name, 0) + adj
adjusted_budgets["その他"] = max(budgets.get("その他", 0) - total_adj, 0)
budgets = adjusted_budgets

spent_by_genre: dict[str, int] = {}
for e in expenses:
    g = e["ジャンル"]
    spent_by_genre[g] = spent_by_genre.get(g, 0) + int(e["金額"])

# ── ヘッダ ──
st.markdown(f"### 🗓 {year}年{month}月（{current_day}日経過 / {total_days}日）")

if not income_history:
    st.warning("月収が未登録です。サイドバーの「月収・予算設定」から入力してください。")

source = prev_income if prev_income else base_income
variable_total = max(source - monthly_fixed, 0)

c1, c2 = st.columns(2)
c1.metric("基準月収", f"¥{base_income:,}")
source_label = f"¥{prev_income:,}" if prev_income else f"¥{base_income:,}（基準）"
c2.metric("予算原資（前月月収）", source_label)

c3, c4 = st.columns(2)
c3.metric("固定費", f"¥{monthly_fixed:,}")
c4.metric("変動費予算", f"¥{variable_total:,}")

st.divider()

# ── ジャンル別カード ──
for g in genres:
    name = g["ジャンル名"]
    budget = budgets.get(name, 0)
    spent = spent_by_genre.get(name, 0)
    remaining = budget - spent
    status, color, _ = calc_pace_status(spent, budget, current_day, total_days)
    emoji = STATUS_EMOJI.get(status, "")
    pct = min(spent / budget * 100, 100) if budget > 0 else (100 if spent > 0 else 0)

    st.markdown(
        f"""
<div style="margin-bottom:.25rem;padding:.75rem;background:#1a1a2e;border-radius:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.25rem;">
    <strong>{name}</strong><span>{status} {emoji}</span>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.85rem;color:#aaa;margin-bottom:.4rem;">
    <span>¥{spent:,} / ¥{budget:,}</span><span>残り ¥{remaining:,}</span>
  </div>
  <div style="background:#333;border-radius:6px;height:10px;overflow:hidden;">
    <div style="background:{color};width:{pct:.1f}%;height:100%;border-radius:6px;"></div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ＋/− ボタン（「その他」以外に表示、その他の予算が原資）
    if name != "その他":
        bcol1, bcol2, bcol3 = st.columns([1, 1, 3])
        current_adj = adjustments.get(name, 0)
        other_budget = budgets.get("その他", 0)
        with bcol1:
            if st.button("−¥1,000", key=f"dec_{name}", disabled=(current_adj <= -budget + 1000)):
                adjustments[name] = current_adj - 1000
                st.session_state[ADJUST_KEY] = adjustments
                st.rerun()
        with bcol2:
            if st.button("＋¥1,000", key=f"inc_{name}", disabled=(other_budget < 1000)):
                adjustments[name] = current_adj + 1000
                st.session_state[ADJUST_KEY] = adjustments
                st.rerun()

# ── 保存ボタン ──
has_unsaved = any(v != 0 for k, v in adjustments.items() if k != "その他")
saved_adj = get_budget_adjustments(year_month)
is_dirty = adjustments != saved_adj

if is_dirty:
    if st.button("💾 予算調整を保存", use_container_width=True, type="primary"):
        save_budget_adjustments(year_month, adjustments)
        st.success("✅ 予算調整を保存しました")
        st.rerun()

# ── フッタ ──
total_spent = sum(spent_by_genre.values())
total_budget = sum(budgets.values())
st.divider()
st.markdown(f"**合計支出: ¥{total_spent:,} / ¥{total_budget:,}**")

if st.button("＋ 支出を入力", use_container_width=True, type="primary"):
    st.switch_page("pages/expense_input.py")

if st.button("🔄 データを更新", use_container_width=True):
    st.cache_data.clear()
    st.session_state.pop(ADJUST_KEY, None)
    st.rerun()
