import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px
import re
from datetime import datetime

# 網頁基礎設定
st.set_page_config(page_title="台股多股利投資分析", page_icon="📈", layout="wide")

@st.cache_data(ttl=300) 
def get_investment_data(stock_ids):
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

            # 1. 取得最新成交價
            latest_price = df_price.iloc[-1]['close']
            prices[sid] = {'price': latest_price}

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

# --- 介面設計 ---
st.title("📈 台股多股利投資分析系統")
st.caption(f"數據更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

input_ids = st.text_input("輸入對比代號 (例: 2330, 2881)", value="2330, 2881")

if input_ids:
    with st.spinner('正在同步市場數據...'):
        data, current_info = get_investment_data(input_ids)
        
        if data is not None:
            # 第一區塊：市場行情與預估
            st.subheader("🎯 當前行情與預估殖利率")
            metrics = st.columns(len(current_info))
            for i, (sid, info) in enumerate(current_info.items()):
                # 取出最後一年的配息金額計算預估殖利率
                last_div = data[data['股票代號'] == sid].iloc[-1]['現金股利']
                est_yield = round((last_div / info['price']) * 100, 2)
                
                metrics[i].metric(
                    label=f"{sid} 預估殖利率",
                    value=f"{est_yield} %",
                    delta=f"股價: {info['price']} 元",
                    delta_color="off"
                )

            st.divider()

            # 第二區塊：視覺化分析
            st.subheader("📊 歷年數據對比")
            tab1, tab2 = st.tabs(["殖利率走勢", "配息金額"])
            
            with tab1:
                fig1 = px.line(data, x='year', y='歷史殖利率(%)', color='股票代號', markers=True,
                               title="歷年平均殖利率走勢 (以年度均價計算)")
                fig1.update_xaxes(type='category', title="年度")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                fig2 = px.bar(data, x='year', y='現金股利', color='股票代號', barmode='group', text_auto='.1f',
                              title="歷年現金股利發放對比")
                fig2.update_xaxes(type='category', title="年度")
                st.plotly_chart(fig2, use_container_width=True)

            # 第三區塊：原始數據
            with st.expander("📂 查看詳細歷史數據報表"):
                # 重新整理表格顯示
                df_display = data.sort_values(['股票代號', 'year'], ascending=[True, False])
                st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("請確認代號輸入是否正確，或該股票是否有配息紀錄。")

st.divider()
st.info("💡 說明：『預估殖利率』係以最近一年度發放之現金股利總額除以最新收盤價計算，僅供投資參考。")
