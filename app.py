import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px

# 設定網頁標題
st.set_page_config(page_title="台股股利小幫手", page_icon="📈", layout="wide")

@st.cache_data(ttl=3600)
def load_dividend_data(stock_id):
    try:
        dl = DataLoader()
        df = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2010-01-01')
        
        if df is None or df.empty:
            return None
        
        # 定義我們需要的欄位與對應名稱
        rename_map = {
            'year': '年度',
            'CashEarningsDistribution': '現金股利',
            'StockEarningsDistribution': '股票股利',
            'ExDividendExRightsDate': '除權息日'
        }
        
        # 只取現有的欄位
        existing_cols = [c for c in rename_map.keys() if c in df.columns]
        df = df[existing_cols].rename(columns=rename_map)
        
        # 補齊數值欄位並填入 0
        for col in ['現金股利', '股票股利']:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 按年度加總處理 (台積電季配息會自動合併)
        report = df.groupby('年度').agg({
            '現金股利': 'sum',
            '股票股利': 'sum'
        }).sort_index(ascending=False).reset_index()
        
        report['總計'] = report['現金股利'] + report['股票股利']
        return report
    except Exception as e:
        st.error(f"資料處理發生錯誤: {e}")
        return None

# --- 網頁介面 ---
st.title("💰 台股歷年股利查詢系統")
stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    with st.spinner('讀取數據中...'):
        data = load_dividend_data(stock_id)
        
        if data is not None:
            # 數據卡片顯示
            c1, c2, c3 = st.columns(3)
            latest = data.iloc[0]
            c1.metric(f"{latest['年度']} 現金股利", f"{latest['現金股利']} 元")
            c2.metric(f"{latest['年度']} 股票股利", f"{latest['股票股利']} 元")
            c3.metric("資料年份總數", f"{len(data)} 年")

            # 趨勢圖
            st.subheader("📈 歷年配息趨勢")
            fig = px.bar(data, x='年度', y=['現金股利', '股票股利'], barmode='stack')
            st.plotly_chart(fig, use_container_width=True)

            # 資料表格
            st.subheader("📋 詳細數據表")
            st.dataframe(data, use_container_width=True)
        else:
            st.warning("查無資料，請確認代號是否正確。")
