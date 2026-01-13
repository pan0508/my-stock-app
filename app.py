import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px
import re

# 設定網頁標題與寬度
st.set_page_config(page_title="台股股利 & 殖利率分析", page_icon="💰", layout="wide")

@st.cache_data(ttl=3600)
def get_stock_data(stock_id):
    try:
        dl = DataLoader()
        # 1. 抓取股利資料
        df_div = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2000-01-01')
        # 2. 抓取價格資料 (計算殖利率用)
        df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date='2000-01-01')
        
        if df_div is None or df_div.empty:
            return None, None

        # --- 年度文字清理與西元轉換 ---
        def clean_year(y):
            nums = re.findall(r'\d+', str(y))
            if not nums: return 0
            y_int = int(nums[0])
            return y_int + 1911 if y_int < 200 else y_int

        df_div['year'] = df_div['year'].apply(clean_year)
        
        # --- 欄位名稱自動偵測與重新命名 (容錯機制) ---
        name_map = {
            'CashEarningsDistribution': '現金股利',
            'StockEarningsDistribution': '股票股利',
            'ExDividendExRightsDate': '除權息日'
        }
        # 只有當欄位真的存在時才進行改名
        to_rename = {k: v for k, v in name_map.items() if k in df_div.columns}
        df_div = df_div.rename(columns=to_rename)
        
        # 確保必要的數值欄位存在，若不存在則補 0
        for col in ['現金股利', '股票股利']:
            if col not in df_div.columns:
                df_div[col] = 0.0
            else:
                df_div[col] = pd.to_numeric(df_div[col], errors='coerce').fillna(0.0)

        # --- 計算殖利率 (年度平均收盤價) ---
        avg_price_dict = {}
        if df_price is not None and not df_price.empty:
            df_price['date'] = pd.to_datetime(df_price['date'])
            df_price['year'] = df_price['date'].dt.year
            avg_price_dict = df_price.groupby('year')['close'].mean().to_dict()

        # --- 資料匯整 ---
        agg_dict = {'現金股利': 'sum', '股票股利': 'sum'}
        if '除權息日' in df_div.columns:
            agg_dict['除權息日'] = 'max'

        report = df_div.groupby('year').agg(agg_dict).sort_index(ascending=False).reset_index()
        report = report[report['year'] > 1900].rename(columns={'year': '年度'})

        # 計算殖利率 (%)
        report['殖利率(%)'] = report.apply(
            lambda x: round((x['現金股利'] / avg_price_dict.get(x['年度'], 1)) * 100, 2) 
            if avg_price_dict.get(x['年度']) else 0.0, axis=1
        )
        report['總計'] = report['現金股利'] + report['股票股利']
        
        return report, avg_price_dict
    except Exception as e:
        st.error(f"分析失敗: {e}")
        return None, None

# --- 網頁介面 ---
st.title("💰 台股歷年股利 & 殖利率分析系統")
st.markdown("🔍 自動轉換 **西元年度** | 以年度平均股價計算 **現金殖利率**")

stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    with st.spinner('連線資料庫並計算數據中...'):
        data, _ = get_stock_data(stock_id)
        
        if data is not None and not data.empty:
            latest = data.iloc[0]
            
            # 數據看板
            c1, c2, c3, c4 = st.columns(4)
            y_label = str(int(latest['年度']))
            c1.metric(f"{y_label} 現金股利", f"{round(latest['現金股利'], 2)} 元")
            c2.metric("歷年平均殖利率", f"{round(data['殖利率(%)'].mean(), 2)} %")
            
            # 安全顯示除權息日
            ex_date = latest['除權息日'] if '除權息日' in latest else "暫無資料"
            c3.metric("最新除息參考日", str(ex_date))
            c4.metric("歷史收錄年份", f"{len(data)} 年")

            # 圖表：現金股利趨勢
            st.subheader("📈 歷年現金股利發放趨勢")
            fig = px.bar(data, x='年度', y='現金股利', text_auto='.2f', color_discrete_sequence=['#00CC96'])
            fig.update_xaxes(type='category')
            st.plotly_chart(fig, use_container_width=True)
            
            # 圖表：殖利率趨勢
            st.subheader("📊 歷年現金殖利率趨勢 (%)")
            fig2 = px.line(data, x='年度', y='殖利率(%)', markers=True, color_discrete_sequence=['#FF4B4B'])
            fig2.update_xaxes(type='category')
            st.plotly_chart(fig2, use_container_width=True)

            # 數據表格
            st.subheader("📋 完整數據清單")
            st.dataframe(data.style.format({
                '年度': '{:.0f}', '現金股利': '{:.2f}', '股票股利': '{:.2f}',
                '總計': '{:.2f}', '殖利率(%)': '{:.2f}%'
            }), use_container_width=True)
        else:
            st.warning("查無資料，請確認代號是否正確。")

st.divider()
st.caption("資料來源：FinMind API | 計算基準：該年度每日收盤價之平均值。")
