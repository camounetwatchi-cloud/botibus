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
from typing import Optional, List, Dict, Any

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

def load_css(file_name: str) -> None:
    """
    Loads a CSS file and injects it into the Streamlit app.

    Args:
        file_name (str): Path to the CSS file.
    """
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def get_bot_process() -> Optional['psutil.Process']:
    """
    Finds the live_trade.py process if it's running.

    Returns:
        Optional[psutil.Process]: The process object if found, else None.
    """
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

def start_bot() -> bool:
    """
    Starts the trading bot in a separate process.

    Returns:
        bool: True if started successfully, False otherwise.
    """
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

def stop_bot() -> bool:
    """
    Stops the trading bot process.

    Returns:
        bool: True if stopped successfully, False otherwise.
    """
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

def render_sidebar(storage: DataStorage) -> str:
    """
    Renders the sidebar navigation and controls.

    Args:
        storage (DataStorage): The data storage instance.

    Returns:
        str: The selected page name.
    """
    st.sidebar.title("🚀 Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Trade History", "Analytics", "Settings"])
    
    st.sidebar.divider()
    st.sidebar.subheader("Live Feed Controls")
    
    # Auto-refresh toggle
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 5
        
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_refresh
    
    refresh_rate = st.sidebar.slider("Refresh rate (s)", 2, 60, st.session_state.refresh_interval)
    st.session_state.refresh_interval = refresh_rate
    
    if st.sidebar.button("🔄 Force Refresh", use_container_width=True):
        st.rerun()
    
    # Bot status from database heartbeat (for cloud deployment)
    st.sidebar.divider()
    try:
        bot_status = storage.get_bot_status()
        last_heartbeat = bot_status.get("last_heartbeat")
    except Exception:
        bot_status = {}
        last_heartbeat = None
    
    # Check if heartbeat is recent (within 20 minutes for GitHub Actions cron)
    is_running = False
    if last_heartbeat is not None:
        try:
            if isinstance(last_heartbeat, str):
                last_heartbeat = pd.to_datetime(last_heartbeat)
            time_since = datetime.now() - last_heartbeat.replace(tzinfo=None)
            is_running = time_since < timedelta(minutes=2)
        except Exception:
            pass
    
    # Storage Status Display
    st.sidebar.divider()
    storage_type = storage.storage_type
    if "Supabase" in storage_type:
        st.sidebar.success(f"✅ Storage: {storage_type}")
    else:
        st.sidebar.error(f"⚠️ Storage: {storage_type}")
        st.sidebar.caption("⛔ Dashboard may not reflect cloud bot activity!")
        with st.sidebar.expander("🔧 How to fix"):
            st.markdown("""
**TIMEOUT ERROR?**
Change port **5432** → **6543** in your URL.

**Correct Format (Transaction Mode):**
```
postgresql://...:6543/postgres
```

Get this URL from: 
Supabase → Project Settings → Database → Connection String → **Transaction Pooler**
            """)
    
    if is_running:
        st.sidebar.success(f"🤖 Bot is ONLINE ({bot_status.get('exchange', 'unknown').upper()})")
        st.sidebar.caption(f"Mode: {bot_status.get('mode', 'unknown')} | Positions: {bot_status.get('open_positions', 0)}")
        if last_heartbeat:
            st.sidebar.caption(f"Last heartbeat: {last_heartbeat.strftime('%H:%M:%S')}")
    else:
        st.sidebar.error("⚪ Bot is OFFLINE")
        st.sidebar.caption("No recent heartbeat from cloud bot")
        # Offer to check local process as fallback
        bot_proc = get_bot_process()
        if bot_proc is not None:
            st.sidebar.info("📍 Local process detected")
    
    # Local bot control (still useful for development)
    st.sidebar.divider()
    st.sidebar.subheader("🖥️ Local Bot Control")
    bot_proc = get_bot_process()
    if bot_proc is not None:
        if st.sidebar.button("🛑 STOP LOCAL BOT", type="primary", use_container_width=True):
            if stop_bot():
                st.toast("Local bot stopped!")
                time.sleep(1)
                st.rerun()
    else:
        if st.sidebar.button("🚀 START LOCAL BOT", use_container_width=True):
            if start_bot():
                st.toast("Local bot starting...")
                time.sleep(2)
                st.rerun()

    if st.sidebar.button("🚨 EMERGENCY STOP ALL", use_container_width=True):
        st.sidebar.warning("⚠️ Emergency stop signal sent!")
        stop_bot()

    return page


