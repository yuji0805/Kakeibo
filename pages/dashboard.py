import streamlit as st
import calendar
from datetime import date

from sheets import get_income_history, get_fixed_costs, get_genre_settings, get_expenses, get_budget_adjustments, save_budget_adjustments
from budget import (
    calc_base_income,
    calc_monthly_fixed_costs,
    calc_genre_budgets,
    calc_pace_status,
    calc_ratio_status,
    calc_status_hints,
    get_prev_month,
)

# ペースベース判定を使うジャンル
PACE_GENRES = {"食費", "水代"}

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
savings_spent = 0
for e in expenses:
    g = e["ジャンル"]
    if g == "貯金":
        savings_spent += int(e["金額"])
    else:
        spent_by_genre[g] = spent_by_genre.get(g, 0) + int(e["金額"])

total_spent = sum(spent_by_genre.values())
total_budget = sum(budgets.values())

# ── 月末に変動費余剰を貯金から差し引き ──
budget_surplus = max(total_budget - total_spent, 0)
is_last_day = (current_day == total_days)
net_savings = savings_spent - budget_surplus if is_last_day else savings_spent

# ── ヘッダ ──
st.markdown(f"### 🗓 {year}年{month}月（{current_day}日経過 / {total_days}日）")

if not income_history:
    st.warning("月収が未登録です。「月収・予算設定」から入力してください。")

if st.button("＋ 支出を入力", use_container_width=True, type="primary", key="input_top"):
    st.switch_page("pages/expense_input.py")

# ── 合計支出メータ ──
source = prev_income if prev_income else base_income
variable_total = max(source - monthly_fixed, 0)

total_status, total_color, _ = calc_pace_status(total_spent, total_budget, current_day, total_days)
total_emoji = STATUS_EMOJI.get(total_status, "")
total_pct = min(total_spent / total_budget * 100, 100) if total_budget > 0 else 0
total_remaining = total_budget - total_spent
total_hints = calc_status_hints(total_spent, total_budget, current_day, total_days, use_pace=True)

st.markdown(
    f"""
<div style="margin-bottom:.5rem;padding:.85rem;background:#1a1a2e;border-radius:8px;border:1px solid {total_color}44;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.25rem;">
    <strong>📊 今月の合計支出</strong><span>{total_status} {total_emoji}</span>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.85rem;color:#aaa;margin-bottom:.5rem;">
    <span>¥{total_spent:,} / ¥{total_budget:,}</span><span>残り ¥{total_remaining:,}</span>
  </div>
  <div style="background:#333;border-radius:6px;height:14px;overflow:hidden;">
    <div style="background:{total_color};width:{total_pct:.1f}%;height:100%;border-radius:6px;"></div>
  </div>
</div>""",
    unsafe_allow_html=True,
)

if total_hints:
    st.markdown(f"<small style='color:#aaa;'>{'　／　'.join(total_hints)}</small>", unsafe_allow_html=True)

# ── 固定費・変動費予算 ──
c3, c4, c5 = st.columns(3)
c3.metric("固定費", f"¥{monthly_fixed:,}")
c4.metric("変動費予算", f"¥{variable_total:,}")
if is_last_day and budget_surplus > 0:
    c5.metric(
        "💰 今月くずした貯金（実質）",
        f"¥{net_savings:,}",
        delta=f"−¥{budget_surplus:,} 予算余り相殺",
        delta_color="off",
    )
else:
    c5.metric("💰 今月くずした貯金", f"¥{savings_spent:,}")

st.divider()

# ── ジャンル別カード ──
for g in genres:
    name = g["ジャンル名"]
    budget = budgets.get(name, 0)
    spent = spent_by_genre.get(name, 0)
    remaining = budget - spent

    # 食費・水代はペースベース、それ以外は割合ベース
    if name in PACE_GENRES:
        status, color, _ = calc_pace_status(spent, budget, current_day, total_days)
    else:
        status, color, _ = calc_ratio_status(spent, budget)

    emoji = STATUS_EMOJI.get(status, "")
    pct = min(spent / budget * 100, 100) if budget > 0 else (100 if spent > 0 else 0)
    hints = calc_status_hints(spent, budget, current_day, total_days, name in PACE_GENRES)

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

    if hints:
        st.markdown(f"<small style='color:#aaa;'>{'　／　'.join(hints)}</small>", unsafe_allow_html=True)

    # ＋/− ボタン（「その他」以外に表示）
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

st.divider()

# ── 保存ボタン ──
saved_adj = get_budget_adjustments(year_month)
is_dirty = adjustments != saved_adj
if is_dirty:
    if st.button("💾 予算調整を保存", use_container_width=True, type="primary"):
        save_budget_adjustments(year_month, adjustments)
        st.success("✅ 予算調整を保存しました")
        st.rerun()

if st.button("🔄 データを更新", use_container_width=True):
    st.cache_data.clear()
    st.session_state.pop(ADJUST_KEY, None)
    st.rerun()
