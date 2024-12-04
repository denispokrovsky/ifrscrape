import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from io import BytesIO
import re


# Add page configuration with wide layout and title
st.set_page_config(
    page_title="МСФО Scraper",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS to improve the look
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #1c83e1;
    }
    </style>
""", unsafe_allow_html=True)

# Add title and description
st.title("МСФО Data Scraper 📊")
st.markdown("""
This app collects financial data for Russian-listed companies including:
- Company Name and Sector
- EBITDA and Net Profit
- Net Debt and Assets
- ROE, ROA, and Net Margin
""")

@st.cache_data(ttl=3600)  # Cache the results for 1 hour
def get_tickers():
    """Get list of tickers from the main page"""
    url = "https://smart-lab.ru/q/shares/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    tickers = []
    for link in soup.find_all('a', href=re.compile(r'/q/[A-Z]+/f/y/')):
        ticker = link['href'].split('/')[2]
        if ticker not in tickers:
            tickers.append(ticker)
    
    return tickers

def get_financial_data(ticker):
    """Get financial data for a specific ticker"""
    url = f"https://smart-lab.ru/q/{ticker}/f/y/MSFO/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        data = {
            'Ticker': ticker,
            'Company_Name': None,
            'Sector': None, 
            'EBITDA': None,
            'Net_Profit': None,
            'Net_Debt': None,
            'Net_Assets': None,
            'Assets': None,
            'ROE': None,
            'ROA': None,
            'Net_Margin': None
        }
        
        # Find company name and sector
        for th_tag in soup.find_all('th'):
            span = th_tag.find('span')
            if span and "smart-lab.ru" in span.get_text():
                company_name = th_tag.find(text=True, recursive=False).strip()
                data['Company_Name'] = company_name
        
        for a_tag in soup.find_all('a', string=lambda text: text and "Aнализ сектора " in text):
            sector_analysis = a_tag.get_text().split("Aнализ сектора ", 1)[-1].strip()
            data['Sector'] = sector_analysis

        # Find financial data
        rows = soup.find_all('tr')
        for row in rows:
            field = row.find('th')
            if not field:
                continue
                
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
                
            field_text = field.text.strip()
            value_cell = cells[-3]
            
            if value_cell:
                value = value_cell.text.strip()
                
                if field_text.startswith('EBITDA'):
                    data['EBITDA'] = value
                elif 'Чистая прибыль' in field_text:
                    data['Net_Profit'] = value
                elif 'Чистый долг' in field_text:
                    data['Net_Debt'] = value
                elif 'Чистые активы' in field_text:
                    data['Net_Assets'] = value
                elif 'Активы' in field_text and data['Assets'] is None:
                    data['Assets'] = value
                elif 'ROE' in field_text:
                    data['ROE'] = value
                elif 'ROA' in field_text:
                    data['ROA'] = value
                elif 'Чистая рентаб' in field_text:
                    data['Net_Margin'] = value
        
        return data
        
    except Exception as e:
        st.error(f"Error processing {ticker}: {str(e)}")
        return None

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Main app functionality
if st.button("Start Scraping", type="primary"):
    with st.spinner("Getting list of tickers..."):
        tickers = get_tickers()
    
    if tickers:
        st.success(f"Found {len(tickers)} companies")
        
        # Initialize containers
        progress_bar = st.progress(0)
        status_container = st.empty()
        data_container = st.empty()
        
        results = []
        for i, ticker in enumerate(tickers):
            # Update progress
            progress = (i + 1) / len(tickers)
            progress_bar.progress(progress)
            status_container.info(f"Processing {ticker} ({i+1}/{len(tickers)})")
            
            data = get_financial_data(ticker)
            if data:
                results.append(data)
                
                # Update data preview
                df_current = pd.DataFrame(results)
                data_container.dataframe(df_current, use_container_width=True)
            
            time.sleep(3)  # Respectful delay between requests
        
        # Final DataFrame
        df = pd.DataFrame(results)
        
        # Download section
        st.success("Scraping completed! Download the data below:")
        
        col1, col2 = st.columns(2)
        with col1:
            excel_data = to_excel(df)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name="financial_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        
        with col2:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="financial_data.csv",
                mime="text/csv",
            )
    else:
        st.error("Failed to retrieve tickers. Please try again later.")

# Add footer
st.markdown("---")
st.markdown("Good luck!")