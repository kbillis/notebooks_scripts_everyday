# ═══════════════════════════════════════════════════════════════════
# 📈 ADVANCED STOCK ALERT SYSTEM
# Multi-Strategy Technical Analysis with Email Notifications
# ═══════════════════════════════════════════════════════════════════

import warnings
warnings.filterwarnings('ignore')

import argparse
import datetime
import logging
import os
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from typing import Dict, List, Tuple, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import schedule
import yfinance as yf
from tqdm import tqdm

# SendGrid import (optional)
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    HAS_SENDGRID = True
except ImportError:
    HAS_SENDGRID = False
    print("⚠️  SendGrid not installed. Run: pip install sendgrid")

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION & LOGGING
# ═══════════════════════════════════════════════════════════════════

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(f'stock_alerts_{datetime.date.today()}.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Configuration
class Config:
    # Email settings
    EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'sendgrid')  # 'sendgrid' or 'hotmail'
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
    SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')  # For Hotmail
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')  # For SendGrid
    RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', '')
    
    # Stock settings
    STOCKS_TO_TRACK = [
        'AAPL', 'MSFT', 'NIO'
        # , 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META',
        # 'MSFT', 'SOFI', 'ROKU', 'MRNA', 'ZM', 'SPCE', 'PLTR'
    ]
    
    
    CURRENCIES_TO_TRACK = ['GBPEUR=X', 'GBPCHF=X', 'EURUSD=X']
    
    # Trading parameters
    BOLLINGER_WINDOW_SHORT = 10
    BOLLINGER_WINDOW_LONG = 50
    RSI_WINDOW = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Alert settings
    ENABLE_EMAIL = True
    ENABLE_PLOTS = False
    ENABLE_HTML_OUTPUT = True
    DATA_START_DATE = '2022-01-01'
    CHECK_INTERVAL_HOURS = 1
    
    # Signal strength thresholds
    STRONG_SIGNAL_THRESHOLD = 2  # Number of indicators agreeing

# ═══════════════════════════════════════════════════════════════════
# EMAIL NOTIFICATION (YOUR FUNCTION)
# ═══════════════════════════════════════════════════════════════════

def send_email_to_inform(symbol: str, action: str, text: str, receiver: str, provider: str = "sendgrid"):
    """
    Sends an email notification based on a specific event.

    This function supports sending emails via SendGrid's API or Hotmail SMTP. 
    Credentials must be set as environment variables.

    Args:
        symbol (str): The stock or crypto symbol (e.g., "PLTR", "BTC").
        action (str): The type of event (e.g., "BUY", "SELL", "EMERGENCY").
        text (str): The body of the email message (can be HTML).
        receiver (str): The recipient's email address.
        provider (str): The email service provider ("sendgrid" or "hotmail").
    
    Returns:
        int: 1 if successful, 0 if failed.
    """
    if provider.lower() == "sendgrid":
        if not HAS_SENDGRID:
            log.error("SendGrid library not installed. Run: pip install sendgrid")
            return 0
            
        # Use the safer .get() method to prevent KeyError
        sender = os.environ.get('SENDER_EMAIL')
        api_key = os.environ.get('SENDGRID_API_KEY')

        # Check if the required environment variables are set
        if not sender or not api_key:
            log.error("Error: SENDER_EMAIL or SENDGRID_API_KEY environment variables not set.")
            log.error("Please set these variables and try again.")
            return 0

        current_date = datetime.date.today().strftime("%Y-%m-%d")

        # Construct the email message
        message = Mail(
            from_email=sender,
            to_emails=receiver,
            subject=f"Stock Bot: {current_date} {symbol} {action}",
            html_content=text
        )

        try:
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)

            if response.status_code == 202:
                log.info("### Email Sent Successfully via SendGrid ###")
                log.info(f"To: {receiver}")
                log.info(f"Subject: {message.subject}")
                log.info("---")
                return 1
            else:
                log.error(f"Error sending email. Status Code: {response.status_code}")
                log.error(response.body)
                return 0

        except Exception as e:
            # This will catch any errors from the API client or network issues
            log.error(f"An unexpected error occurred: {e}")
            return 0

    elif provider.lower() == "hotmail":
        try:
            sender = os.environ.get('SENDER_EMAIL')
            sender_pass = os.environ.get('SENDER_PASSWORD')
        except KeyError:
            log.error("Error: SENDER_EMAIL or SENDER_PASSWORD environment variables not set for Hotmail.")
            log.error("Please set these variables and try again.")
            return 0

        if not sender or not sender_pass:
            log.error("Error: SENDER_EMAIL or SENDER_PASSWORD not set.")
            return 0

        current_date = datetime.date.today().strftime("%Y-%m-%d")

        # Define the email content
        msg = EmailMessage()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = f"Stock Bot: {current_date} {symbol} {action}"
        
        # Set content (supports HTML)
        msg.set_content(text, subtype='html')

        # Use a secure SSL context
        context = ssl.create_default_context()
        smtp_server = "smtp.office365.com"
        smtp_port = 587

        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as smtp:
                smtp.starttls(context=context)  # Secure the connection
                smtp.login(sender, sender_pass)
                smtp.send_message(msg)
                log.info("### Email Sent Successfully via Hotmail ###")
                log.info(f"To: {receiver}")
                log.info(f"Subject: {msg['Subject']}")
                log.info("---")
                return 1
        except smtplib.SMTPAuthenticationError:
            log.error("Error: Failed to authenticate. Check your email and password.")
        except Exception as e:
            log.error(f"An unexpected error occurred: {e}")
        return 0

    else:
        log.error(f"Error: Unsupported provider '{provider}'. Please use 'sendgrid' or 'hotmail'.")
        return 0

