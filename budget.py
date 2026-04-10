"""予算計算ロジック"""
from __future__ import annotations

import calendar
from statistics import quantiles


def calc_base_income(income_records: list[dict]) -> int:
    """基準月収（Q1: 第1四分位数）を算出する。"""
    amounts = sorted(int(r["月収"]) for r in income_records if r.get("月収"))
    if not amounts:
        return 0
    if len(amounts) < 4:
        return min(amounts)
    return int(quantiles(amounts, n=4)[0])


def calc_monthly_fixed_costs(fixed_costs: list[dict], month: int) -> int:
    """指定月の固定費合計を算出する。"""
    total = 0
    for fc in fixed_costs:
        kind = str(fc.get("種別", ""))
        amount = int(fc.get("月額", 0) or 0)
        if kind == "monthly":
            total += amount
        elif kind == "annual":
            bm = fc.get("計上月", "")
            if bm and int(bm) == month:
                total += amount
    return total


def calc_genre_budgets(
    base_income: int,
    monthly_fixed: int,
    genre_settings: list[dict],
    prev_month_income: int | None,
) -> dict[str, int]:
    """ジャンル別予算を算出する。

    コアジャンル: 基準月収ベースの変動費予算 × 割合（安定）
    その他:       前月月収ベースの変動費予算 − コア合計（余剰吸収）
    """
    base_variable = max(base_income - monthly_fixed, 0)

    budgets: dict[str, int] = {}
    core_total = 0

    for g in genre_settings:
        name = g["ジャンル名"]
        if name == "その他":
            continue
        ratio = float(g.get("割合", 0) or 0) / 100.0
        b = int(base_variable * ratio)
        budgets[name] = b
        core_total += b

    actual = prev_month_income if prev_month_income else base_income
    actual_variable = max(actual - monthly_fixed, 0)
    budgets["その他"] = max(actual_variable - core_total, 0)

    return budgets


def calc_status_hints(
    spent: int, budget: int, current_day: int, total_days: int, use_pace: bool
) -> list[str]:
    """現在のステータスに応じた閾値までの金額ヒントを返す。"""
    if budget <= 0:
        return []

    if use_pace:
        elapsed = max(current_day / total_days, 0.05)
        boundaries = [
            int(0.8 * elapsed * budget),
            int(1.0 * elapsed * budget),
            int(1.2 * elapsed * budget),
            budget,
        ]
    else:
        boundaries = [
            int(0.4 * budget),
            int(0.7 * budget),
            int(0.9 * budget),
            budget,
        ]

    status_names = ["余裕", "適正", "注意", "使いすぎ", "超過"]

    # 現在のインデックスを求める（0=余裕 〜 4=超過）
    idx = sum(1 for b in boundaries if spent >= b)

    hints: list[str] = []

    if idx == 4:  # 超過
        overspend = spent - budget
        hints.append(f"¥{overspend:,} 超過中")
        reduce = spent - boundaries[2] + 1
        if reduce > 0:
            hints.append(f"¥{reduce:,} 減らすと「使いすぎ」")
    else:
        # 悪化方向：次の閾値まで
        diff_worse = boundaries[idx] - spent
        if diff_worse > 0:
            hints.append(f"あと ¥{diff_worse:,} で「{status_names[idx + 1]}」")
        # 改善方向：前の閾値を下回るには
        if idx > 0:
            reduce = spent - boundaries[idx - 1] + 1
            if reduce > 0:
                hints.append(f"¥{reduce:,} 減らすと「{status_names[idx - 1]}」")

    return hints


def calc_ratio_status(spent: int, budget: int) -> tuple[str, str, float]:
    """消費率のみでステータスを判定する（日付連動なし）。"""
    if budget <= 0:
        return ("超過", "#f44336", float("inf")) if spent > 0 else ("—", "#888", 0.0)

    ratio = spent / budget

    if ratio > 1.0:
        return "超過", "#f44336", ratio
    if ratio >= 0.9:
        return "使いすぎ", "#f44336", ratio
    if ratio >= 0.7:
        return "注意", "#FFC107", ratio
    if ratio >= 0.4:
        return "適正", "#66BB6A", ratio
    return "余裕", "#4CAF50", ratio


def calc_pace_status(
    spent: int, budget: int, current_day: int, total_days: int
) -> tuple[str, str, float]:
    """ペースベースのステータス判定。

    Returns:
        (ステータスラベル, カラーコード, ペース比)
    """
    if budget <= 0:
        return ("超過", "#f44336", float("inf")) if spent > 0 else ("—", "#888", 0.0)

    consumption = spent / budget

    # 予算超過は最優先
    if consumption > 1.0:
        return "超過", "#f44336", consumption

    # ペース比（経過率は最低5%で計算し月初の振れを抑制）
    elapsed = max(current_day / total_days, 0.05)
    pace = consumption / elapsed

    if pace < 0.8:
        return "余裕", "#4CAF50", pace
    if pace < 1.0:
        return "適正", "#66BB6A", pace
    if pace < 1.2:
        return "注意", "#FFC107", pace
    return "使いすぎ", "#f44336", pace


def get_prev_month(year: int, month: int) -> tuple[int, int]:
    """前月の (年, 月) を返す。"""
    if month == 1:
        return year - 1, 12
    return year, month - 1
