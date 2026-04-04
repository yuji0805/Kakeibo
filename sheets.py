"""Google Sheets データアクセス層"""
from __future__ import annotations

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WS_INCOME = "月収履歴"
WS_FIXED = "固定費マスタ"
WS_GENRES = "ジャンル設定"
WS_EXPENSES = "支出データ"
WS_ADJUSTMENTS = "予算調整"

DEFAULT_GENRES = [
    ["食費", 40.0, 1],
    ["水代", 4.0, 2],
    ["飲み会代", 16.0, 3],
    ["薬局代", 4.0, 4],
    ["革代", 2.4, 5],
    ["その他", 0, 6],
]


# ── 接続 ──


@st.cache_resource
def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _get_ss() -> gspread.Spreadsheet:
    return _get_client().open_by_key(st.secrets["spreadsheet_id"])


def init_spreadsheet() -> None:
    """ワークシートが無ければ作成し、デフォルトデータを投入する。"""
    ss = _get_ss()
    existing = {ws.title for ws in ss.worksheets()}

    sheets_def = {
        WS_INCOME: ["年月", "月収"],
        WS_FIXED: ["項目名", "月額", "種別", "計上月"],
        WS_GENRES: ["ジャンル名", "割合", "表示順"],
        WS_EXPENSES: ["日付", "金額", "ジャンル", "メモ"],
        WS_ADJUSTMENTS: ["年月", "ジャンル名", "調整額"],
    }

    for name, headers in sheets_def.items():
        if name not in existing:
            ws = ss.add_worksheet(title=name, rows=1000, cols=len(headers))
            ws.update(values=[headers], range_name="A1")
            if name == WS_GENRES:
                ws.update(values=DEFAULT_GENRES, range_name="A2")


# ── 読み取り (キャッシュ付き) ──


@st.cache_data(ttl=120)
def get_income_history() -> list[dict]:
    return _get_ss().worksheet(WS_INCOME).get_all_records()


@st.cache_data(ttl=120)
def get_fixed_costs() -> list[dict]:
    return _get_ss().worksheet(WS_FIXED).get_all_records()


@st.cache_data(ttl=120)
def get_genre_settings() -> list[dict]:
    records = _get_ss().worksheet(WS_GENRES).get_all_records()
    return sorted(records, key=lambda r: int(r.get("表示順", 99)))


@st.cache_data(ttl=120)
def _get_all_expenses() -> list[dict]:
    return _get_ss().worksheet(WS_EXPENSES).get_all_records()


def get_expenses(year_month: str | None = None) -> list[dict]:
    """支出データを取得する。year_month 指定時はその月だけ返す。"""
    records = _get_all_expenses()
    if year_month:
        return [r for r in records if str(r["日付"]).startswith(year_month)]
    return list(records)


# ── 書き込み ──


def save_income(year_month: str, amount: int) -> None:
    ws = _get_ss().worksheet(WS_INCOME)
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if r["年月"] == year_month:
            ws.update_cell(i + 2, 2, amount)
            get_income_history.clear()
            return
    ws.append_row([year_month, amount], value_input_option="USER_ENTERED")
    get_income_history.clear()


def save_fixed_cost(name: str, amount: int, kind: str, billing_month: str = "") -> None:
    ws = _get_ss().worksheet(WS_FIXED)
    ws.append_row([name, amount, kind, billing_month], value_input_option="USER_ENTERED")
    get_fixed_costs.clear()


def update_fixed_cost(
    row_idx: int, name: str, amount: int, kind: str, billing_month: str = ""
) -> None:
    ws = _get_ss().worksheet(WS_FIXED)
    ws.update(
        values=[[name, amount, kind, billing_month]],
        range_name=f"A{row_idx + 2}:D{row_idx + 2}",
    )
    get_fixed_costs.clear()


def delete_fixed_cost(row_idx: int) -> None:
    ws = _get_ss().worksheet(WS_FIXED)
    ws.delete_rows(row_idx + 2)
    get_fixed_costs.clear()


def save_genre_ratios(genres: list[dict]) -> None:
    ws = _get_ss().worksheet(WS_GENRES)
    rows = [[g["ジャンル名"], g["割合"], g["表示順"]] for g in genres]
    ws.update(values=rows, range_name=f"A2:C{len(rows) + 1}")
    get_genre_settings.clear()


def save_expense(date: str, amount: int, genre: str, memo: str = "") -> None:
    ws = _get_ss().worksheet(WS_EXPENSES)
    ws.append_row([date, amount, genre, memo], value_input_option="USER_ENTERED")
    _get_all_expenses.clear()


# ── 予算調整 ──


@st.cache_data(ttl=120)
def get_budget_adjustments(year_month: str) -> dict[str, int]:
    """指定月の予算調整を {ジャンル名: 調整額} で返す。"""
    ws = _get_ss().worksheet(WS_ADJUSTMENTS)
    records = ws.get_all_records()
    return {
        r["ジャンル名"]: int(r["調整額"])
        for r in records
        if r["年月"] == year_month and int(r.get("調整額", 0)) != 0
    }


def save_budget_adjustments(year_month: str, adjustments: dict[str, int]) -> None:
    """指定月の予算調整を保存する（既存行は上書き、新規は追加）。"""
    ws = _get_ss().worksheet(WS_ADJUSTMENTS)
    records = ws.get_all_records()

    # 既存の行番号を特定
    existing: dict[str, int] = {}  # genre -> row index (0-based in records)
    for i, r in enumerate(records):
        if r["年月"] == year_month:
            existing[r["ジャンル名"]] = i

    for genre, adj in adjustments.items():
        if genre == "その他" or adj == 0:
            continue
        if genre in existing:
            ws.update_cell(existing[genre] + 2, 3, adj)
        else:
            ws.append_row([year_month, genre, adj], value_input_option="USER_ENTERED")

    # 調整が0に戻った項目は削除（下から削除してインデックスずれ防止）
    for genre, row_idx in sorted(existing.items(), key=lambda x: -x[1]):
        if adjustments.get(genre, 0) == 0:
            ws.delete_rows(row_idx + 2)

    get_budget_adjustments.clear()
