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
        # 抓取資料：從 2000 年開始抓，確保資料量充足
        df = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2000-01-01')
        
        if df is None or df.empty:
            return None
        
        # 欄位對應
        rename_map = {
            'year': '年度', 
            'CashEarningsDistribution': '現金股利', 
            'StockEarningsDistribution': '股票股利'
        }
        existing_cols = [c for c in rename_map.keys() if c in df.columns]
        df = df[existing_cols].rename(columns=rename_map)
        
        # --- 年度修正邏輯：自動判定民國或西元 ---
        def fix_year(y):
            try:
                y_val = int(float(y))
                # 如果年度小於 200 (例如 99, 112)，自動加 1911 轉為西元
                if y_val < 200:
                    return y_val + 1911
                return y_val
            except:
                return 0

        df['年度'] = df['年度'].apply(fix_year)
        
        # 數值清理：確保是浮點數且補 0
        for col in ['現金股利', '股票股利']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # 按年度加總處理 (處理季配息情況)
        report = df.groupby('年度').agg({
            '現金股利': 'sum', 
            '股票股利': 'sum'
        }).sort_index(ascending=False).reset_index()
        
        # 排除無效年度資料
        report = report[report['年度'] > 1900]
        report['總計'] = report['現金股利'] + report['股票股利']
        return report
    except Exception as e:
        st.error(f"資料處理發生意外: {e}")
        return None

# --- 網頁介面佈局 ---
st.title("💰 台股歷年股利查詢系統")
st.markdown("輸入台股代號後按 Enter，系統會自動轉換為 **西元年份** 顯示。")

stock_id = st.text_input("輸入台股代號 (如: 2330, 2454, 2881)", value="2330")

if stock_id:
    with st.spinner('連線 FinMind 資料庫中...'):
        data = load_dividend_data(stock_id)
        
        if data is not None and not data.empty:
            latest = data.iloc[0]
            
            # 頂部三大指標卡片
            c1, c2, c3 = st.columns(3)
            # 強制將年度轉為字串，避免 Streamlit 顯示成 "2,024"
            y_label = str(int(latest['年度']))
            c1.metric(f"{y_label}年 現金股利", f"{round(float(latest['現金股利']), 2)} 元")
            c2.metric(f"{y_label}年 股票股利", f"{round(float(latest['股票股利']), 2)} 元")
            c3.metric("歷史收錄年數", f"{len(data)} 年")

            # 視覺化圖表
            st.subheader("📈 歷年配息趨勢 (西元)")
            fig = px.bar(data, x='年度', y=['現金股利', '股票股利'], 
                         labels={'value':'金額 (元)', 'variable':'種類'},
                         barmode='stack', 
                         color_discrete_map={'現金股利': '#00CC96', '股票股利': '#636EFA'})
            # 設定 X 軸格式：類別型態可確保 2024, 2023 一一對應
            fig.update_xaxes(type='category', tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

            # 詳細表格
            st.subheader("📋 數據詳情")
            st.dataframe(data.style.format({
                '年度': '{:.0f}',
                '現金股利': '{:.2f}',
                '股票股利': '{:.2f}',
                '總計': '{:.2f}'
            }), use_container_width=True)
            
            # 下載功能
            csv = data.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV格式)", data=csv, file_name=f"{stock_id}_dividend_west.csv")
        else:
            st.warning("查無此股票資料。請確認：1. 代號正確 2. 該股是否有配發股利 3. 稍後再試。")

st.divider()
st.caption("資料來源：FinMind API | 此網頁僅供程式學習交流使用。")
