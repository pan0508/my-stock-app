import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="台股全方位分析工具", page_icon="📈", layout="wide")

@st.cache_data(ttl=600) # 股價縮短快取時間至 10 分鐘
def get_comprehensive_data(stock_ids):
    all_dividend_data = []
    current_prices = {}
    dl = DataLoader()
    
    id_list = [s.strip() for s in stock_ids.split(',')]
    
    for sid in id_list:
        try:
            # 1. 抓取股利資料
            df_div = dl.taiwan_stock_dividend(stock_id=sid, start_date='2010-01-01')
            # 2. 抓取價格資料 (歷史 + 最新)
            df_price = dl.taiwan_stock_daily(stock_id=sid, start_date='2010-01-01')
            
            if df_div is None or df_div.empty or df_price is None or df_price.empty:
                continue

            # 取得最新一筆成交價
            latest_price = df_price.iloc[-1]['close']
            current_prices[sid] = latest_price

            # 年度清理邏輯
            def clean_year(y):
                nums = re.findall(r'\d+', str(y))
                if not nums: return 0
                y_int = int(nums[0])
                return y_int + 1911 if y_int < 200 else y_int

            df_div['year'] = df_div['year'].apply(clean_year)
            df_div['現金股利'] = pd.to_numeric(df_div['CashEarningsDistribution'], errors='coerce').fillna(0.0)
            
            # 計算歷史年度均價
            df_price['date'] = pd.to_datetime(df_price['date'])
            df_price['year'] = df_price['date'].dt.year
            avg_price_dict = df_price.groupby('year')['close'].mean().to_dict()

            # 彙整年度數據
            report = df_div.groupby('year').agg({'現金股利': 'sum'}).sort_index().reset_index()
            report['股票代號'] = sid
            report['殖利率(%)'] = report.apply(
                lambda x: round((x['現金股利'] / avg_price_dict.get(x['year'], 1)) * 100, 2) 
                if avg_price_dict.get(x['year']) else 0.0, axis=1
            )
            all_dividend_data.append(report)
        except Exception as e:
            st.error(f"代號 {sid} 資料抓取失敗: {e}")
            continue
            
    return (pd.concat(all_dividend_data) if all_dividend_data else None), current_prices

# --- 網頁介面 ---
st.title("🚀 台股多股對比 & 即時監控")
st.markdown("輸入多個代號（如 `2330, 2454`），系統將自動比對 **歷年殖利率** 與 **最新股價**。")

input_ids = st.text_input("輸入股票代號 (用英文逗號隔開)", value="2330, 2881")

if input_ids:
    with st.spinner('正在同步最新市場價格與歷年配息...'):
        combined_data, prices = get_comprehensive_data(input_ids)
        
        if combined_data is not None:
            # 第一部分：即時股價看板
            st.subheader("🔔 即時行情快報")
            cols = st.columns(len(prices))
            for i, (sid, price) in enumerate(prices.items()):
                cols[i].metric(label=f"{sid} 最新股價", value=f"{price} 元")

            # 第二部分：殖利率對比圖
            st.subheader("📈 歷年現金殖利率對比 (%)")
            fig_yield = px.line(
                combined_data, x='year', y='殖利率(%)', color='股票代號',
                markers=True, hover_data={'year': True, '殖利率(%)': ':.2f'}
            )
            fig_yield.update_xaxes(type='category', title="年度")
            st.plotly_chart(fig_yield, use_container_width=True)

            # 第三部分：股利組成圖
            st.subheader("💰 歷年現金股利發放金額")
            fig_div = px.bar(
                combined_data, x='year', y='現金股利', color='股票代號',
                barmode='group', text_auto='.1f'
            )
            fig_div.update_xaxes(type='category', title="年度")
            st.plotly_chart(fig_div, use_container_width=True)

            # 第四部分：對比數據表
            with st.expander("查看詳細數據清單"):
                pivot_df = combined_data.pivot(index='year', columns='股票代號', values='殖利率(%)')
                st.dataframe(pivot_df.sort_index(ascending=False).style.highlight_max(axis=1, color='#e6f3ff'), use_container_width=True)
        else:
            st.warning("查無資料，請確認代號輸入是否正確。")

st.divider()
st.caption(f"最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 資料來源：FinMind API")
