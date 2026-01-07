"""
Auto-Learning Module for Trading Bot.

Implements automated performance analysis and parameter adjustment:
- Daily trade analysis
- Dynamic confidence threshold adjustment
- Symbol blacklisting based on performance
- Model retraining triggers
- Parameter optimization suggestions
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from src.data.storage import DataStorage
from src.learning.performance import PerformanceAnalyzer
from src.config.settings import settings


class AutoLearner:
    """
    Automated learning and parameter adjustment system.
    
    Analyzes trading performance daily and:
    1. Adjusts confidence thresholds per symbol
    2. Manages symbol blacklist
    3. Suggests risk parameter changes
    4. Triggers model retraining when needed
    """
    
    CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "dynamic_params.json"
    
    # Thresholds for adjustments
    MIN_TRADES_FOR_ANALYSIS = 10
    BLACKLIST_WIN_RATE = 0.35      # Blacklist if win rate < 35%
    BOOST_WIN_RATE = 0.65          # Boost confidence if win rate > 65%
    CONSECUTIVE_LOSS_DAYS = 3      # Reduce risk after 3 losing days
    CONSECUTIVE_WIN_DAYS = 5       # Increase risk after 5 winning days
    RETRAIN_AUC_THRESHOLD = 0.55   # Retrain if model AUC drops below this
    
    def __init__(self, storage: DataStorage = None):
        """
        Initialize auto-learner.
        
        Args:
            storage: DataStorage instance (creates new if None)
        """
        self.storage = storage or DataStorage()
        self.analyzer = PerformanceAnalyzer(self.storage)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load dynamic configuration or create default."""
        if self.CONFIG_PATH.exists():
            with open(self.CONFIG_PATH, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            'last_analysis': None,
            'symbol_blacklist': [],
            'symbol_confidence_adjustments': {},
            'risk_multiplier': 1.0,
            'consecutive_loss_days': 0,
            'consecutive_win_days': 0,
            'retrain_suggested': False,
            'daily_pnl_history': []
        }
    
    def _save_config(self):
        """Save configuration to file."""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=2, default=str)
    
    def run_daily_analysis(self) -> Dict:
        """
        Run daily performance analysis and adjust parameters.
        
        Returns:
            Dictionary of adjustments made
        """
        logger.info("🧠 Running daily auto-learning analysis...")
        
        adjustments = {
            'timestamp': datetime.now().isoformat(),
            'blacklist_changes': [],
            'confidence_adjustments': {},
            'risk_adjustment': None,
            'retrain_suggested': False,
            'insights': []
        }
        
        # Analyze yesterday's performance
        yesterday_pnl = self._get_daily_pnl(days_ago=1)
        adjustments['insights'].append(f"Yesterday's PnL: €{yesterday_pnl:.2f}")
        
        # Update consecutive win/loss streak
        if yesterday_pnl > 0:
            self.config['consecutive_win_days'] += 1
            self.config['consecutive_loss_days'] = 0
        elif yesterday_pnl < 0:
            self.config['consecutive_loss_days'] += 1
            self.config['consecutive_win_days'] = 0
        
        # 1. Analyze symbol performance
        symbol_adjustments = self._analyze_symbols()
        adjustments['blacklist_changes'] = symbol_adjustments['blacklist_changes']
        adjustments['confidence_adjustments'] = symbol_adjustments['confidence']
        
        # 2. Adjust risk based on streaks
        risk_adj = self._adjust_risk_on_streaks()
        if risk_adj:
            adjustments['risk_adjustment'] = risk_adj
        
        # 3. Check if model retraining is needed
        if self._should_retrain():
            adjustments['retrain_suggested'] = True
            self.config['retrain_suggested'] = True
            adjustments['insights'].append("⚠️ Model retraining recommended")
        
        # Update daily PnL history
        self.config['daily_pnl_history'].append({
            'date': datetime.now().date().isoformat(),
            'pnl': yesterday_pnl
        })
        # Keep last 30 days
        self.config['daily_pnl_history'] = self.config['daily_pnl_history'][-30:]
        
        # Save updated config
        self.config['last_analysis'] = datetime.now().isoformat()
        self._save_config()
        
        # Log summary
        logger.info(f"   Blacklist: {self.config['symbol_blacklist']}")
        logger.info(f"   Risk multiplier: {self.config['risk_multiplier']:.2f}")
        logger.info(f"   Streak: {self.config['consecutive_win_days']} wins / {self.config['consecutive_loss_days']} losses")
        
        return adjustments
    
    def _get_daily_pnl(self, days_ago: int = 1) -> float:
        """Get PnL for a specific day."""
        try:
            trades = self.storage.get_trade_history(limit=100)
            if trades.empty:
                return 0
            
            target_date = (datetime.now() - timedelta(days=days_ago)).date()
            
            if 'exit_time' in trades.columns:
                trades['date'] = pd.to_datetime(trades['exit_time']).dt.date
                day_trades = trades[trades['date'] == target_date]
                
                if 'pnl' in day_trades.columns:
                    return day_trades['pnl'].sum()
                elif 'net_pnl' in day_trades.columns:
                    return day_trades['net_pnl'].sum()
            
            return 0
        except Exception as e:
            logger.warning(f"Error getting daily PnL: {e}")
            return 0
    
    def _analyze_symbols(self) -> Dict:
        """Analyze per-symbol performance and update adjustments."""
        result = {
            'blacklist_changes': [],
            'confidence': {}
        }
        
        for symbol in settings.SYMBOLS:
            stats = self.analyzer.get_symbol_stats(symbol, lookback_trades=30)
            
            if stats['total_trades'] < self.MIN_TRADES_FOR_ANALYSIS:
                continue
            
            win_rate = stats['win_rate']
            
            # Blacklist logic
            if win_rate < self.BLACKLIST_WIN_RATE:
                if symbol not in self.config['symbol_blacklist']:
                    self.config['symbol_blacklist'].append(symbol)
                    result['blacklist_changes'].append({
                        'symbol': symbol,
                        'action': 'added',
                        'reason': f'win_rate={win_rate:.1%}'
                    })
                    logger.warning(f"   ⛔ Blacklisted {symbol} (win rate: {win_rate:.1%})")
            else:
                # Remove from blacklist if performance improved
                if symbol in self.config['symbol_blacklist']:
                    self.config['symbol_blacklist'].remove(symbol)
                    result['blacklist_changes'].append({
                        'symbol': symbol,
                        'action': 'removed',
                        'reason': f'win_rate_improved={win_rate:.1%}'
                    })
                    logger.info(f"   ✅ Removed {symbol} from blacklist")
            
            # Confidence adjustment
            if win_rate >= self.BOOST_WIN_RATE:
                self.config['symbol_confidence_adjustments'][symbol] = 1.2
                result['confidence'][symbol] = 1.2
            elif win_rate >= 0.5:
                self.config['symbol_confidence_adjustments'][symbol] = 1.0
                result['confidence'][symbol] = 1.0
            else:
                self.config['symbol_confidence_adjustments'][symbol] = 0.8
                result['confidence'][symbol] = 0.8
        
        return result
    
    def _adjust_risk_on_streaks(self) -> Optional[Dict]:
        """Adjust risk based on winning/losing streaks."""
        current_mult = self.config['risk_multiplier']
        new_mult = current_mult
        reason = None
        
        if self.config['consecutive_loss_days'] >= self.CONSECUTIVE_LOSS_DAYS:
            new_mult = max(0.5, current_mult * 0.8)
            reason = f"{self.config['consecutive_loss_days']} consecutive losing days"
            logger.warning(f"   📉 Reducing risk: {reason}")
        
        elif self.config['consecutive_win_days'] >= self.CONSECUTIVE_WIN_DAYS:
            new_mult = min(1.5, current_mult * 1.1)
            reason = f"{self.config['consecutive_win_days']} consecutive winning days"
            logger.info(f"   📈 Increasing risk: {reason}")
        
        if new_mult != current_mult:
            self.config['risk_multiplier'] = new_mult
            return {
                'old': current_mult,
                'new': new_mult,
                'reason': reason
            }
        
        return None
    
    def _should_retrain(self) -> bool:
        """Check if model retraining is recommended."""
        # Check recent win rate across all symbols
        try:
            all_stats = self.analyzer.get_all_symbol_performance()
            
            if not all_stats:
                return False
            
            total_wins = sum(s.get('winning_trades', 0) for s in all_stats.values())
            total_trades = sum(s.get('total_trades', 0) for s in all_stats.values())
            
            if total_trades < 50:
                return False
            
            overall_win_rate = total_wins / total_trades
            
            # If win rate drops below 40%, suggest retraining
            if overall_win_rate < 0.40:
                logger.warning(f"   ⚠️ Overall win rate low: {overall_win_rate:.1%}")
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking retrain condition: {e}")
            return False
    
    def get_confidence_adjustment(self, symbol: str) -> float:
        """
        Get confidence multiplier for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Confidence multiplier (0.5 to 1.5)
        """
        return self.config['symbol_confidence_adjustments'].get(symbol, 1.0)
    
    def get_risk_multiplier(self) -> float:
        """Get current risk multiplier based on performance."""
        return self.config['risk_multiplier']
    
    def is_blacklisted(self, symbol: str) -> bool:
        """Check if symbol is currently blacklisted."""
        return symbol in self.config['symbol_blacklist']
    
    def get_insights_report(self) -> str:
        """Generate human-readable insights report."""
        lines = [
            "=" * 50,
            "🧠 AUTO-LEARNING INSIGHTS REPORT",
            "=" * 50,
            f"Last analysis: {self.config.get('last_analysis', 'Never')}",
            "",
            "📊 Current Status:",
            f"   Risk Multiplier: {self.config['risk_multiplier']:.2f}x",
            f"   Win Streak: {self.config['consecutive_win_days']} days",
            f"   Loss Streak: {self.config['consecutive_loss_days']} days",
            "",
            "⛔ Blacklisted Symbols:",
        ]
        
        if self.config['symbol_blacklist']:
            for sym in self.config['symbol_blacklist']:
                lines.append(f"   - {sym}")
        else:
            lines.append("   None")
        
        lines.extend([
            "",
            "📈 Symbol Confidence Adjustments:",
        ])
        
        for sym, adj in self.config['symbol_confidence_adjustments'].items():
            if adj != 1.0:
                lines.append(f"   {sym}: {adj:.1f}x")
        
        if self.config['retrain_suggested']:
            lines.extend([
                "",
                "⚠️ RECOMMENDATION: Model retraining suggested!",
            ])
        
        lines.append("=" * 50)
        
        return "\n".join(lines)


# CLI usage
if __name__ == "__main__":
    learner = AutoLearner()
    result = learner.run_daily_analysis()
    print(learner.get_insights_report())