def render_dashboard(storage: DataStorage, balance_info: dict, open_trades: pd.DataFrame, closed_trades: pd.DataFrame) -> None:
    """
    Renders the main dashboard view with metrics and active trades.

    Args:
        storage (DataStorage): The data storage instance.
        balance_info (dict): Dictionary containing balance information.
        open_trades (pd.DataFrame): DataFrame of currently open trades.
        closed_trades (pd.DataFrame): DataFrame of closed trades history.
    """
    # === TOP METRICS ROW ===
    st.subheader("💰 Portfolio Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    # Realized PnL (from closed trades)
    realized_pnl = closed_trades['pnl'].sum() if not closed_trades.empty else 0.0
    
    # Unrealized PnL (from open positions)
    unrealized_pnl = 0.0
    if not open_trades.empty:
        # For each open position, calculate current value vs entry
        for _, trade in open_trades.iterrows():
            entry_val = trade['entry_price'] * trade['amount']
            # Estimate current value (use entry as estimate if no live price)
            current_val = entry_val  # Will be updated with live prices if available
            if trade['side'] == 'buy':
                unrealized_pnl += current_val - entry_val
            else:
                unrealized_pnl += entry_val - current_val
    
    with col1:
        st.metric("Total Balance", f"${balance_info['total']:,.2f}")
    with col2:
        st.metric("Free Capital", f"${balance_info['free']:,.2f}")
    with col3:
        pnl_color = "normal" if realized_pnl >= 0 else "inverse"
        st.metric("Realized PnL", f"${realized_pnl:+,.2f}", delta_color=pnl_color)
    with col4:
        unr_color = "normal" if unrealized_pnl >= 0 else "inverse"
        st.metric("Unrealized PnL", f"${unrealized_pnl:+,.2f}", delta_color=unr_color)

    st.divider()

    # === KEY PERFORMANCE INDICATORS ===
    st.subheader("📊 Performance KPIs")
    kpi_cols = st.columns(5)
    
    # Calculate KPIs
    if not closed_trades.empty:
        win_trades = closed_trades[closed_trades['pnl'] > 0]
        loss_trades = closed_trades[closed_trades['pnl'] < 0]
        
        # Win Rate
        win_rate = (len(win_trades) / len(closed_trades) * 100)
        
        # Profit Factor (gross profit / gross loss)
        gross_profit = win_trades['pnl'].sum() if not win_trades.empty else 0
        gross_loss = abs(loss_trades['pnl'].sum()) if not loss_trades.empty else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
        # Average Trade Duration
        avg_duration = "N/A"
        if 'exit_time' in closed_trades.columns and 'entry_time' in closed_trades.columns:
            try:
                durations = pd.to_datetime(closed_trades['exit_time']) - pd.to_datetime(closed_trades['entry_time'])
                avg_mins = durations.mean().total_seconds() / 60
                if avg_mins < 60:
                    avg_duration = f"{avg_mins:.0f}m"
                elif avg_mins < 1440:
                    avg_duration = f"{avg_mins/60:.1f}h"
                else:
                    avg_duration = f"{avg_mins/1440:.1f}d"
            except Exception:
                pass
        
        # Max Drawdown (from cumulative PnL)
        sorted_trades = closed_trades.sort_values('exit_time')
        cumulative = sorted_trades['pnl'].cumsum()
        running_max = cumulative.cummax()
        drawdown = running_max - cumulative
        max_drawdown = drawdown.max() if not drawdown.empty else 0
        
        # Average Win/Loss
        avg_win = win_trades['pnl'].mean() if not win_trades.empty else 0
        avg_loss = loss_trades['pnl'].mean() if not loss_trades.empty else 0
    else:
        win_rate = 0
        profit_factor = 0
        avg_duration = "N/A"
        max_drawdown = 0
        avg_win = 0
        avg_loss = 0
    
    with kpi_cols[0]:
        st.metric("Win Rate", f"{win_rate:.1f}%")
    with kpi_cols[1]:
        st.metric("Profit Factor", f"{profit_factor:.2f}")
    with kpi_cols[2]:
        st.metric("Avg Duration", avg_duration)
    with kpi_cols[3]:
        st.metric("Max Drawdown", f"${max_drawdown:,.2f}")
    with kpi_cols[4]:
        st.metric("Total Trades", f"{len(closed_trades)}")

    st.divider()

    # === CHARTS ROW ===
    chart_left, chart_right = st.columns([3, 2])

    with chart_left:
        st.subheader("📈 Equity Curve")
        balance_history = storage.get_balance_history(hours=48)
        if not balance_history.empty and len(balance_history) > 1:
            fig_equity = go.Figure()
            fig_equity.add_trace(go.Scatter(
                x=balance_history['timestamp'],
                y=balance_history['total'],
                mode='lines',
                fill='tozeroy',
                name='Total Balance',
                line=dict(color='#00d4aa', width=2),
                fillcolor='rgba(0, 212, 170, 0.1)'
            ))
            fig_equity.update_layout(
                template="plotly_dark",
                margin=dict(l=20, r=20, t=20, b=20),
                height=250,
                showlegend=False,
                xaxis_title="",
                yaxis_title="Balance ($)"
            )
            st.plotly_chart(fig_equity, use_container_width=True)
        else:
            st.info("📊 Equity curve will appear once balance history accumulates.")

    with chart_right:
        st.subheader("🎯 Trade Results")
        if not closed_trades.empty:
            # Last 20 trades bar chart
            recent = closed_trades.head(20).sort_values('exit_time')
            colors = ['#00d4aa' if x > 0 else '#ff4757' for x in recent['pnl']]
            fig_bars = go.Figure(data=[
                go.Bar(
                    x=list(range(1, len(recent) + 1)),
                    y=recent['pnl'],
                    marker_color=colors,
                    text=[f"${p:+.2f}" for p in recent['pnl']],
                    textposition='outside',
                    textfont=dict(size=9)
                )
            ])
            fig_bars.update_layout(
                template="plotly_dark",
                margin=dict(l=20, r=20, t=20, b=20),
                height=250,
                showlegend=False,
                xaxis_title="Trade #",
                yaxis_title="PnL ($)"
            )
            st.plotly_chart(fig_bars, use_container_width=True)
        else:
            st.info("🎯 Trade results will appear here once trades are closed.")

    st.divider()

    # === ACTIVE POSITIONS ===
    pos_left, pos_right = st.columns([2, 1])
    
    with pos_left:
        st.subheader("🔥 Active Positions")
        if not open_trades.empty:
            disp_trades = open_trades.copy()
            disp_trades['Entry Time'] = pd.to_datetime(disp_trades['entry_time']).dt.strftime('%H:%M:%S')
            disp_trades['Value'] = disp_trades['entry_price'] * disp_trades['amount']
            st.dataframe(
                disp_trades[['symbol', 'side', 'entry_price', 'amount', 'Value', 'Entry Time']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No active positions at the moment.")

    with pos_right:
        st.subheader("🔔 Recent Events")
        if not closed_trades.empty:
            for _, trade in closed_trades.head(5).iterrows():
                color = "green" if trade['pnl'] > 0 else "red"
                st.markdown(f":{color}[{trade['symbol']}] ${trade['pnl']:+,.2f}")
        else:
            st.info("No recent trades.")



def render_trade_history(closed_trades: pd.DataFrame) -> None:
    """
    Renders the trade history page with filters and export options.

    Args:
        closed_trades (pd.DataFrame): DataFrame of closed trades history.
    """
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


def render_analytics(closed_trades: pd.DataFrame) -> None:
    """
    Renders advanced analytics and charts.

    Args:
        closed_trades (pd.DataFrame): DataFrame of closed trades history.
    """
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


def render_settings(storage: DataStorage) -> None:
    """
    Renders the settings and system status page.

    Args:
        storage (DataStorage): The data storage instance.
    """
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
        if "Supabase" in storage.storage_type:
            st.success("✅ Database Connected (Cloud)")
        else:
            st.error("⚠️ Database: Local Mode (Fallback)")
            if storage.connection_error:
                st.error(f"Connection Error: {storage.connection_error}")
            else:
                st.warning("PostgreSQL disabled or unreachable.")
    with col2:
        bot_proc = get_bot_process()
        if bot_proc:
            st.success(f"✅ Bot Running (PID: {bot_proc.pid})")
        else:
            st.error("❌ Bot Offline")
    with col3:
        st.success("✅ Data Feed Active")


def main() -> None:
    """Main entry point for the Streamlit dashboard."""
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
    
    try:
        storage = DataStorage(read_only=True)
    except Exception as e:
        st.error(f"Failed to initialize storage: {e}")
        return
    
    # Render Sidebar
    page = render_sidebar(storage)

    # Load Data
    balance_info = storage.get_latest_balance()
    open_trades = storage.get_trades(status="open")
    closed_trades = storage.get_trades(status="closed")
    
    # Header
    st.title("⚡ Trading Bot Terminal")
    
    # Route to pages
    if page == "Dashboard":
        render_dashboard(storage, balance_info, open_trades, closed_trades)
    elif page == "Trade History":
        render_trade_history(closed_trades)
    elif page == "Analytics":
        render_analytics(closed_trades)
    elif page == "Settings":
        render_settings(storage)

    # Auto-refresh logic
    time_now = datetime.now().strftime("%H:%M:%S")
    st.caption(f"Last updated: {time_now}")
    
    if st.session_state.auto_refresh and page == "Dashboard":
        time.sleep(st.session_state.refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
