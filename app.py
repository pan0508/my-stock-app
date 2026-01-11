import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px

st.set_page_config(page_title="台股股利小幫手", page_icon="📈", layout="wide")

@st.cache_data(ttl=3600) # 快取 1 小時，避免頻繁請求被 API 封鎖
def load_dividend_data(stock_id):
    dl = DataLoader()
    df = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2010-01-01')
    if df.empty: return None
    df = df[['year', 'CashEarningsDistribution', 'StockEarningsDistribution', 'ExDividendExRightsDate']]
    df.columns = ['年度', '現金股利', '股票股利', '除權息日']
    report = df.groupby('年度').agg({'現金股利':'sum', '股票股利':'sum', '除權息日':'max'}).sort_index(ascending=False).reset_index()
    report['總計'] = report['現金股利'] + report['股票股利']
    return report

st.title("💰 台股歷年股利查詢系統")
stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    data = load_dividend_data(stock_id)
    if data is not None:
        c1, c2, c3 = st.columns(3)
        latest = data.iloc[0]
        c1.metric(f"{latest['年度']} 現金股利", f"{latest['現金股利']} 元")
        c2.metric(f"{latest['年度']} 股票股利", f"{latest['股票股利']} 元")
        c3.metric("累計發放次數", f"{len(data)} 年")

        st.plotly_chart(px.bar(data, x='年度', y=['現金股利', '股票股利'], title="歷年配息趨勢"), use_container_width=True)
        st.dataframe(data, use_container_width=True)
    else:
        st.error("查無資料，請檢查代號。")
