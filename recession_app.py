import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import altair as alt
import os

# --- CONFIG ---
FRED_API_KEY = st.secrets.get("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

st.set_page_config(page_title="Recession Indicator Dashboard", layout="wide")
st.title("📉 Recession Indicator Dashboard")
st.markdown("Tracking recession risk using real-time macro, credit, and consumer indicators")

# --- TIMEFRAME SELECTOR ---
timeframe = st.selectbox("Select timeframe:", ["YTD", "1Y", "3Y", "5Y", "10Y", "Max"])
today = datetime.date.today()
timeframe_map = {
    "YTD": datetime.date(today.year, 1, 1),
    "1Y": today - datetime.timedelta(days=365),
    "3Y": today - datetime.timedelta(days=3 * 365),
    "5Y": today - datetime.timedelta(days=5 * 365),
    "10Y": today - datetime.timedelta(days=10 * 365),
    "Max": datetime.date(2000, 1, 1)
}
start_date = timeframe_map[timeframe]

# --- HELPERS ---
def get_fred_series(series_id, label):
    series = fred.get_series(series_id, observation_start=start_date)
    df = pd.DataFrame(series, columns=[label])
    df.index = pd.to_datetime(df.index)
    return df.dropna()

def get_yahoo_series(ticker, label):
    df = yf.download(ticker, start=start_date, progress=False)
    if df.empty or 'Close' not in df:
        return pd.DataFrame(columns=[label])
    df = df[['Close']].dropna()
    df.columns = [label]
    return df

def plot_indicator(name, data, category, threshold=None, reverse=False, y_min=None):
    with st.container():
        if data.empty:
            st.warning(f"{name} – No data available for selected timeframe.")
            return

        st.markdown(f"**{category} → {name}**")

        latest_val = data.iloc[-1].values[0]
        status = ""
        if threshold is not None:
            if reverse:
                if latest_val > threshold:
                    status = "🔴"
                elif latest_val > threshold * 0.8:
                    status = "🟡"
                else:
                    status = "🟢"
            else:
                if latest_val < threshold:
                    status = "🔴"
                elif latest_val < threshold * 1.2:
                    status = "🟡"
                else:
                    status = "🟢"

        st.markdown(f"**Latest:** {latest_val:.2f} {status}")

        df = data.reset_index().rename(columns={"index": "Date"})
        y_col = df.columns[1]
        y_axis = alt.Y(
            y_col,
            title="",
            scale=alt.Scale(domainMin=y_min) if y_min is not None else alt.Undefined
        )

        line = alt.Chart(df).mark_line().encode(
            x=alt.X("Date:T", axis=alt.Axis(format="%b-%y", title="Date")),
            y=y_axis,
            tooltip=["Date", y_col]
        )

        min_row = df.loc[df[y_col].idxmin()]
        max_row = df.loc[df[y_col].idxmax()]
        min_point = alt.Chart(pd.DataFrame([min_row])).mark_point(color="blue", size=80).encode(
            x="Date:T", y=y_col, tooltip=["Date", y_col]
        )
        max_point = alt.Chart(pd.DataFrame([max_row])).mark_point(color="red", size=80).encode(
            x="Date:T", y=y_col, tooltip=["Date", y_col]
        )

        min_label = alt.Chart(pd.DataFrame([min_row])).mark_text(
            align="left", dx=5, dy=-10, color="blue"
        ).encode(
            x="Date:T", y=y_col, text=alt.Text(y_col, format=".2f")
        )
        max_label = alt.Chart(pd.DataFrame([max_row])).mark_text(
            align="left", dx=5, dy=-10, color="red"
        ).encode(
            x="Date:T", y=y_col, text=alt.Text(y_col, format=".2f")
        )

        chart = (line + min_point + max_point + min_label + max_label).properties(height=200)
        st.altair_chart(chart, use_container_width=True)

# --- MACROECONOMIC ---
st.header("📊 Economic Conditions")
col1, col2 = st.columns(2)
with col1:
    gdp = get_fred_series("A191RL1Q225SBEA", "GDP QoQ (%)")
    plot_indicator("GDP Growth (QoQ)", gdp, "Macroeconomic", threshold=0)

    cpi = get_fred_series("CPIAUCSL", "CPI Index")
    cpi["Inflation (YoY %)"] = cpi["CPI Index"].pct_change(periods=12) * 100
    inflation = cpi[["Inflation (YoY %)"]].dropna()
    plot_indicator("Inflation (YoY %)", inflation, "Macroeconomic", threshold=2, reverse=True)

with col2:
    unemployment = get_fred_series("UNRATE", "Unemployment Rate")
    plot_indicator("Unemployment Rate", unemployment, "Macroeconomic", threshold=5, reverse=True)

    inflation_exp = get_fred_series("T5YIE", "5Y Inflation Expectations")
    plot_indicator("Inflation Expectations (5Y)", inflation_exp, "Macroeconomic", threshold=2.5, reverse=True)

# --- MARKET INDICATORS ---
st.header("📈 Market Indicators")
col1, col2 = st.columns(2)
with col1:
    sp500 = get_yahoo_series("^GSPC", "S&P 500")
    plot_indicator("S&P 500", sp500, "Market", threshold=3000)
with col2:
    vix = get_yahoo_series("^VIX", "VIX")
    plot_indicator("VIX Volatility Index", vix, "Market", threshold=20, reverse=True)

# --- YIELD CURVE ---
st.header("💵 Treasury Yield Curve")
yields = pd.DataFrame()
yields["1Y"] = get_fred_series("GS1", "1Y")
yields["3Y"] = get_fred_series("GS3", "3Y")
yields["5Y"] = get_fred_series("GS5", "5Y")
yields["10Y"] = get_fred_series("GS10", "10Y")
yields = yields.dropna()
yields = yields[yields.index >= start_date]
yields_long = yields.reset_index().melt(id_vars="index", var_name="Maturity", value_name="Yield")
yields_long.rename(columns={"index": "Date"}, inplace=True)

yield_chart = alt.Chart(yields_long).mark_line().encode(
    x="Date:T",
    y="Yield:Q",
    color="Maturity:N",
    tooltip=["Date", "Maturity", "Yield"]
).properties(title="Treasury Yields by Maturity", height=300)
st.altair_chart(yield_chart, use_container_width=True)

# --- CONSUMER HEALTH ---
st.header("🚗 Consumer Financial Health")
col1, col2 = st.columns(2)
with col1:
    delinquencies = get_fred_series("DRCCLACBS", "Credit Card Delinquency Rate")
    plot_indicator("Credit Card Delinquency Rate", delinquencies, "Consumer", threshold=3, reverse=True)

    savings = get_fred_series("PSAVERT", "Personal Savings Rate")
    plot_indicator("Personal Savings Rate", savings, "Consumer", threshold=5)

with col2:
    loans = get_fred_series("CONSUMERLOANS", "Consumer Loans")
    plot_indicator("Consumer Loans at Banks", loans, "Consumer", threshold=3000)

    retail_sales = get_fred_series("RSXFS", "Retail Sales (ex-Autos)")
    plot_indicator("Retail Sales (Ex-Autos)", retail_sales, "Consumer", threshold=100)

# --- CONSUMER MOBILITY ---
st.header("✈️ Consumer Mobility")
col1, col2 = st.columns(2)
with col1:
    gas = get_fred_series("MGACSR", "Gasoline Demand")
    plot_indicator("Weekly Gasoline Demand", gas, "Mobility", threshold=7000)

with col2:
    air_traffic = get_fred_series("ENPLANE", "Air Travel Enplanements")
    plot_indicator("Air Travel Enplanements", air_traffic, "Mobility", threshold=60000)

st.markdown("---")
st.caption("Data from FRED & Yahoo Finance | Dashboard by Levi Jobe")