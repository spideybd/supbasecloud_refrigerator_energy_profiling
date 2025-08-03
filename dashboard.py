# dashboard.py (Updated with control buttons)

import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# --- Page Configuration and Supabase Connection (Same as before) ---
st.set_page_config(page_title="Fridge Energy Monitor (Cloud)", page_icon="⚡", layout="wide")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"] # Use the anon public key
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Could not connect to Supabase. Check your Streamlit secrets.")
    st.info(f"Error: {e}")
    st.stop()

# --- Functions (Same as before) ---
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
st.title("Refrigerator Real-Time Energy Monitor & Control ☁️")
st.caption("Powered by a local collector and a cloud database. This page will auto-refresh.")

# --- NEW: Add Control Buttons ---
st.subheader("Plug Control")
col1, col2 = st.columns(2)

with col1:
    if st.button("🟢 Turn Plug ON"):
        try:
            # Insert a new 'ON' command into the database
            supabase.table('commands').insert({"command": "ON"}).execute()
            st.success("Smart plug turned on!")
        except Exception as e:
            st.error(f"Failed to send command: {e}")

with col2:
    if st.button("🔴 Turn Plug OFF"):
        try:
            # Insert a new 'OFF' command into the database
            supabase.table('commands').insert({"command": "OFF"}).execute()
            st.success("Smart plug turned off!")
        except Exception as e:
            st.error(f"Failed to send command: {e}")

st.divider() # Add a visual separator

# --- Auto-Refreshing Dashboard (Same as before) ---
placeholder = st.empty()

while True:
    try:
        with placeholder.container():
            response = supabase.table('energy_log').select("*").order('timestamp', desc=True).limit(1000).execute()
            data = response.data
            
            if not data:
                st.warning("Waiting for data...")
                time.sleep(15) 
                continue

            df = pd.DataFrame(data).sort_values('timestamp').reset_index(drop=True)
            
            # --- Display Metrics and Chart (Same as before) ---
            latest_reading = df.iloc[-1]
            power = latest_reading['power_w']
            voltage = latest_reading['voltage_v']
            current = latest_reading['current_ma']
            total_kwh = calculate_total_kwh(df)

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("⚡ Power", f"{power:.2f} W")
            m_col2.metric("🔌 Voltage", f"{voltage:.1f} V")
            m_col3.metric("💡 Current", f"{current} mA")
            m_col4.metric("🔋 Total Usage", f"{total_kwh:.3f} kWh")

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

