import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px

st.set_page_config(page_title="台股股利全方位分析", page_icon="💰", layout="wide")

@st.cache_data(ttl=3600)
def get_stock_data(stock_id):
    try:
        dl = DataLoader()
        # 1. 抓取股利資料
        df_div = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2005-01-01')
        # 2. 抓取價格資料 (計算殖利率用)
        df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date='2005-01-01')
        
        if df_div is None or df_div.empty:
            return None, None

        # --- 處理年份與股利 ---
        df_div['year'] = df_div['year'].apply(lambda x: int(x)+1911 if int(x)<200 else int(x))
        df_div = df_div.rename(columns={
            'CashEarningsDistribution': '現金股利',
            'StockEarningsDistribution': '股票股利',
            'ExDividendExRightsDate': '除權息日'
        })
        
        # 轉數值
        for col in ['現金股利', '股票股利']:
            df_div[col] = pd.to_numeric(df_div[col], errors='coerce').fillna(0.0)

        # --- 計算殖利率 (使用該年度平均股價) ---
        df_price['date'] = pd.to_datetime(df_price['date'])
        df_price['year'] = df_price['date'].dt.year
        avg_price = df_price.groupby('year')['close'].mean().to_dict()

        # 按年度加總
        report = df_div.groupby('year').agg({
            '現金股利': 'sum',
            '股票股利': 'sum',
            '除權息日': 'max'
        }).sort_index(ascending=False).reset_index()

        report['殖利率(%)'] = report.apply(lambda x: round((x['現金股利'] / avg_price.get(x['year'], 1)) * 100, 2) if avg_price.get(x['year']) else 0, axis=1)
        report['總計'] = report['現金股利'] + report['股票股利']
        
        # 填息天數模擬 (API 限制，此處標註除權息日供參考)
        report = report.rename(columns={'year': '年度'})
        return report, avg_price
    except Exception as e:
        st.error(f"分析失敗: {e}")
        return None, None

st.title("💰 台股歷年股利 & 殖利率分析系統")
st.markdown("已自動轉換為 **西元年**。殖利率以「年度平均股價」為基準計算。")

stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    with st.spinner('正在分析大數據...'):
        data, avg_prices = get_stock_data(stock_id)
        
        if data is not None and not data.empty:
            latest = data.iloc[0]
            
            # 頂部指標
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"{int(latest['年度'])} 現金股利", f"{round(latest['現金股利'], 2)} 元")
            c2.metric("歷年平均殖利率", f"{round(data['殖利率(%)'].mean(), 2)} %")
            c3.metric("填息參考日", str(latest['除權息日']))
            c4.metric("歷史總配息次數", f"{len(data)} 次")

            # 圖表：股利 + 殖利率
            st.subheader("📈 歷年配息與殖利率趨勢")
            fig = px.bar(data, x='年度', y='現金股利', text_auto='.2f', title="歷年現金股利 (元)")
            fig.update_xaxes(type='category')
            st.plotly_chart(fig, use_container_width=True)
            
            fig2 = px.line(data, x='年度', y='殖利率(%)', markers=True, title="歷年現金殖利率 (%)")
            fig2.update_xaxes(type='category')
            st.plotly_chart(fig2, use_container_width=True)

            # 表格
            st.subheader("📋 詳細數據報表")
            st.dataframe(data.style.format({
                '現金股利': '{:.2f}', '股票股利': '{:.2f}', 
                '總計': '{:.2f}', '殖利率(%)': '{:.2f}%'
            }), use_container_width=True)
            
            st.info("註：填息天數受限於歷史資料完整度，目前顯示最新除權息日，若收盤價大於除息前一日股價即視為填息。")
        else:
            st.warning("查無資料。請確保該股票有配息紀錄。")

st.divider()
st.caption("資料來源：FinMind API | 此計算結果僅供參考。")
