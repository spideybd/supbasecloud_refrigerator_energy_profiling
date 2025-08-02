# dashboard.py

import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Fridge Energy Monitor (Cloud)",
    page_icon="⚡",
    layout="wide"
)

# --- Connect to Supabase ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Could not connect to Supabase. Check your Streamlit secrets.")
    st.info(f"Error: {e}")
    st.stop()


# --- Functions (The kWh calculation function remains the same) ---
def calculate_total_kwh(df):
    if len(df) < 2: return 0.0
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds()
    df['avg_power'] = df['power_w'].rolling(window=2).mean()
    df['energy_joules'] = df['avg_power'] * df['time_diff']
    total_joules = df['energy_joules'].sum()
    total_kwh = total_joules / 3600000
    return total_kwh


# --- Main Application ---
st.title("Refrigerator Real-Time Energy Monitor ☁️")
st.caption("Powered by a local collector and a cloud database. This page will auto-refresh.")

# --- 2. CREATE A PLACEHOLDER ---
placeholder = st.empty()


# --- 3. WRAP THE LOGIC IN A 'WHILE TRUE' LOOP ---
while True:
    try:
        # --- 4. USE THE PLACEHOLDER CONTAINER ---
        with placeholder.container():
            # Fetch the most recent 1000 records
            response = supabase.table('energy_log').select("*").order('timestamp', desc=True).limit(1000).execute()
            data = response.data
            
            if not data:
                st.warning("Waiting for data... Is the local collector script running?")
                time.sleep(15) 
                continue

            df = pd.DataFrame(data).sort_values('timestamp').reset_index(drop=True)

            # Display Metrics from the most recent data point
            latest_reading = df.iloc[-1]
            power = latest_reading['power_w']
            voltage = latest_reading['voltage_v']
            current = latest_reading['current_ma']
            total_kwh = calculate_total_kwh(df)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("⚡ Power", f"{power:.2f} W")
            col2.metric("🔌 Voltage", f"{voltage:.1f} V")
            col3.metric("💡 Current", f"{current} mA")
            col4.metric("🔋 Total Usage", f"{total_kwh:.3f} kWh")

            # Historical Data Chart
            st.subheader("Power Usage Over Time (Last 100 Readings)")
            chart_df = df.tail(100).rename(columns={'timestamp':'index'}).set_index('index')
            st.line_chart(chart_df['power_w'])
            
            with st.expander("Show Raw Data Log"):
                st.dataframe(df.tail(20))

    except Exception as e:
        with placeholder.container():
            st.error(f"🔥 An error occurred: {e}")
            st.warning("Will attempt to reconnect in 15 seconds...")
    
    time.sleep(15)