# ═══════════════════════════════════════════════════════════════════
# GENERATE REPORTS & PLOTS
# ═══════════════════════════════════════════════════════════════════
def generate_report_content(report_data: dict) -> tuple[str, str]:
    """
    Transforms the trading signal dictionary into a formatted HTML report and a plain text summary.

    Args:
        report_data (dict): The dictionary containing analysis results for multiple symbols.

    Returns:
        tuple[str, str]: A tuple containing (html_content, text_summary).
    """
    html_rows = ""
    text_lines = []
    
    # Define color mappings for the Action column
    ACTION_COLORS = {
        'STRONG BUY': '#1F7A8C', # Teal/Strong Green
        'BUY': '#25AE7D',       # Medium Green
        'HOLD': '#5F5F5F',       # Gray
        'SELL': '#FF9900',       # Orange
        'STRONG SELL': '#D92121'  # Red
    }

    # Iterate over each symbol and its data
    for symbol, data in report_data.items():
        # Safely convert numpy types to standard floats and format
        current_price = float(data.get('current_price', 0))
        price_change_pct = float(data.get('price_change_pct', 0))
        signal_strength = float(data.get('signal_strength', 0))
        action = data.get('action', 'N/A')
        signals = '<br>'.join(data.get('signals', ['No specific signals.']))
        
        # Determine the color for the Action cell
        action_color = ACTION_COLORS.get(action, '#5F5F5F')
        
        # Determine the price change color
        price_color = '#D92121' if price_change_pct < 0 else '#25AE7D'

        # Build the HTML row for the symbol
        html_rows += f"""
        <tr style="border-bottom: 1px solid #ccc;">
            <td style="padding: 10px; font-weight: bold; font-size: 1.1em; color: #1F7A8C;">{symbol}</td>
            <td style="padding: 10px; font-weight: bold; color: {action_color};">{action}</td>
            <td style="padding: 10px; text-align: right;">{signal_strength:.1f}</td>
            <td style="padding: 10px; text-align: right;">${current_price:.2f}</td>
            <td style="padding: 10px; text-align: right; color: {price_color};">{price_change_pct:.2f}%</td>
            <td style="padding: 10px; font-size: 0.9em;">{signals}</td>
        </tr>
        """
        
        # Build the plain text summary line
        text_lines.append(
            f"Symbol: {symbol} | Action: {action} | Price: ${current_price:.2f} "
            f"| Change: {price_change_pct:.2f}% | Strength: {signal_strength:.1f}"
        )

    # --- Construct the Final HTML Content ---
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; }}
            .container {{ width: 90%; margin: 20px auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h2 {{ color: #1F7A8C; border-bottom: 2px solid #ccc; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #e0e0e0; color: #333; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; }}
            .signal-details td {{ font-size: 0.9em; color: #555; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📈 Trading Signal Report ({datetime.date.today().strftime("%Y-%m-%d")})</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 8%;">Symbol</th>
                        <th style="width: 10%;">Action</th>
                        <th style="width: 8%; text-align: right;">Signal Strength</th>
                        <th style="width: 10%; text-align: right;">Current Price</th>
                        <th style="width: 10%; text-align: right;">24h % Change</th>
                        <th style="width: 50%;">Key Signals</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
            <p style="margin-top: 30px; color: #777; font-size: 0.8em;">Note: Indicators like RSI, Bollinger Bands, and STOCH were used to generate these signals.</p>
        </div>
    </body>
    </html>
    """

    # --- Construct the Final Text Content ---
    text_summary = "Trading Report for Today:\n" + "\n".join(text_lines)
    
    return html_content, text_summary


# ═══════════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ═══════════════════════════════════════════════════════════════════

class TechnicalIndicators:
    """Calculate various technical indicators."""
    
    @staticmethod
    def sma(prices: pd.Series, window: int) -> pd.Series:
        """Simple Moving Average."""
        return prices.rolling(window=window).mean()
    
    @staticmethod
    def ema(prices: pd.Series, window: int) -> pd.Series:
        """Exponential Moving Average."""
        return prices.ewm(span=window, adjust=False).mean()
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = TechnicalIndicators.sma(prices, window)
        std = prices.rolling(window=window).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        return upper, sma, lower
    
    @staticmethod
    def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)."""
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """Average True Range (volatility indicator)."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()
        return atr
    
    @staticmethod
    def stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator."""
        lowest_low = low.rolling(window=window).min()
        highest_high = high.rolling(window=window).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=3).mean()
        return k, d

# ═══════════════════════════════════════════════════════════════════
# SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════════

class SignalGenerator:
    """Generate trading signals based on multiple indicators."""
    
    def __init__(self, df: pd.DataFrame, config: Config):
        self.df = df
        self.config = config
        self.signals = {}
        
    def analyze(self) -> Dict[str, any]:
        """Run all technical analysis and generate signals."""
        close = self.df['Close']
        high = self.df['High']
        low = self.df['Low']
        
        # Current price info
        current_price = close.iloc[-1]
        prev_close = close.iloc[-2] if len(close) > 1 else current_price
        price_change = ((current_price - prev_close) / prev_close) * 100
        
        # Calculate all indicators
        bb_upper_short, bb_mid_short, bb_lower_short = TechnicalIndicators.bollinger_bands(
            close, self.config.BOLLINGER_WINDOW_SHORT
        )
        bb_upper_long, bb_mid_long, bb_lower_long = TechnicalIndicators.bollinger_bands(
            close, self.config.BOLLINGER_WINDOW_LONG
        )
        
        rsi = TechnicalIndicators.rsi(close, self.config.RSI_WINDOW)
        macd_line, signal_line, histogram = TechnicalIndicators.macd(close)
        atr = TechnicalIndicators.atr(high, low, close)
        stoch_k, stoch_d = TechnicalIndicators.stochastic_oscillator(high, low, close)
        
        sma_20 = TechnicalIndicators.sma(close, 20)
        sma_50 = TechnicalIndicators.sma(close, 50)
        sma_200 = TechnicalIndicators.sma(close, 200)
        
        # Get current values
        current_rsi = rsi.iloc[-1]
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Generate signals
        signals = []
        signal_strength = 0
        action = "HOLD"
        
        # 1. Bollinger Bands (Short-term)
        if current_price < bb_lower_short.iloc[-1]:
            signals.append("🟢 BB_SHORT: Price below lower band (oversold)")
            signal_strength += 1
            action = "BUY"
        elif current_price > bb_upper_short.iloc[-1]:
            signals.append("🔴 BB_SHORT: Price above upper band (overbought)")
            signal_strength -= 1
            action = "SELL"
        
        # 2. Bollinger Bands (Long-term)
        if current_price < bb_lower_long.iloc[-1]:
            signals.append("🟢 BB_LONG: Price below lower band (strong oversold)")
            signal_strength += 1
        elif current_price > bb_upper_long.iloc[-1]:
            signals.append("🔴 BB_LONG: Price above upper band (strong overbought)")
            signal_strength -= 1
        
        # 3. RSI
        if current_rsi < self.config.RSI_OVERSOLD:
            signals.append(f"🟢 RSI: Oversold ({current_rsi:.1f} < {self.config.RSI_OVERSOLD})")
            signal_strength += 1
        elif current_rsi > self.config.RSI_OVERBOUGHT:
            signals.append(f"🔴 RSI: Overbought ({current_rsi:.1f} > {self.config.RSI_OVERBOUGHT})")
            signal_strength -= 1
        
        # 4. MACD
        if current_macd > current_signal and macd_line.iloc[-2] <= signal_line.iloc[-2]:
            signals.append("🟢 MACD: Bullish crossover")
            signal_strength += 1
        elif current_macd < current_signal and macd_line.iloc[-2] >= signal_line.iloc[-2]:
            signals.append("🔴 MACD: Bearish crossover")
            signal_strength -= 1
        
        # 5. Moving Average Crossovers
        if len(sma_20) > 0 and len(sma_50) > 0:
            if current_price > sma_20.iloc[-1] > sma_50.iloc[-1]:
                signals.append("🟢 MA: Price above SMA(20) and SMA(50) - Uptrend")
                signal_strength += 0.5
            elif current_price < sma_20.iloc[-1] < sma_50.iloc[-1]:
                signals.append("🔴 MA: Price below SMA(20) and SMA(50) - Downtrend")
                signal_strength -= 0.5
        
        # 6. Stochastic Oscillator
        if current_stoch_k < 20:
            signals.append(f"🟢 STOCH: Oversold ({current_stoch_k:.1f})")
            signal_strength += 0.5
        elif current_stoch_k > 80:
            signals.append(f"🔴 STOCH: Overbought ({current_stoch_k:.1f})")
            signal_strength -= 0.5
        
        # Determine final action based on signal strength
        if signal_strength >= self.config.STRONG_SIGNAL_THRESHOLD:
            action = "STRONG BUY"
        elif signal_strength >= 1:
            action = "BUY"
        elif signal_strength <= -self.config.STRONG_SIGNAL_THRESHOLD:
            action = "STRONG SELL"
        elif signal_strength <= -1:
            action = "SELL"
        else:
            action = "HOLD"
        
        # Add volume analysis if available
        if 'Volume' in self.df.columns:
            avg_volume = self.df['Volume'].rolling(20).mean().iloc[-1]
            current_volume = self.df['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio > 1.5:
                signals.append(f"📊 Volume: High ({volume_ratio:.1f}x average)")
            elif volume_ratio < 0.5:
                signals.append(f"📊 Volume: Low ({volume_ratio:.1f}x average)")
        
        # Compile results
        result = {
            'action': action,
            'signal_strength': signal_strength,
            'current_price': current_price,
            'price_change_pct': price_change,
            'indicators': {
                'rsi': current_rsi,
                'macd': current_macd,
                'macd_signal': current_signal,
                'bb_lower_short': bb_lower_short.iloc[-1],
                'bb_upper_short': bb_upper_short.iloc[-1],
                'bb_lower_long': bb_lower_long.iloc[-1],
                'bb_upper_long': bb_upper_long.iloc[-1],
                'atr': current_atr,
                'stoch_k': current_stoch_k,
                'sma_20': sma_20.iloc[-1] if len(sma_20) > 0 else None,
                'sma_50': sma_50.iloc[-1] if len(sma_50) > 0 else None,
                'sma_200': sma_200.iloc[-1] if len(sma_200) > 0 else None,
            },
            'signals': signals
        }
        
        return result

# ═══════════════════════════════════════════════════════════════════
# EMAIL NOTIFICATION WRAPPER
# ═══════════════════════════════════════════════════════════════════

class EmailNotifier:
    """Send email notifications for trading signals."""
    
    def __init__(self, config: Config):
        self.config = config
        
    def send_alert(self, symbol: str, analysis: Dict) -> bool:
        """Send email alert for a trading signal."""
        if not self.config.ENABLE_EMAIL:
            log.info(f"Email disabled. Would send: {symbol} - {analysis['action']}")
            return False
        
        # Only send for actionable signals
        if analysis['action'] == 'HOLD':
            return False
        
        # Check if credentials are set
        if self.config.EMAIL_PROVIDER.lower() == 'sendgrid':
            if not self.config.SENDGRID_API_KEY or not self.config.SENDER_EMAIL:
                log.warning("SendGrid credentials not set. Skipping email.")
                return False
        elif self.config.EMAIL_PROVIDER.lower() == 'hotmail':
            if not self.config.SENDER_EMAIL or not self.config.SENDER_PASSWORD:
                log.warning("Hotmail credentials not set. Skipping email.")
                return False
        
        if not self.config.RECEIVER_EMAIL:
            log.warning("Receiver email not set. Skipping email.")
            return False
        
        # Create HTML body
        html_body = self._create_html_body(symbol, analysis)
        
        # Send using your function
        result = send_email_to_inform(
            symbol=symbol,
            action=analysis['action'],
            text=html_body,
            receiver=self.config.RECEIVER_EMAIL,
            provider=self.config.EMAIL_PROVIDER
        )
        
        return result == 1
    
    def _create_html_body(self, symbol: str, analysis: Dict) -> str:
        """Create HTML email body."""
        action_color = {
            'STRONG BUY': '#00C853',
            'BUY': '#4CAF50',
            'HOLD': '#FFC107',
            'SELL': '#FF5722',
            'STRONG SELL': '#D32F2F'
        }
        
        color = action_color.get(analysis['action'], '#757575')
        
        signals_html = '<ul>' + ''.join([f'<li>{s}</li>' for s in analysis['signals']]) + '</ul>'
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px; }}
                .content {{ padding: 20px; }}
                .indicator {{ background-color: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                td {{ padding: 8px; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{symbol}: {analysis['action']}</h1>
                <h2>Signal Strength: {analysis['signal_strength']:.1f}</h2>
            </div>
            
            <div class="content">
                <h3>💰 Price Info</h3>
                <table>
                    <tr>
                        <td><strong>Current Price:</strong></td>
                        <td>${analysis['current_price']:.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Change:</strong></td>
                        <td>{analysis['price_change_pct']:+.2f}%</td>
                    </tr>
                </table>
                
                <h3>📊 Indicators</h3>
                <table>
                    <tr><td><strong>RSI:</strong></td><td>{analysis['indicators']['rsi']:.1f}</td></tr>
                    <tr><td><strong>MACD:</strong></td><td>{analysis['indicators']['macd']:.2f}</td></tr>
                    <tr><td><strong>Stochastic:</strong></td><td>{analysis['indicators']['stoch_k']:.1f}</td></tr>
                    <tr><td><strong>BB Lower (Short):</strong></td><td>${analysis['indicators']['bb_lower_short']:.2f}</td></tr>
                    <tr><td><strong>BB Upper (Short):</strong></td><td>${analysis['indicators']['bb_upper_short']:.2f}</td></tr>
                </table>
                
                <h3>🎯 Signals Detected</h3>
                {signals_html}
                
                <p><em>Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
            </div>
        </body>
        </html>
        """
        
        return html

# ═══════════════════════════════════════════════════════════════════
# MAIN ANALYZER
# ═══════════════════════════════════════════════════════════════════

class StockAnalyzer:
    """Main stock analysis class."""
    
    def __init__(self, config: Config):
        self.config = config
        self.notifier = EmailNotifier(config)
        
    def fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch stock data from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=self.config.DATA_START_DATE, end=datetime.date.today())
            
            if df.empty:
                log.warning(f"⚠️  No data for {symbol}")
                return None
            
            return df
            
        except Exception as e:
            log.error(f"❌ Error fetching {symbol}: {e}")
            return None
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze a single symbol."""
        log.info(f"📊 Analyzing {symbol}...")
        
        # Fetch data
        df = self.fetch_data(symbol)
        if df is None:
            return None
        
        # Generate signals
        signal_gen = SignalGenerator(df, self.config)
        analysis = signal_gen.analyze()
        
        # Log results
        log.info(f"   {symbol}: {analysis['action']} | "
                   f"Price: ${analysis['current_price']:.2f} ({analysis['price_change_pct']:+.2f}%) | "
                   f"Strength: {analysis['signal_strength']:.1f}")
        
        for signal in analysis['signals']:
            log.info(f"      {signal}")
        
        # Send email if actionable
        if analysis['action'] != 'HOLD':
            log.info(f"   ✉️  Sending email alert for {symbol}...")
            # self.notifier.send_alert(symbol, analysis)
        
        return analysis
    
    def analyze_all(self, symbols: List[str]) -> Dict[str, Dict]:
        """Analyze all symbols."""
        results = {}
        
        log.info(f"\n{'='*70}")
        log.info(f"🚀 Starting analysis of {len(symbols)} symbols")
        log.info(f"{'='*70}\n")
        
        for symbol in tqdm(symbols, desc="Analyzing"):
            results[symbol] = self.analyze_symbol(symbol)
            time.sleep(1)  # Rate limiting
        
        # Summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict[str, Dict]):
        """Print analysis summary."""
        log.info(f"\n{'='*70}")
        log.info("📈 ANALYSIS SUMMARY")
        log.info(f"{'='*70}")
        
        buy_signals = [s for s, r in results.items() if r and 'BUY' in r['action']]
        sell_signals = [s for s, r in results.items() if r and 'SELL' in r['action']]
        hold_signals = [s for s, r in results.items() if r and r['action'] == 'HOLD']
        
        log.info(f"🟢 BUY Signals: {len(buy_signals)}")
        for symbol in buy_signals:
            log.info(f"   {symbol}: {results[symbol]['action']} (Strength: {results[symbol]['signal_strength']:.1f})")
        
        log.info(f"\n🔴 SELL Signals: {len(sell_signals)}")
        for symbol in sell_signals:
            log.info(f"   {symbol}: {results[symbol]['action']} (Strength: {results[symbol]['signal_strength']:.1f})")
        
        log.info(f"\n⚪ HOLD: {len(hold_signals)}")
        
        log.info(f"\n{'='*70}\n")

# ═══════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Advanced Stock Alert System with Multi-Indicator Analysis'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of symbols (e.g., AAPL,TSLA,NVDA)',
        default=None
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run on schedule (every hour)'
    )
    parser.add_argument(
        '--test-email',
        action='store_true',
        help='Send test email and exit'
    )
    parser.add_argument(
        '--provider',
        type=str,
        choices=['sendgrid', 'hotmail'],
        help='Email provider (overrides environment variable)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Initialize config
    config = Config()
    
    # Override provider if specified
    if args.provider:
        config.EMAIL_PROVIDER = args.provider
    
    # Test email
    if args.test_email:
        log.info(f"📧 Testing email via {config.EMAIL_PROVIDER.upper()}...")
        test_html = """
        <html>
        <body>
            <h1 style="color: green;">✅ Test Email</h1>
            <p>If you're reading this, your email configuration is working!</p>
            <p><strong>Provider:</strong> {}</p>
            <p><strong>Timestamp:</strong> {}</p>
        </body>
        </html>
        """.format(config.EMAIL_PROVIDER.upper(), datetime.datetime.now())
        
        result = send_email_to_inform(
            symbol='TEST',
            action='TEST',
            text=test_html,
            receiver=config.RECEIVER_EMAIL,
            provider=config.EMAIL_PROVIDER
        )
        
        if result == 1:
            log.info("✅ Test email sent successfully!")
        else:
            log.error("❌ Test email failed. Check your credentials.")
        return
    
    # Use custom symbols or defaults
    symbols = args.symbols.split(',') if args.symbols else config.STOCKS_TO_TRACK
    
    # Initialize analyzer
    analyzer = StockAnalyzer(config)
    
    # Run analysis
    def run_analysis():
        log.info(f"\n🕐 Analysis started at {datetime.datetime.now()}")
        results =  analyzer.analyze_all(symbols)
        html_content, text_summary = generate_report_content(results)
        receiver_email = config.RECEIVER_EMAIL
        send_email_to_inform( symbol="listAllSymbols", action="Summary", text=html_content, receiver=receiver_email)
            
        if config.ENABLE_HTML_OUTPUT:
            filename = "output_page.html"

            # Open the file and write the content
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"HTML content saved successfully to {filename}")

        breakpoint()
        log.info(f"✅ Analysis complete\n")
    
    if args.schedule:
        # Run on schedule
        log.info(f"⏰ Scheduling analysis every {config.CHECK_INTERVAL_HOURS} hour(s)")
        schedule.every(config.CHECK_INTERVAL_HOURS).hours.do(run_analysis)
        
        # Run once immediately
        run_analysis()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Run once
        run_analysis()

if __name__ == "__main__":
    main()