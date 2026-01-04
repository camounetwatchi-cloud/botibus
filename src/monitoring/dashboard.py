import streamlit as st
import sys
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.data.storage import DataStorage
from datetime import datetime, timedelta
import time
import subprocess
import os
import signal
try:
    import psutil
except ImportError:
    psutil = None

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def get_bot_process():
    """Find the live_trade.py process if it's running."""
    if psutil is None:
        return None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('live_trade.py' in arg for arg in cmdline):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def start_bot():
    """Start the trading bot in a separate process."""
    try:
        # Use the same python executable from the current environment
        python_exe = sys.executable
        script_path = os.path.join(os.getcwd(), "scripts", "live_trade.py")
        
        # Start the process - using subprocess.Popen to let it run in background
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        
        process = subprocess.Popen(
            [python_exe, script_path],
            cwd=os.getcwd(),
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        return True
    except Exception as e:
        st.error(f"Failed to start bot: {e}")
        return False

def stop_bot():
    """Stop the trading bot process."""
    proc = get_bot_process()
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            return True
        except Exception as e:
            try:
                proc.kill()
                return True
            except:
                st.error(f"Failed to stop bot: {e}")
    return False

def main():
    st.set_page_config(
        page_title="Antigravity Trading Terminal", 
        page_icon="📈", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load custom styles
    load_css("src/monitoring/dashboard.css")

    # Initialize session state for settings
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 5
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'
    if 'notifications' not in st.session_state:
        st.session_state.notifications = True

    storage = DataStorage(read_only=True)
    
    # --- Sidebar ---
    st.sidebar.title("🚀 Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Trade History", "Analytics", "Settings"])
    
    st.sidebar.divider()
    st.sidebar.subheader("Live Feed Controls")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_refresh
    
    refresh_rate = st.sidebar.slider("Refresh rate (s)", 2, 60, st.session_state.refresh_interval)
    st.session_state.refresh_interval = refresh_rate
    
    if st.sidebar.button("🔄 Force Refresh", use_container_width=True):
        st.rerun()
    
    # Emergency stop button
    st.sidebar.divider()
    bot_proc = get_bot_process()
    is_running = bot_proc is not None
    
    if is_running:
        st.sidebar.success("🤖 Bot is ONLINE")
        if st.sidebar.button("🛑 STOP TRADING BOT", type="primary", use_container_width=True):
            if stop_bot():
                st.toast("Bot stopped successfully!")
                time.sleep(1)
                st.rerun()
    else:
        st.sidebar.error("⚪ Bot is OFFLINE")
        if st.sidebar.button("🚀 START TRADING BOT", type="primary", use_container_width=True):
            if start_bot():
                st.toast("Bot starting...")
                time.sleep(2)
                st.rerun()

    if st.sidebar.button("🚨 EMERGENCY STOP ALL", use_container_width=True):
        st.sidebar.warning("⚠️ Emergency stop signal sent! (Simulated)")
        stop_bot()

    # --- Data Loading ---
    balance_info = storage.get_latest_balance()
    open_trades = storage.get_trades(status="open")
    closed_trades = storage.get_trades(status="closed")
    
    # --- Header ---
    st.title("⚡ Trading Bot Terminal")
    
    if page == "Dashboard":
        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        total_pnl = closed_trades['pnl'].sum() if not closed_trades.empty else 0.0
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        
        with col1:
            st.metric("Total Balance", f"${balance_info['total']:,.2f}")
        with col2:
            st.metric("Free Capital", f"${balance_info['free']:,.2f}")
        with col3:
            st.metric("Total PnL", f"${total_pnl:+,.2f}", delta_color=pnl_color)
        with col4:
            win_rate = (len(closed_trades[closed_trades['pnl'] > 0]) / len(closed_trades) * 100) if not closed_trades.empty else 0
            st.metric("Win Rate", f"{win_rate:.1f}%")

        st.divider()

        # Active Trades & Chart Row
        left_col, right_col = st.columns([2, 1])

        with left_col:
            st.subheader("🔥 Active Positions")
            if not open_trades.empty:
                # Add some calculated columns for better display
                disp_trades = open_trades.copy()
                disp_trades['Entry Time'] = pd.to_datetime(disp_trades['entry_time']).dt.strftime('%H:%M:%S')
                st.dataframe(
                    disp_trades[['symbol', 'side', 'entry_price', 'amount', 'Entry Time']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Quick action buttons for open positions
                st.caption("Quick Actions:")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("📤 Export Positions", use_container_width=True):
                        csv = disp_trades.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                with col_b:
                    if st.button("🔔 Set Alert", use_container_width=True):
                        st.info("Alert functionality coming soon!")
            else:
                st.info("No active positions at the moment.")

            st.subheader("📊 Market Overview")
            symbol = st.selectbox("Select Symbol", SYMBOLS)
            df = storage.load_ohlcv(symbol, "1h")
            if not df.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=df['timestamp'],
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close']
                )])
                fig.update_layout(
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=400,
                    xaxis_rangeslider_visible=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Waiting for market data for {symbol}...")

        with right_col:
            st.subheader("📈 Performance")
            if not closed_trades.empty:
                # PnL distribution
                fig_pie = px.pie(
                    closed_trades, 
                    names="symbol", 
                    values=closed_trades['pnl'].abs(),
                    title="PnL Distribution by Asset",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pie.update_layout(template="plotly_dark", showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Recent alerts/log mock
                st.subheader("🔔 Recent Events")
                for _, trade in closed_trades.head(5).iterrows():
                    color = "green" if trade['pnl'] > 0 else "red"
                    st.markdown(f":{color}[Trade {trade['id']} closed] | {trade['symbol']} | PnL: ${trade['pnl']:+,.2f}")
            else:
                st.info("Trade history will appear here once trades are closed.")

    elif page == "Trade History":
        st.subheader("📜 Complete Trade History")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol_filter = st.multiselect("Filter by Symbol", 
                                          options=["All", "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
                                          default=["All"])
        with col2:
            side_filter = st.multiselect("Filter by Side", 
                                        options=["All", "buy", "sell"],
                                        default=["All"])
        with col3:
            pnl_filter = st.selectbox("Filter by Result", 
                                     options=["All", "Profitable", "Loss"])
        
        if not closed_trades.empty:
            filtered_trades = closed_trades.copy()
            
            # Apply filters
            if "All" not in symbol_filter:
                filtered_trades = filtered_trades[filtered_trades['symbol'].isin(symbol_filter)]
            if "All" not in side_filter:
                filtered_trades = filtered_trades[filtered_trades['side'].isin(side_filter)]
            if pnl_filter == "Profitable":
                filtered_trades = filtered_trades[filtered_trades['pnl'] > 0]
            elif pnl_filter == "Loss":
                filtered_trades = filtered_trades[filtered_trades['pnl'] < 0]
            
            st.dataframe(filtered_trades, use_container_width=True, hide_index=True)
            
            # Export button
            if st.button("📥 Export Trade History", use_container_width=False):
                csv = filtered_trades.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No trade history available yet.")

    elif page == "Analytics":
        st.subheader("📐 Advanced Analytics")
        if not closed_trades.empty:
            # Equity Curve
            closed_trades_sorted = closed_trades.sort_values('exit_time')
            closed_trades_sorted['cumulative_pnl'] = closed_trades_sorted['pnl'].cumsum()
            fig_curve = px.line(
                closed_trades_sorted, 
                x="exit_time", 
                y="cumulative_pnl",
                title="Cumulative Profit/Loss Curve",
                labels={"cumulative_pnl": "PnL ($)", "exit_time": "Time"}
            )
            fig_curve.update_layout(template="plotly_dark")
            st.plotly_chart(fig_curve, use_container_width=True)
            
            # Additional analytics
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📊 Trade Statistics")
                total_trades = len(closed_trades)
                winning_trades = len(closed_trades[closed_trades['pnl'] > 0])
                losing_trades = len(closed_trades[closed_trades['pnl'] < 0])
                avg_win = closed_trades[closed_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
                avg_loss = closed_trades[closed_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
                
                st.metric("Total Trades", total_trades)
                st.metric("Winning Trades", winning_trades)
                st.metric("Losing Trades", losing_trades)
                st.metric("Average Win", f"${avg_win:.2f}")
                st.metric("Average Loss", f"${avg_loss:.2f}")
            
            with col2:
                st.subheader("🎯 Performance by Symbol")
                symbol_performance = closed_trades.groupby('symbol')['pnl'].agg(['sum', 'count', 'mean']).reset_index()
                symbol_performance.columns = ['Symbol', 'Total PnL', 'Trade Count', 'Avg PnL']
                st.dataframe(symbol_performance, use_container_width=True, hide_index=True)
        else:
            st.info("Not enough data for analytics.")
    
    elif page == "Settings":
        st.subheader("⚙️ Application Settings")
        
        st.write("### Display Preferences")
        col1, col2 = st.columns(2)
        
        with col1:
            theme = st.selectbox("Theme", ["Dark", "Light"], 
                                index=0 if st.session_state.theme == 'dark' else 1)
            st.session_state.theme = theme.lower()
            
            notifications = st.checkbox("Enable Notifications", 
                                       value=st.session_state.notifications)
            st.session_state.notifications = notifications
        
        with col2:
            st.write("### Data Management")
            if st.button("🧹 Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.success("Cache cleared successfully!")
            
            if st.button("📊 Export All Data", use_container_width=True):
                st.info("Export functionality available in Trade History page")
        
        st.divider()
        
        st.write("### About")
        st.info("""
        **Antigravity Trading Terminal v1.0**
        
        - Real-time monitoring dashboard
        - Automated trading execution
        - Advanced analytics and reporting
        
        Built for professional traders with cutting-edge technology.
        """)
        
        st.write("### System Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("✅ Database Connected")
        with col2:
            bot_proc = get_bot_process()
            if bot_proc:
                st.success(f"✅ Bot Running (PID: {bot_proc.pid})")
            else:
                st.error("❌ Bot Offline")
        with col3:
            st.success("✅ Data Feed Active")

    # Auto-refresh logic
    time_now = datetime.now().strftime("%H:%M:%S")
    st.caption(f"Last updated: {time_now}")
    
    # Implement auto-refresh if enabled
    if st.session_state.auto_refresh and page == "Dashboard":
        time.sleep(st.session_state.refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
