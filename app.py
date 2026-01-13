import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="台股究極分析儀", page_icon="💎", layout="wide")

@st.cache_data(ttl=300) # 股價快取縮短至 5 分鐘
def get_ultimate_data(stock_ids):
    all_divs = []
    prices = {}
    dl = DataLoader()
    id_list = [s.strip() for s in stock_ids.split(',')]
    
    for sid in id_list:
        try:
            # 抓取股利與價格
            df_div = dl.taiwan_stock_dividend(stock_id=sid, start_date='2010-01-01')
            df_price = dl.taiwan_stock_daily(stock_id=sid, start_date='2010-01-01')
            
            if df_div is None or df_div.empty or df_price is None: continue

            # 1. 取得最新成交價與日期
            latest_price = df_price.iloc[-1]['close']
            latest_date = df_price.iloc[-1]['date']
            prices[sid] = {'price': latest_price, 'date': latest_date}

            # 2. 年度清理與西元轉換
            def clean_year(y):
                nums = re.findall(r'\d+', str(y))
                return (int(nums[0]) + 1911 if int(nums[0]) < 200 else int(nums[0])) if nums else 0

            df_div['year'] = df_div['year'].apply(clean_year)
            df_div['現金股利'] = pd.to_numeric(df_div['CashEarningsDistribution'], errors='coerce').fillna(0.0)
            
            # 3. 年度均價計算
            df_price['date'] = pd.to_datetime(df_price['date'])
            df_price['year'] = df_price['date'].dt.year
            avg_price_dict = df_price.groupby('year')['close'].mean().to_dict()

            # 4. 數據彙整
            report = df_div.groupby('year').agg({'現金股利': 'sum'}).sort_index().reset_index()
            report['股票代號'] = sid
            report['歷史殖利率(%)'] = report.apply(
                lambda x: round((x['現金股利'] / avg_price_dict.get(x['year'], 1)) * 100, 2) 
                if avg_price_dict.get(x['year']) else 0.0, axis=1
            )
            all_divs.append(report)
        except: continue
            
    return (pd.concat(all_divs) if all_divs else None), prices

# --- 介面 ---
st.title("💎 台股究極投資分析儀")
st.markdown("當前時間: " + datetime.now().strftime('%Y-%m-%d %H:%M'))

input_ids = st.text_input("輸入對比代號 (例: 2330, 2881, 2454)", value="2330, 2881")

if input_ids:
    with st.spinner('正在計算預估值...'):
        data, current_info = get_ultimate_data(input_ids)
        
        if data is not None:
            # 頂部：預估殖利率看板
            st.subheader("🎯 預估即時殖利率 (以最新股利 / 當前股價計算)")
            metrics = st.columns(len(current_info))
            for i, (sid, info) in enumerate(current_info.items()):
                # 抓取該股最後一次的總股利
                last_div = data[data['股票代號'] == sid].iloc[-1]['現金股利']
                est_yield = round((last_div / info['price']) * 100, 2)
                
                metrics[i].metric(
                    label=f"{sid} 預估殖利率",
                    value=f"{est_yield} %",
                    delta=f"股價: {info['price']} 元",
                    delta_color="off"
                )

            # 圖表區
            tab1, tab2 = st.tabs(["📊 殖利率對比", "💰 配息成長性"])
            with tab1:
                fig1 = px.line(data, x='year', y='歷史殖利率(%)', color='股票代號', markers=True)
                fig1.update_xaxes(type='category', title="年度")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                fig2 = px.bar(data, x='year', y='現金股利', color='股票代號', barmode='group', text_auto='.1f')
                fig2.update_xaxes(type='category', title="年度")
                st.plotly_chart(fig2, use_container_width=True)

            # 詳細表格
            with st.expander("📂 查看各股詳細配息歷史"):
                st.dataframe(data.sort_values(['股票代號', 'year'], ascending=[True, False]), use_container_width=True)
        else:
            st.warning("請確認代號輸入是否正確。")

st.divider()
st.caption("提示：預估殖利率採用『最近一次發放的總股利』與『今日收盤價』計算，僅供參考。")
