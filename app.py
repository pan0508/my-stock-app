import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.express as px
import re

st.set_page_config(page_title="台股股利全方位分析", page_icon="💰", layout="wide")

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

        # --- 處理年份與文字清理 (解決 '93年' 報錯問題) ---
        def clean_year(y):
            # 使用正規表達式只留下數字
            nums = re.findall(r'\d+', str(y))
            if not nums: return 0
            y_int = int(nums[0])
            # 自動判斷民國/西元
            return y_int + 1911 if y_int < 200 else y_int

        df_div['year'] = df_div['year'].apply(clean_year)
        df_div = df_div.rename(columns={
            'CashEarningsDistribution': '現金股利',
            'StockEarningsDistribution': '股票股利',
            'ExDividendExRightsDate': '除權息日'
        })
        
        # 轉為純數值，避免運算錯誤
        for col in ['現金股利', '股票股利']:
            df_div[col] = pd.to_numeric(df_div[col], errors='coerce').fillna(0.0)

        # --- 計算殖利率 (使用該年度平均收盤價) ---
        df_price['date'] = pd.to_datetime(df_price['date'])
        df_price['year'] = df_price['date'].dt.year
        avg_price = df_price.groupby('year')['close'].mean().to_dict()

        # 按年度加總 (因應季配息或半年配)
        report = df_div.groupby('year').agg({
            '現金股利': 'sum',
            '股票股利': 'sum',
            '除權息日': 'max'
        }).sort_index(ascending=False).reset_index()

        # 計算殖利率公式：(現金股利 / 年度均價) * 100
        report['殖利率(%)'] = report.apply(lambda x: round((x['現金股利'] / avg_price.get(x['year'], 1)) * 100, 2) if avg_price.get(x['year']) else 0, axis=1)
        report['總計'] = report['現金股利'] + report['股票股利']
        
        report = report.rename(columns={'year': '年度'})
        # 移除無效資料
        report = report[report['年度'] > 1900]
        
        return report, avg_price
    except Exception as e:
        st.error(f"分析失敗: {e}")
        return None, None

# --- 網頁介面 ---
st.title("💰 台股歷年股利 & 殖利率分析系統")
st.markdown("🔍 已解決年份文字報錯，自動計算 **西元年度** 與 **現金殖利率**。")

stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    with st.spinner('正在從資料庫運算歷年數據...'):
        data, avg_prices = get_stock_data(stock_id)
        
        if data is not None and not data.empty:
            latest = data.iloc[0]
            
            # 頂部儀表板
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"{int(latest['年度'])} 現金股利", f"{round(latest['現金股利'], 2)} 元")
            c2.metric("歷年平均殖利率", f"{round(data['殖利率(%)'].mean(), 2)} %")
            c3.metric("填息參考(最新除息日)", str(latest['除權息日']))
            c4.metric("總計收錄年分", f"{len(data)} 年")

            # 視覺化圖表
            st.subheader("📈 歷年現金股利趨勢")
            fig = px.bar(data, x='年度', y='現金股利', text_auto='.2f', color_discrete_sequence=['#00CC96'])
            fig.update_xaxes(type='category')
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📊 歷年現金殖利率趨勢 (%)")
            fig2 = px.line(data, x='年度', y='殖利率(%)', markers=True)
            fig2.update_xaxes(type='category')
            st.plotly_chart(fig2, use_container_width=True)

            # 詳細報表
            st.subheader("📋 完整數據清單")
            st.dataframe(data.style.format({
                '年度': '{:.0f}',
                '現金股利': '{:.2f}',
                '股票股利': '{:.2f}',
                '總計': '{:.2f}',
                '殖利率(%)': '{:.2f}%'
            }), use_container_width=True)
            
            st.info("💡 填息提示：填息天數取決於市場收盤價。若最新除權息日後股價回到除息前價格即為填息。")
        else:
            st.warning("查無資料。請確認該代號是否正確或是否有配息紀錄。")

st.divider()
st.caption("資料來源：FinMind API | 計算基準：該年度每日收盤價之平均值。")
