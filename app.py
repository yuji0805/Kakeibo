import streamlit as st

VERSION = "v1.0"

st.set_page_config(page_title=f"家計簿 {VERSION}", page_icon="💰", layout="centered")

# ── Google Sheets 未設定時のガイド ──
if "gcp_service_account" not in st.secrets or "spreadsheet_id" not in st.secrets:
    st.error("⚠️ Google Sheets の設定がされていません。")
    st.markdown(
        """
### セットアップ手順

1. **Google Cloud Console** でプロジェクトを作成し、**Google Sheets API** を有効化
2. **サービスアカウント**を作成し、JSON キーをダウンロード
3. **Google スプレッドシートを新規作成**し、サービスアカウントのメールアドレスに「編集者」権限で共有
4. `.streamlit/secrets.toml` を作成し以下を記入：

```toml
spreadsheet_id = "スプレッドシートのID"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = \"\"\"
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
\"\"\"
client_email = "xxx@xxx.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```
    """
    )
    st.stop()

# ── 初期化 ──
from sheets import init_spreadsheet  # noqa: E402

if "initialized" not in st.session_state:
    with st.spinner("初期化中..."):
        init_spreadsheet()
    st.session_state["initialized"] = True

# ── ナビゲーション ──
st.sidebar.markdown(f"<small style='color:#666;'>{VERSION}</small>", unsafe_allow_html=True)

pg = st.navigation(
    [
        st.Page("pages/dashboard.py", title="ダッシュボード", icon="📊", default=True),
        st.Page("pages/expense_input.py", title="支出入力", icon="💰"),
        st.Page("pages/fixed_costs.py", title="固定費設定", icon="🔧"),
        st.Page("pages/income_budget.py", title="月収・予算設定", icon="💵"),
        st.Page("pages/history.py", title="履歴", icon="📈"),
    ]
)
pg.run()
