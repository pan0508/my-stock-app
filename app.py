import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="台股股利小幫手", page_icon="📈", layout="wide")

@st.cache_data(ttl=3600)
def load_dividend_data(stock_id):
    try:
        dl = DataLoader()
        # 抓取資料
        df = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2010-01-01')
        
        if df is None or df.empty:
            return None
        
        # 欄位對應與清洗
        rename_map = {
            'year': '年度',
            'CashEarningsDistribution': '現金股利',
            'StockEarningsDistribution': '股票股利'
        }
        
        existing_cols = [c for c in rename_map.keys() if c in df.columns]
        df = df[existing_cols].rename(columns=rename_map)
        
        # 轉換數值並補 0
        for col in ['現金股利', '股票股利']:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # 按年度合併加總 (例如處理季配息)
        report = df.groupby('年度').agg({
            '現金股利': 'sum',
            '股票股利': 'sum'
        }).sort_index(ascending=False).reset_index()
        
        report['總計'] = report['現金股利'] + report['股票股利']
        return report
    except Exception as e:
        st.error(f"資料讀取錯誤: {e}")
        return None

# --- 網頁介面 ---
st.title("💰 台股歷年股利查詢系統")
st.markdown("輸入股票代號後按下 Enter，即可查看歷年配息數據。")

stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    with st.spinner('數據計算中...'):
        data = load_dividend_data(stock_id)
        
        if data is not None:
            # 取得最新一年的數據
            latest = data.iloc[0]
            
            # 頂部數據卡片 (加上 round 處理小數點)
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{int(latest['年度'])}年度 現金股利", f"{round(latest['現金股利'], 2)} 元")
            c2.metric(f"{int(latest['年度'])}年度 股票股利", f"{round(latest['股票股利'], 2)} 元")
            c3.metric("歷史收錄年數", f"{len(data)} 年")

            # 趨勢圖表
            st.subheader("📈 歷年配息組成趨勢")
            fig = px.bar(data, x='年度', y=['現金股利', '股票股利'], 
                         labels={'value':'金額', 'variable':'種類'},
                         barmode='stack', 
                         color_discrete_map={'現金股利': '#00CC96', '股票股利': '#636EFA'})
            st.plotly_chart(fig, use_container_width=True)

            # 詳細數據表格 (美化顯示小數點兩位)
            st.subheader("📋 詳細數據報表")
            st.dataframe(data.style.format({
                '年度': '{:.0f}',
                '現金股利': '{:.2f}',
                '股票股利': '{:.2f}',
                '總計': '{:.2f}'
            }), use_container_width=True)
            
            # 下載按鈕
            csv = data.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", data=csv, file_name=f"{stock_id}_dividends.csv")
            
        else:
            st.warning("查無此股票資料，請檢查代號是否正確。")

st.divider()
st.caption("資料來源：FinMind API | 此工具僅供參考，實際數據以公開資訊觀測站為準。")
