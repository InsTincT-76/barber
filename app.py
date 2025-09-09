import os
import pandas as pd
import numpy as np
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta



def get_gspread_client(credentials_path: str, scopes: list[str]):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scopes)
    return gspread.authorize(credentials)


@st.cache_data(show_spinner=False)
def load_sales_dataframe(sheet_id: str, credentials_path: str) -> pd.DataFrame:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    client = get_gspread_client(credentials_path, scopes)
    worksheet = client.open_by_key(sheet_id).sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        return df

    # Normalize columns
    df.columns = [c.strip().title() for c in df.columns]

    # Drop form timestamp and map Barber -> Barber Name
    if "Timestamp" in df.columns:
        df = df.drop(columns=["Timestamp"]) 
    if "Barber Name" not in df.columns and "Barber" in df.columns:
        df = df.rename(columns={"Barber": "Barber Name"})

    # Parse date (accepts 7/1/2025 or 07-01-2025, etc.)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    else:
        df["Date"] = pd.NaT

    # Coerce numeric price (strip currency/commas if present)
    if "Price" in df.columns:
        df["Price"] = (
            df["Price"].astype(str).str.replace(r"[^0-9\.-]", "", regex=True)
        )
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    else:
        df["Price"] = np.nan

    # Normalize text fields
    for col in ["Barber Name", "Payment Method"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["Date", "Price"])  # keep only valid rows
    return df


def filter_by_period(df: pd.DataFrame, mode: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    mask = (df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))
    return df.loc[mask].copy()


def compute_summaries(df: pd.DataFrame) -> dict:
    results: dict[str, pd.DataFrame | float | int] = {}
    results["total_revenue"] = float(df["Price"].sum()) if not df.empty else 0.0
    results["num_transactions"] = int(len(df))

    if "Barber Name" in df.columns:
        by_barber = df.groupby("Barber Name")["Price"].agg(["sum", "count"]).reset_index()
        by_barber = by_barber.rename(columns={"sum": "revenue", "count": "transactions"})
        results["by_barber"] = by_barber.sort_values("revenue", ascending=False)

    if "Payment Method" in df.columns:
        by_method = df.groupby("Payment Method")["Price"].agg(["sum", "count"]).reset_index()
        by_method = by_method.rename(columns={"sum": "revenue", "count": "transactions"})
        results["by_method"] = by_method.sort_values("revenue", ascending=False)

    by_day = df.groupby(df["Date"].dt.date)["Price"].sum().reset_index(name="revenue")
    results["by_day"] = by_day
    return results


def format_currency(value: float) -> str:
    return f"OMR {value:,.2f}"


def ai_insights(df: pd.DataFrame, summaries: dict) -> list[str]:
    insights: list[str] = []
    if df.empty:
        return ["No data in the selected range."]

    # Heuristic insights
    if "by_barber" in summaries and not summaries["by_barber"].empty:
        top_row = summaries["by_barber"].iloc[0]
        insights.append(
            f"Top performer: {top_row['Barber Name']} with {format_currency(top_row['revenue'])} across {int(top_row['transactions'])} cuts."
        )

    if "by_method" in summaries and not summaries["by_method"].empty:
        methods = summaries["by_method"].set_index("Payment Method")
        cash = methods["revenue"].get("Cash", 0)
        card = float(methods["revenue"].sum() - cash)
        if cash or card:
            share = (cash / (cash + card)) * 100 if (cash + card) else 0
            insights.append(f"Cash share: {share:.1f}% (Cash {format_currency(cash)} vs Card {format_currency(card)}).")

    # Day-of-week trend
    df["dow"] = df["Date"].dt.day_name()
    by_dow = df.groupby("dow")["Price"].mean().sort_values()
    if not by_dow.empty:
        slowest = by_dow.index[0]
        fastest = by_dow.index[-1]
        if by_dow.iloc[-1] > 0:
            drop = (1 - by_dow.iloc[0] / by_dow.iloc[-1]) * 100
            insights.append(f"{slowest}s are {drop:.0f}% slower than {fastest}s on average.")

    return insights


    # (AI chat removed)
    return []


def main():
    st.set_page_config(page_title="Barbershop Sales", page_icon="💈", layout="wide")
    st.title("💈 Barbershop Sales Dashboard")

    with st.sidebar:
        st.header("Settings")
        credentials_path = st.text_input(
            "Service account JSON path",
            value=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/Users/instinct/Desktop/test/lasgidi-471606-75e838c5829c.json"),
        )
        sheet_id = st.text_input("Google Sheet ID", value=os.getenv("SHEET_ID", ""))
        st.caption("Share the sheet with the service account email shown inside the JSON file.")
        # (AI key input removed)

        st.header("Aggregation")
        mode = st.radio("Period", ["Daily", "Weekly", "Monthly"], index=0, horizontal=True)

        today = datetime.today().date()
        default_start = today - timedelta(days=6)

        if mode == "Daily":
            start_date = st.date_input("Date", value=today)
            end_date = start_date
        elif mode == "Weekly":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Week start", value=default_start)
            with col2:
                end_date = st.date_input("Week end", value=today)
        else:  # Monthly
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start date", value=default_start.replace(day=1))
            with col2:
                end_date = st.date_input("End date", value=today)

        load_btn = st.button("Load Data", type="primary")

    # Load data when button pressed, and persist in session state
    if load_btn:
        if not sheet_id:
            st.error("Please provide a Google Sheet ID in the sidebar.")
        else:
            with st.spinner("Loading data..."):
                try:
                    st.session_state.df = load_sales_dataframe(sheet_id, credentials_path)
                except Exception as ex:
                    st.exception(ex)
                    st.session_state.df = pd.DataFrame()

    # If we have data in session, compute filtered and render
    if "df" in st.session_state and not st.session_state.df.empty:
        filtered = filter_by_period(st.session_state.df, mode, start_date, end_date)
        summaries = compute_summaries(filtered)

        st.subheader("Filtered Rows")
        st.dataframe(filtered, use_container_width=True)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Revenue", format_currency(summaries["total_revenue"]))
        col_b.metric("Transactions", f"{summaries['num_transactions']}")
        avg_ticket = summaries["total_revenue"] / summaries["num_transactions"] if summaries["num_transactions"] else 0
        col_c.metric("Avg Ticket", format_currency(avg_ticket))

        st.subheader("Breakdowns")
        if "by_barber" in summaries:
            st.markdown("**By Barber**")
            st.dataframe(summaries["by_barber"], use_container_width=True)
        if "by_method" in summaries:
            st.markdown("**By Payment Method**")
            st.dataframe(summaries["by_method"], use_container_width=True)

        st.subheader("Insights")
        for tip in ai_insights(filtered, summaries):
            st.write("- ", tip)
    else:
        st.info("Load data from the sidebar to view summaries.")


if __name__ == "__main__":
    main()


