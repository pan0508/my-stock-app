@st.cache_data(ttl=3600)
def load_dividend_data(stock_id):
    dl = DataLoader()
    df = dl.taiwan_stock_dividend(stock_id=stock_id, start_date='2010-01-01')
    
    if df.empty:
        return None
    
    # --- 這裡進行安全修正 ---
    # 先把我們需要的欄位對應表寫好
    rename_map = {
        'year': '年度',
        'CashEarningsDistribution': '現金股利',
        'StockEarningsDistribution': '股票股利',
        'ExDividendExRightsDate': '除權息日'
    }
    
    # 只保留存在的欄位，避免 KeyError
    existing_cols = [c for c in rename_map.keys() if c in df.columns]
    df = df[existing_cols].rename(columns=rename_map)
    
    # 確保所有數值欄位都存在，如果沒有就補 0
    for col in ['現金股利', '股票股利']:
        if col not in df.columns:
            df[col] = 0
            
    # 按年度加總
    report = df.groupby('年度').agg({
        '現金股利': 'sum',
        '股票股利': 'sum',
        '除權息日': 'max' if '除權息日' in df.columns else 'first'
    }).sort_index(ascending=False).reset_index()
    
    report['總計'] = report['現金股利'] + report['股票股利']
    return report
