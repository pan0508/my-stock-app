import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px
import re

st.set_page_config(page_title="台股多股利對比系統", page_icon="📊", layout="wide")

@st.cache_data(ttl=3600)
def get_multi_stock_data(stock_ids):
    all_data = []
    dl = DataLoader()
    
    # 將輸入的字串轉為清單，例如 "2330, 2454" -> ["2330", "2454"]
    id_list = [s.strip() for s in stock_ids.split(',')]
    
    for sid in id_list:
        try:
            # 抓取股利與價格
            df_div = dl.taiwan_stock_dividend(stock_id=sid, start_date='2010-01-01')
            df_price = dl.taiwan_stock_daily(stock_id=sid, start_date='2010-01-01')
            
            if df_div is None or df_div.empty:
                continue

            # 年度清理
            def clean_year(y):
                nums = re.findall(r'\d+', str(y))
                if not nums: return 0
                y_int = int(nums[0])
                return y_int + 1911 if y_int < 200 else y_int

            df_div['year'] = df_div['year'].apply(clean_year)
            df_div['現金股利'] = pd.to_numeric(df_div['CashEarningsDistribution'], errors='coerce').fillna(0.0)
            
            # 計算均價與殖利率
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
            all_data.append(report)
        except:
            continue
            
    return pd.concat(all_data) if all_data else None

# --- 網頁介面 ---
st.title("📊 台股歷年殖利率多股對比")
st.markdown("請輸入多個股票代號，並用 **英文逗號 (,)** 隔開。例如：`2330, 2454, 2881`")

input_ids = st.text_input("輸入股票代號對比", value="2330, 2454")

if input_ids:
    with st.spinner('正在抓取多檔股票數據...'):
        combined_data = get_multi_stock_data(input_ids)
        
        if combined_data is not None:
            # 1. 殖利率對比折線圖
            st.subheader("📈 歷年現金殖利率對比 (%)")
            fig_yield = px.line(
                combined_data, x='year', y='殖利率(%)', color='股票代號',
                markers=True, title="各股歷年平均殖利率走勢"
            )
            fig_yield.update_xaxes(type='category', title="年度")
            st.plotly_chart(fig_yield, use_container_width=True)

            # 2. 現金股利對比柱狀圖
            st.subheader("💰 歷年現金股利發放對比")
            fig_div = px.bar(
                combined_data, x='year', y='現金股利', color='股票代號',
                barmode='group', title="各股歷年配息金額對比"
            )
            fig_div.update_xaxes(type='category', title="年度")
            st.plotly_chart(fig_div, use_container_width=True)

            # 3. 數據總表
            st.subheader("📋 對比數據詳情")
            pivot_df = combined_data.pivot(index='year', columns='股票代號', values='殖利率(%)')
            st.write("各年度殖利率 (%) 一覽表：")
            st.dataframe(pivot_df.sort_index(ascending=False), use_container_width=True)
            
        else:
            st.warning("查無資料，請確認輸入格式是否正確。")

st.divider()
st.caption("註：殖利率以當年度平均收盤價為分母計算。資料來源：FinMind API。")
