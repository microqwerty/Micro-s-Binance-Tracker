import os
import json
import time
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
import logging
from datetime import datetime, timedelta
import random
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Try different import paths for BinanceSocketManager based on package version
try:
    # For newer versions of python-binance (v1.0.0+)
    from binance.websocket.spot.websocket_client import SpotWebsocketClient as BinanceSocketManager
except ImportError:
    try:
        # For python-binance intermediate versions
        from binance.streams import BinanceSocketManager
    except ImportError:
        try:
            # For versions that use streams module
            from binance.streams import BinanceSocketManager
        except ImportError:
            try:
                # For older versions of python-binance
                from binance.websocket.spot.websocket_client import SpotWebsocketClient as BinanceSocketManager
            except ImportError:
                # Fallback if websocket functionality is not available
                class BinanceSocketManager:
                    """Fallback implementation if BinanceSocketManager is not available."""
                    
                    def __init__(self, client):
                        self.client = client
                        print("Warning: WebSocket functionality is not available. Using polling instead.")
                        
                    def start(self):
                        pass
                        
                    def start_symbol_ticker_socket(self, symbol, callback):
                        return f"fallback-{symbol}"
                        
                    def stop_socket(self, conn_key):
                        pass
                        
                    def close(self):
                        pass

# Try to import DepthCacheManager if available
try:
    from binance.depthcache import DepthCacheManager
except ImportError:
    # Define dummy class if not available
    class DepthCacheManager:
        """Fallback implementation if DepthCacheManager is not available."""
        def __init__(self, client, symbol, callback=None):
            self.client = client
            print("Warning: DepthCacheManager functionality is not available.")

class BinanceApiClient:
    """
    Wrapper for the Binance API client with read-only operations.
    Handles account data, market data, and WebSocket connections.
    """
    
    # Path to manual data file
    MANUAL_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manual_data.json")
    
    # Path to user preferences file
    PREFERENCES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "preferences.json")
    
    # Binance API base endpoints
    API_BASE_URL = "https://api.binance.com"
    API_BASE_URL_ALTERNATIVE = "https://api-gcp.binance.com"
    WEBSOCKET_BASE_URL = "wss://ws-api.binance.com:443/ws-api/v3"
    WEBSOCKET_BASE_URL_ALTERNATIVE = "wss://ws-api.binance.com:9443/ws-api/v3"
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the Binance API client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
        """
        # Initialize client with optional timeout setting for better reliability
        self.client = Client(api_key, api_secret, requests_params={'timeout': 30})
        self.socket_manager = None
        self.socket_connections = {}
        self.price_callbacks = {}
        self._ws_thread = None
        
        # Manual data
        self.manual_orders = {}  # Symbol -> List[Order]
        self.symbol_mappings = {}  # Invalid symbol -> Valid symbol
        
        # User preferences
        self.preferences = {
            'preferred_pairs': {}  # Asset -> Preferred pair
        }
        
        # Rate limit tracking
        self.request_weights = {}  # Endpoint -> (weight, timestamp)
        self.last_used_weight = 0
        self.weight_usage_timestamp = time.time()
        self.last_response_headers = {}
        
        # Cache for frequently accessed data
        self.exchange_info_cache = None
        self.exchange_info_timestamp = 0
        self.ticker_cache = {}
        self.fee_rates = {
            'maker': 0.001,  # Default maker fee (0.1%)
            'taker': 0.001   # Default taker fee (0.1%)
        }
        
        # Load manual data and preferences
        self._load_manual_data()
        self._load_preferences()
        
        # Try to get actual fee rates
        try:
            self._update_fee_rates()
        except Exception as e:
            logging.warning(f"Could not get fee rates: {e}")
        
    def _update_fee_rates(self) -> None:
        """
        Update fee rates from account information.
        """
        try:
            # Try to get trading fee rates
            trading_fees = self.client.get_trade_fee()
            if trading_fees and 'tradeFee' in trading_fees:
                for fee_info in trading_fees['tradeFee']:
                    if fee_info['symbol'] == '':  # Default fees
                        self.fee_rates = {
                            'maker': float(fee_info['maker']),
                            'taker': float(fee_info['taker'])
                        }
                        break
        except Exception as e:
            # If get_trade_fee not available, try account info
            logging.debug(f"Could not get fee rates from trade_fee: {e}")
            try:
                account_info = self.get_account_info()
                # Look for commission rates if available in account info
                if 'commissionRates' in account_info:
                    self.fee_rates = {
                        'maker': float(account_info['commissionRates']['maker']),
                        'taker': float(account_info['commissionRates']['taker'])
                    }
            except Exception as e2:
                logging.debug(f"Could not get fee rates from account info: {e2}")
                # Keep default values
                pass
                
    def _handle_api_response(self, response_headers: dict) -> None:
        """
        Handle API response headers to track rate limits.
        
        Args:
            response_headers: Response headers from API request
        """
        if not response_headers:
            return
            
        # Store last response headers
        self.last_response_headers = response_headers
        
        # Track weight usage if available
        if 'x-mbx-used-weight' in response_headers:
            self.last_used_weight = int(response_headers['x-mbx-used-weight'])
            self.weight_usage_timestamp = time.time()
            
        # Track order count if available
        if 'x-mbx-order-count' in response_headers:
            self.last_order_count = int(response_headers['x-mbx-order-count'])
    
    def get_account_info(self) -> Dict:
        """
        Get account information including balances.
        
        Returns:
            Account information dictionary
        """
        try:
            response = self.client.get_account()
            # Handle rate limit tracking
            self._handle_api_response(self.client.response.headers)
            return response
        except BinanceAPIException as e:
            if e.code == -1010:  # IP is banned
                logging.error(f"IP banned due to rate limit violation: {e}")
                # Implement exponential backoff or notify user
                raise
            elif e.code == -1015:  # Too many requests
                logging.warning(f"Rate limit exceeded: {e}")
                # Implement exponential backoff
                wait_time = 30 + random.randint(1, 30)  # 30-60 seconds with jitter
                logging.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                return self.get_account_info()  # Retry
            else:
                raise
    
    def get_spot_balances(self, min_value: float = 0.0) -> List[Dict]:
        """
        Get non-zero spot balances.
        
        Args:
            min_value: Minimum USD value to include (default: 0.0)
            
        Returns:
            List of balance dictionaries with additional price info
        """
        try:
            account = self.get_account_info()  # Using our wrapped method to track rate limits
            balances = []
            
            # List of stablecoins with 1:1 USD peg (approximately)
            stablecoins = ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'USDP', 'FDUSD', 'USDK']
            
            # Get all tickers for price info more efficiently with ticker/price endpoint
            try:
                ticker_prices = self.client.get_symbol_ticker()
                prices = {ticker['symbol']: float(ticker['price']) for ticker in ticker_prices}
                # Handle rate limit tracking
                self._handle_api_response(self.client.response.headers)
            except BinanceAPIException as e:
                if e.code == -1010 or e.code == -1015:  # IP banned or too many requests
                    # Fallback to individual price checks as needed (less efficient)
                    logging.warning(f"Rate limit issue when getting all tickers: {e}")
                    prices = {}
                else:
                    raise
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                # Skip zero balances
                if total <= 0:
                    continue
                    
                # Calculate USD value
                usd_value = 0
                
                # Check if asset is a stablecoin
                if asset in stablecoins:
                    usd_value = total
                else:
                    # Try different quote assets in priority order
                    for quote in ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']:
                        symbol = f"{asset}{quote}"
                        if symbol in prices:
                            if quote in stablecoins:
                                # Direct conversion to USD
                                usd_value = total * prices[symbol]
                            elif quote == 'BTC' and 'BTCUSDT' in prices:
                                # Convert through BTC
                                btc_value = total * prices[symbol]
                                usd_value = btc_value * prices['BTCUSDT']
                            elif quote == 'ETH' and 'ETHUSDT' in prices:
                                # Convert through ETH
                                eth_value = total * prices[symbol]
                                usd_value = eth_value * prices['ETHUSDT']
                            break
                
                # Skip if below minimum value
                if usd_value < min_value:
                    continue
                    
                # Check if we have a preferred trading pair
                preferred_pair = self.get_preferred_pair(asset)
                
                balances.append({
                    'asset': asset,
                    'free': free,
                    'locked': locked,
                    'total': total,
                    'usd_value': usd_value,
                    'preferred_pair': preferred_pair
                })
                
            # Sort by USD value (descending)
            return sorted(balances, key=lambda x: x['usd_value'], reverse=True)
            
        except BinanceAPIException as e:
            if e.code == -1010:  # IP is banned
                logging.error(f"IP banned due to rate limit violation: {e}")
                # Return empty list or notify user
                return []
            elif e.code == -1015:  # Too many requests
                logging.warning(f"Rate limit exceeded: {e}")
                # Implement exponential backoff
                wait_time = 30 + random.randint(1, 30)  # 30-60 seconds with jitter
                logging.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                return self.get_spot_balances(min_value)  # Retry
            else:
                logging.error(f"Error getting balances: {e}")
                return []
    
    def get_symbol_price(self, symbol: str, use_cache: bool = True) -> float:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            use_cache: Whether to use cached price data if available
            
        Returns:
            Current price as float
        """
        # Check cache first if enabled
        if use_cache and symbol in self.ticker_cache:
            cache_time, price = self.ticker_cache[symbol]
            # Use cache if it's less than 5 seconds old
            if time.time() - cache_time < 5:
                return price
                
        try:
            # First try the ticker price endpoint (most efficient)
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            # Handle rate limit tracking
            self._handle_api_response(self.client.response.headers)
            price = float(ticker['price'])
            
            # Update cache
            self.ticker_cache[symbol] = (time.time(), price)
            return price
            
        except BinanceAPIException as e:
            # Handle different error codes
            if e.code == -1121:  # Invalid symbol
                # Check if we have a mapped symbol
                mapped_symbol = self.get_mapped_symbol(symbol)
                if mapped_symbol != symbol:
                    # Try with the mapped symbol
                    return self.get_symbol_price(mapped_symbol, use_cache)
                    
                # Try multiple fallback methods in sequence
                fallback_methods = [
                    # Try newer tickerPrice endpoint
                    lambda: float(self.client.get_ticker_price(symbol=symbol)['price']),
                    # Try 24hr ticker endpoint
                    lambda: float(self.client.get_ticker(symbol=symbol)['lastPrice']),
                    # Try average price endpoint
                    lambda: float(self.client.get_avg_price(symbol=symbol)['price']),
                    # Try recent trades
                    lambda: float(self.client.get_recent_trades(symbol=symbol, limit=1)[0]['price']),
                    # Try klines (candlestick) data
                    lambda: float(self.client.get_klines(symbol=symbol, interval=self.client.KLINE_INTERVAL_1MINUTE, limit=1)[0][4])
                ]
                
                # Try each fallback method
                for method in fallback_methods:
                    try:
                        price = method()
                        # Update cache if successful
                        self.ticker_cache[symbol] = (time.time(), price)
                        return price
                    except Exception as fallback_error:
                        logging.debug(f"Fallback method failed for {symbol}: {fallback_error}")
                        continue
                
                # If all fallbacks fail, raise the original error
                raise e
                
            elif e.code == -1015:  # Too many requests
                logging.warning(f"Rate limit exceeded when getting price for {symbol}: {e}")
                # Use cached price if available
                if symbol in self.ticker_cache:
                    logging.warning(f"Using cached price for {symbol} due to rate limit")
                    return self.ticker_cache[symbol][1]
                    
                # Implement exponential backoff
                wait_time = 10 + random.randint(1, 20)  # 10-30 seconds with jitter
                logging.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                return self.get_symbol_price(symbol, use_cache)  # Retry
                
            elif e.code == -1010:  # IP banned
                logging.error(f"IP banned when getting price for {symbol}: {e}")
                # Use cached price if available
                if symbol in self.ticker_cache:
                    logging.warning(f"Using cached price for {symbol} due to IP ban")
                    return self.ticker_cache[symbol][1]
                raise
                
            else:
                # For other errors, try to use cache if available
                if symbol in self.ticker_cache:
                    logging.warning(f"Using cached price for {symbol} due to error: {e}")
                    return self.ticker_cache[symbol][1]
                # Otherwise raise the error
                raise
    
    def get_consolidated_order_history(self, asset: str, base_currency: str = 'USDT') -> List[Dict]:
        """
        Get consolidated order history for an asset across all trading pairs.
        
        Args:
            asset: Asset name (e.g., 'BTC')
            base_currency: Currency to normalize values to (default: 'USDT')
            
        Returns:
            List of normalized order dictionaries
        """
        # Get all trading pairs for this asset
        all_pairs = []
        
        # Try different quote assets in priority order
        for quote in ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']:
            pair = f"{asset}{quote}"
            # Check if this pair exists (either in manual orders or via API)
            has_orders = False
            try:
                # Try to get a single order to check if pair exists
                orders = self.client.get_all_orders(symbol=pair, limit=1)
                if orders:
                    has_orders = True
            except BinanceAPIException:
                # Check manual orders
                if pair in self.manual_orders and self.manual_orders[pair]:
                    has_orders = True
            
            if has_orders:
                all_pairs.append(pair)
        
        # Also check symbol mappings for additional pairs
        for invalid_symbol, valid_symbol in self.symbol_mappings.items():
            if invalid_symbol.startswith(asset) and valid_symbol not in all_pairs:
                all_pairs.append(valid_symbol)
        
        # Get orders for all pairs
        all_orders = []
        for pair in all_pairs:
            orders = self.get_order_history(pair)
            
            # Add pair info to each order
            for order in orders:
                # Extract quote asset from symbol
                quote_asset = pair[len(asset):]
                order['baseAsset'] = asset
                order['quoteAsset'] = quote_asset
                order['originalSymbol'] = pair
                
                # Normalize price to base currency if needed
                if quote_asset != base_currency:
                    # Get conversion rate at time of order
                    try:
                        # For simplicity, we use current conversion rate
                        # In a production app, you'd want to get historical rates
                        if quote_asset == 'BTC':
                            btc_price = self.get_symbol_price(f"BTC{base_currency}")
                            normalized_price = order['price'] * btc_price
                            normalized_total = order['cummulativeQuoteQty'] * btc_price
                        elif quote_asset == 'ETH':
                            eth_price = self.get_symbol_price(f"ETH{base_currency}")
                            normalized_price = order['price'] * eth_price
                            normalized_total = order['cummulativeQuoteQty'] * eth_price
                        else:
                            # Direct conversion if available
                            conversion_pair = f"{quote_asset}{base_currency}"
                            try:
                                conversion_rate = self.get_symbol_price(conversion_pair)
                                normalized_price = order['price'] * conversion_rate
                                normalized_total = order['cummulativeQuoteQty'] * conversion_rate
                            except:
                                # If direct conversion not available, try reverse
                                conversion_pair = f"{base_currency}{quote_asset}"
                                try:
                                    conversion_rate = 1 / self.get_symbol_price(conversion_pair)
                                    normalized_price = order['price'] * conversion_rate
                                    normalized_total = order['cummulativeQuoteQty'] * conversion_rate
                                except:
                                    # If all else fails, leave as is
                                    normalized_price = order['price']
                                    normalized_total = order['cummulativeQuoteQty']
                        
                        # Add normalized values
                        order['normalizedPrice'] = normalized_price
                        order['normalizedTotal'] = normalized_total
                        order['baseCurrency'] = base_currency
                    except Exception as e:
                        logging.warning(f"Could not normalize price for {pair}: {e}")
                        # Use original values
                        order['normalizedPrice'] = order['price']
                        order['normalizedTotal'] = order['cummulativeQuoteQty']
                        order['baseCurrency'] = quote_asset
                else:
                    # Already in base currency
                    order['normalizedPrice'] = order['price']
                    order['normalizedTotal'] = order['cummulativeQuoteQty']
                    order['baseCurrency'] = base_currency
            
            all_orders.extend(orders)
        
        # Sort by time (newest first)
        all_orders.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        return all_orders
    
    def get_consolidated_order_history(self, asset: str, base_currency: str = 'USDT') -> List[Dict]:
        """
        Get consolidated order history for an asset across all trading pairs.
        
        Args:
            asset: Asset name (e.g., 'BTC')
            base_currency: Currency to normalize values to (default: 'USDT')
            
        Returns:
            List of normalized order dictionaries
        """
        # Get all trading pairs for this asset
        all_pairs = []
        
        # Try different quote assets in priority order
        for quote in ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']:
            pair = f"{asset}{quote}"
            # Check if this pair exists (either in manual orders or via API)
            has_orders = False
            try:
                # Try to get a single order to check if pair exists
                orders = self.client.get_all_orders(symbol=pair, limit=1)
                if orders:
                    has_orders = True
            except Exception:
                # Check manual orders
                if pair in self.manual_orders and self.manual_orders[pair]:
                    has_orders = True
            
            if has_orders:
                all_pairs.append(pair)
        
        # Also check symbol mappings for additional pairs
        for invalid_symbol, valid_symbol in self.symbol_mappings.items():
            if invalid_symbol.startswith(asset) and valid_symbol not in all_pairs:
                all_pairs.append(valid_symbol)
        
        # Get orders for all pairs
        all_orders = []
        for pair in all_pairs:
            orders = self.get_order_history(pair)
            
            # Add pair info to each order
            for order in orders:
                # Extract quote asset from symbol
                quote_asset = pair[len(asset):]
                order['baseAsset'] = asset
                order['quoteAsset'] = quote_asset
                order['originalSymbol'] = pair
                
                # Normalize price to base currency if needed
                if quote_asset != base_currency:
                    # Get conversion rate at time of order
                    try:
                        # For simplicity, we use current conversion rate
                        # In a production app, you'd want to get historical rates
                        if quote_asset == 'BTC':
                            btc_price = self.get_symbol_price(f"BTC{base_currency}")
                            normalized_price = order['price'] * btc_price
                            normalized_total = order['cummulativeQuoteQty'] * btc_price
                        elif quote_asset == 'ETH':
                            eth_price = self.get_symbol_price(f"ETH{base_currency}")
                            normalized_price = order['price'] * eth_price
                            normalized_total = order['cummulativeQuoteQty'] * eth_price
                        else:
                            # Direct conversion if available
                            conversion_pair = f"{quote_asset}{base_currency}"
                            try:
                                conversion_rate = self.get_symbol_price(conversion_pair)
                                normalized_price = order['price'] * conversion_rate
                                normalized_total = order['cummulativeQuoteQty'] * conversion_rate
                            except:
                                # If direct conversion not available, try reverse
                                conversion_pair = f"{base_currency}{quote_asset}"
                                try:
                                    conversion_rate = 1 / self.get_symbol_price(conversion_pair)
                                    normalized_price = order['price'] * conversion_rate
                                    normalized_total = order['cummulativeQuoteQty'] * conversion_rate
                                except:
                                    # If all else fails, leave as is
                                    normalized_price = order['price']
                                    normalized_total = order['cummulativeQuoteQty']
                        
                        # Add normalized values
                        order['normalizedPrice'] = normalized_price
                        order['normalizedTotal'] = normalized_total
                        order['baseCurrency'] = base_currency
                    except Exception as e:
                        print(f"Could not normalize price for {pair}: {e}")
                        # Use original values
                        order['normalizedPrice'] = order['price']
                        order['normalizedTotal'] = order['cummulativeQuoteQty']
                        order['baseCurrency'] = quote_asset
                else:
                    # Already in base currency
                    order['normalizedPrice'] = order['price']
                    order['normalizedTotal'] = order['cummulativeQuoteQty']
                    order['baseCurrency'] = base_currency
            
            all_orders.extend(orders)
        
        # Sort by time (newest first)
        all_orders.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        return all_orders
    
    def get_order_history(self, symbol: str) -> List[Dict]:
        """
        Get order history for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            List of order dictionaries
        """
        # Check if we have manual orders for this symbol
        manual_orders = self.get_manual_orders(symbol)
        
        # Check if we have a symbol mapping
        mapped_symbol = self.get_mapped_symbol(symbol)
        
        try:
            # Get all orders (including filled, canceled, etc.)
            if mapped_symbol != symbol:
                print(f"Using mapped symbol {mapped_symbol} instead of {symbol}")
                orders = self.client.get_all_orders(symbol=mapped_symbol)
            else:
                orders = self.client.get_all_orders(symbol=symbol)
            
            # Filter to only include filled orders
            filled_orders = [order for order in orders if order['status'] == 'FILLED']
            
            # Add additional calculated fields
            for order in filled_orders:
                order['price'] = float(order['price'])
                order['origQty'] = float(order['origQty'])
                order['executedQty'] = float(order['executedQty'])
                order['cummulativeQuoteQty'] = float(order['cummulativeQuoteQty'])
                
                # Calculate actual execution price (might differ from order price)
                if order['executedQty'] > 0:
                    order['avgPrice'] = order['cummulativeQuoteQty'] / order['executedQty']
                else:
                    order['avgPrice'] = 0
                    
                # Convert timestamp to readable format
                order['time'] = time.strftime('%Y-%m-%d %H:%M:%S',
                                             time.localtime(order['time'] / 1000))
                
                # Mark as API order
                order['isManual'] = False
            
            # Combine with manual orders
            all_orders = filled_orders + manual_orders
            
            # Sort by time (newest first)
            all_orders.sort(key=lambda x: x.get('time', ''), reverse=True)
            
            return all_orders
            
        except BinanceAPIException as e:
            print(f"Error getting order history: {e}")
            
            # If it's an invalid symbol error, return only manual orders
            if e.code == -1121 and manual_orders:  # Invalid symbol
                print(f"Using only manual orders for {symbol}")
                return manual_orders
                
            # If we have a symbol mapping but still got an error, try to prompt for a new mapping
            if mapped_symbol != symbol:
                print(f"Mapped symbol {mapped_symbol} also failed")
                
            # Return empty list if no manual orders
            return manual_orders if manual_orders else []
    
    def get_open_orders(self, symbol: str) -> List[Dict]:
        """
        Get open orders for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            List of open order dictionaries
        """
        # Check if we have a symbol mapping
        mapped_symbol = self.get_mapped_symbol(symbol)
        
        try:
            # Get open orders
            if mapped_symbol != symbol:
                print(f"Using mapped symbol {mapped_symbol} instead of {symbol}")
                open_orders = self.client.get_open_orders(symbol=mapped_symbol)
            else:
                open_orders = self.client.get_open_orders(symbol=symbol)
            
            # Add additional calculated fields
            for order in open_orders:
                order['price'] = float(order['price'])
                order['origQty'] = float(order['origQty'])
                order['executedQty'] = float(order['executedQty'])
                
                # Calculate locked amount (remaining to be executed)
                order['lockedQty'] = order['origQty'] - order['executedQty']
                
                # Convert timestamp to readable format
                order['time'] = time.strftime('%Y-%m-%d %H:%M:%S',
                                             time.localtime(order['time'] / 1000))
            
            return open_orders
            
        except BinanceAPIException as e:
            print(f"Error getting open orders: {e}")
            
            # If it's an invalid symbol error, return empty list
            if e.code == -1121:  # Invalid symbol
                print(f"Symbol {symbol} not found in API. Cannot get open orders.")
                return []
                
            # Re-raise other API errors
            raise
    
    def calculate_consolidated_position_metrics(self, asset: str, base_currency: str = 'USDT') -> Dict:
        """
        Calculate position metrics for an asset across all trading pairs.
        
        Args:
            asset: Asset name (e.g., 'BTC')
            base_currency: Currency to normalize values to (default: 'USDT')
            
        Returns:
            Dictionary with consolidated position metrics
        """
        try:
            # Get consolidated order history
            all_orders = self.get_consolidated_order_history(asset, base_currency)
            
            # Calculate metrics
            total_qty = 0
            total_cost = 0
            total_fees = 0
            
            # Process orders
            for order in all_orders:
                side = order['side']
                qty = float(order['executedQty'])
                
                # Use normalized values
                if 'normalizedTotal' in order:
                    cost = float(order['normalizedTotal'])
                else:
                    cost = float(order['cummulativeQuoteQty'])
                
                # Estimate fees (0.1% standard fee or use actual if available)
                fee = cost * self.fee_rates['taker'] if side == 'BUY' else cost * self.fee_rates['maker']
                if 'commission' in order:
                    fee = float(order['commission'])
                total_fees += fee
                
                if side == 'BUY':
                    total_cost += cost
                    total_qty += qty
                elif side == 'SELL':
                    total_cost -= cost
                    total_qty -= qty
            
            # Get current price in base currency
            try:
                current_price = self.get_symbol_price(f"{asset}{base_currency}")
            except:
                # If direct price not available, try to find through BTC
                try:
                    btc_price = self.get_symbol_price(f"BTC{base_currency}")
                    asset_btc_price = self.get_symbol_price(f"{asset}BTC")
                    current_price = asset_btc_price * btc_price
                except:
                    # If still not available, use last known price
                    if all_orders:
                        current_price = all_orders[0].get('normalizedPrice', 0)
                    else:
                        current_price = 0
            
            # Calculate metrics
            avg_buy_price = total_cost / total_qty if total_qty > 0 else 0
            break_even_price = (total_cost + total_fees) / total_qty if total_qty > 0 else 0
            current_value = total_qty * current_price
            pnl_amount = current_value - total_cost
            pnl_percent = (pnl_amount / total_cost) * 100 if total_cost > 0 else 0
            
            # Get trading pairs used
            trading_pairs = list(set([order.get('originalSymbol', '') for order in all_orders]))
            
            return {
                'asset': asset,
                'baseCurrency': base_currency,
                'current_price': current_price,
                'holdings': total_qty,
                'avg_buy_price': avg_buy_price,
                'break_even_price': break_even_price,
                'total_cost': total_cost,
                'current_value': current_value,
                'pnl_amount': pnl_amount,
                'pnl_percent': pnl_percent,
                'trading_pairs': trading_pairs,
                'order_count': len(all_orders)
            }
        except Exception as e:
            logging.error(f"Error calculating consolidated position metrics: {e}")
            return {
                'asset': asset,
                'baseCurrency': base_currency,
                'current_price': 0,
                'holdings': 0,
                'avg_buy_price': 0,
                'break_even_price': 0,
                'total_cost': 0,
                'current_value': 0,
                'pnl_amount': 0,
                'pnl_percent': 0,
                'trading_pairs': [],
                'order_count': 0,
                'error': str(e)
            }
    
    def calculate_position_metrics(self, symbol: str, include_orders: Optional[List[int]] = None,
                                  manual_price: Optional[float] = None, manual_orders: Optional[List[Dict]] = None) -> Dict:
        """
        Calculate position metrics including average buy price, break-even, and PnL.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            include_orders: Optional list of order IDs to include in calculation
            manual_price: Optional manually provided current price (for symbols not available via API)
            manual_orders: Optional list of manually added orders (for symbols not available via API)
            
        Returns:
            Dictionary with position metrics
        """
        try:
            # Initialize variables
            total_cost = 0
            total_qty = 0
            total_fees = 0
            orders = []
            open_orders = []
            locked_qty = 0
            current_price = 0
            is_manual = False
            
            # Try to get orders from API if manual_orders not provided
            if not manual_orders:
                try:
                    # Get order history (this will include both API and manual orders)
                    orders = self.get_order_history(symbol)
                    
                    # Check if these are only manual orders
                    if all(order.get('isManual', False) for order in orders):
                        is_manual = True
                except BinanceAPIException as api_error:
                    # Handle invalid symbol error
                    if api_error.code == -1121:  # Invalid symbol
                        print(f"Symbol {symbol} not found in API. Using manual orders only.")
                        orders = self.get_manual_orders(symbol)
                        is_manual = True
                    else:
                        # Re-raise other API errors
                        raise
            else:
                # Use provided manual orders
                orders = manual_orders
                is_manual = True
            
            # Get open orders to calculate locked amounts
            try:
                open_orders = self.get_open_orders(symbol)
                
                # Calculate total locked quantity
                for order in open_orders:
                    if order['side'] == 'BUY':
                        # For buy orders, the quote asset (e.g., USDT) is locked
                        pass  # We don't track locked quote assets
                    elif order['side'] == 'SELL':
                        # For sell orders, the base asset (e.g., BTC) is locked
                        locked_qty += order['lockedQty']
            except Exception as e:
                print(f"Error getting open orders: {e}")
                open_orders = []
            
            # Filter orders if include_orders is provided
            if include_orders is not None:
                orders = [order for order in orders if order['orderId'] in include_orders]
            
            # Calculate total cost and quantity
            for order in orders:
                side = order['side']
                qty = float(order['executedQty'])
                cost = float(order['cummulativeQuoteQty'])
                
                # Estimate fees (0.1% standard fee)
                fee = cost * 0.001
                total_fees += fee
                
                if side == 'BUY':
                    total_cost += cost
                    total_qty += qty
                elif side == 'SELL':
                    total_cost -= cost
                    total_qty -= qty
            
            # Get current price (from API or manual input)
            if manual_price is not None:
                current_price = manual_price
            else:
                try:
                    # Check if we have a symbol mapping
                    mapped_symbol = self.get_mapped_symbol(symbol)
                    
                    if mapped_symbol != symbol:
                        print(f"Using mapped symbol {mapped_symbol} for price")
                        current_price = self.get_symbol_price(mapped_symbol)
                    else:
                        current_price = self.get_symbol_price(symbol)
                except BinanceAPIException as api_error:
                    # Handle invalid symbol error
                    if api_error.code == -1121:  # Invalid symbol
                        print(f"Symbol {symbol} not found in API. Cannot get current price.")
                        current_price = 0
                    else:
                        # Re-raise other API errors
                        raise
            
            # Calculate metrics
            avg_buy_price = total_cost / total_qty if total_qty > 0 else 0
            break_even_price = (total_cost + total_fees) / total_qty if total_qty > 0 else 0
            current_value = total_qty * current_price
            pnl_amount = current_value - total_cost
            pnl_percent = (pnl_amount / total_cost) * 100 if total_cost > 0 else 0
            
            # Calculate available and locked amounts
            available_qty = total_qty - locked_qty
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'holdings': total_qty,
                'available': available_qty,
                'locked': locked_qty,
                'open_orders': open_orders,
                'avg_buy_price': avg_buy_price,
                'break_even_price': break_even_price,
                'total_cost': total_cost,
                'current_value': current_value,
                'pnl_amount': pnl_amount,
                'pnl_percent': pnl_percent,
                'is_manual': is_manual or manual_price is not None or manual_orders is not None,
                'mapped_symbol': self.get_mapped_symbol(symbol) if self.get_mapped_symbol(symbol) != symbol else None
            }
        except Exception as e:
            print(f"Error calculating position metrics: {e}")
            return {
                'symbol': symbol,
                'current_price': 0,
                'holdings': 0,
                'available': 0,
                'locked': 0,
                'open_orders': [],
                'avg_buy_price': 0,
                'break_even_price': 0,
                'total_cost': 0,
                'current_value': 0,
                'pnl_amount': 0,
                'pnl_percent': 0,
                'is_manual': False,
                'error': str(e)
            }
    
    def start_symbol_ticker_websocket(self, symbol: str, callback: Callable[[Dict], Any]) -> str:
        """
        Start a WebSocket connection for symbol ticker updates.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            callback: Callback function to handle ticker updates
            
        Returns:
            WebSocket connection key
        """
        try:
            if self.socket_manager is None:
                # Try to use newer WebSocket API if available
                try:
                    # Check which websocket client is available
                    if 'SpotWebsocketClient' in globals():
                        self.socket_manager = BinanceSocketManager(
                            stream_url=self.WEBSOCKET_BASE_URL,
                            on_message=lambda msg: self._process_websocket_message(msg)
                        )
                        logging.info("Using SpotWebsocketClient for WebSocket connection")
                    else:
                        # Fall back to older BinanceSocketManager
                        self.socket_manager = BinanceSocketManager(self.client)
                        logging.info("Using BinanceSocketManager for WebSocket connection")
                except Exception as e:
                    logging.warning(f"Error initializing WebSocket client: {e}")
                    # Create fallback manager
                    self.socket_manager = BinanceSocketManager(self.client)
                    logging.info("Using fallback BinanceSocketManager for WebSocket connection")
                
                # Start WebSocket in a separate thread
                def run_socket():
                    try:
                        # Check which client we're using
                        if hasattr(self.socket_manager, 'connect'):
                            self.socket_manager.connect()
                        elif hasattr(self.socket_manager, 'start_socket'):
                            self.socket_manager.start()
                        else:
                            raise ValueError("Unknown WebSocket client interface")
                    except Exception as e:
                        logging.error(f"Error starting WebSocket: {e}")
                        # Fall back to polling
                        self._start_polling(symbol, callback)
                    
                self._ws_thread = threading.Thread(target=run_socket)
                self._ws_thread.daemon = True
                self._ws_thread.start()
                
                # Wait for connection to establish
                time.sleep(1)
            
            # Store callback
            self.price_callbacks[symbol] = callback
            
            # Process ticker data
            def process_ticker(msg):
                try:
                    # Handle different message formats
                    if isinstance(msg, dict):
                        if msg.get('e') == 'error':
                            logging.error(f"WebSocket error: {msg}")
                            return
                            
                        if msg.get('e') == '24hrTicker':
                            price = float(msg['c'])
                            callback({'symbol': symbol, 'price': price})
                        elif msg.get('data') and msg.get('data', {}).get('c'):
                            # New WebSocket API format
                            price = float(msg['data']['c'])
                            callback({'symbol': symbol, 'price': price})
                    else:
                        # Try to parse as JSON if it's a string
                        if isinstance(msg, str):
                            try:
                                import json
                                data = json.loads(msg)
                                if 'c' in data:
                                    price = float(data['c'])
                                    callback({'symbol': symbol, 'price': price})
                                    return
                            except:
                                pass
                                
                        logging.warning(f"Received message in unknown format: {msg}")
                except Exception as e:
                    logging.error(f"Error processing ticker data: {e}")
            
            # Start the WebSocket connection
            try:
                # Determine which client we're using and how to connect
                if hasattr(self.socket_manager, 'symbol_ticker'):
                    # New client
                    conn_key = f"ticker_{symbol}"
                    self.socket_manager.symbol_ticker(
                        symbol=symbol,
                        callback=process_ticker
                    )
                elif hasattr(self.socket_manager, 'start_symbol_ticker_socket'):
                    # Old client
                    conn_key = self.socket_manager.start_symbol_ticker_socket(symbol, process_ticker)
                elif hasattr(self.socket_manager, 'ticker'):
                    # SpotWebsocketClient
                    conn_key = f"ticker_{symbol}"
                    self.socket_manager.ticker(
                        symbol=symbol,
                        id=conn_key,
                        callback=process_ticker
                    )
                else:
                    raise ValueError("Could not find appropriate WebSocket method")
                
                self.socket_connections[symbol] = conn_key
                logging.info(f"Started WebSocket connection for {symbol}")
                return conn_key
            
            except Exception as e:
                logging.error(f"Error starting ticker socket: {e}")
                # Fall back to polling
                return self._start_polling(symbol, callback)
                
        except Exception as e:
            logging.error(f"Error in WebSocket setup: {e}")
            # Fall back to polling
            return self._start_polling(symbol, callback)
            
    def _process_websocket_message(self, msg):
        """
        Process messages from WebSocket connections.
        
        Args:
            msg: Message received from WebSocket
        """
        try:
            # If it's a string, parse it
            if isinstance(msg, str):
                try:
                    import json
                    msg = json.loads(msg)
                except:
                    logging.error(f"Error parsing WebSocket message: {msg}")
                    return
            
            # Check message type
            if isinstance(msg, dict):
                # Extract symbol and process message based on type
                stream = msg.get('stream', '')
                if 'ticker@' in stream:
                    parts = stream.split('@')[0].split('_')
                    symbol = parts[-1].upper()
                    if symbol in self.price_callbacks:
                        # Extract price based on message format
                        if 'data' in msg and 'c' in msg['data']:
                            price = float(msg['data']['c'])
                        elif 'c' in msg:
                            price = float(msg['c'])
                        else:
                            logging.warning(f"Could not extract price from message: {msg}")
                            return
                            
                        # Call the registered callback
                        self.price_callbacks[symbol]({'symbol': symbol, 'price': price})
        
        except Exception as e:
            logging.error(f"Error processing WebSocket message: {e}")
    
    def _start_polling(self, symbol: str, callback: Callable[[Dict], Any]) -> str:
        """
        Start polling for price updates as a fallback when WebSockets fail.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            callback: Callback function to handle price updates
            
        Returns:
            Polling identifier
        """
        poll_id = f"poll_{symbol}"
        
        # Store callback
        self.price_callbacks[symbol] = callback
        
        # Create polling thread
        def poll_price():
            while symbol in self.price_callbacks:
                try:
                    price = self.get_symbol_price(symbol)
                    callback({'symbol': symbol, 'price': price})
                except Exception as e:
                    print(f"Error polling price: {e}")
                
                # Sleep for 5 seconds
                time.sleep(5)
        
        # Start polling thread
        poll_thread = threading.Thread(target=poll_price)
        poll_thread.daemon = True
        poll_thread.start()
        
        # Store thread reference
        self.socket_connections[symbol] = poll_id
        
        return poll_id
    
    def stop_symbol_ticker_websocket(self, symbol: str) -> None:
        """
        Stop a WebSocket connection for symbol ticker updates.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
        """
        if symbol in self.socket_connections and self.socket_manager is not None:
            conn_key = self.socket_connections[symbol]
            
            # Check if this is a polling connection
            if conn_key.startswith("poll_"):
                # Just remove from callbacks to stop the polling thread
                if symbol in self.price_callbacks:
                    del self.price_callbacks[symbol]
            else:
                try:
                    # Check if this is the new SpotWebsocketClient
                    if hasattr(self.socket_manager, 'stop_socket'):
                        self.socket_manager.stop_socket(conn_key)
                    else:
                        # New client might handle this differently
                        pass
                except Exception as e:
                    print(f"Error stopping socket: {e}")
            
            del self.socket_connections[symbol]
            
            if symbol in self.price_callbacks:
                del self.price_callbacks[symbol]
    
    def _load_manual_data(self):
        """Load manual data from file."""
        try:
            if os.path.exists(self.MANUAL_DATA_PATH):
                with open(self.MANUAL_DATA_PATH, 'r') as f:
                    data = json.load(f)
                    self.manual_orders = data.get('manual_orders', {})
                    self.symbol_mappings = data.get('symbol_mappings', {})
        except Exception as e:
            print(f"Error loading manual data: {e}")
            self.manual_orders = {}
            self.symbol_mappings = {}
    
    def _save_manual_data(self):
        """Save manual data to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.MANUAL_DATA_PATH), exist_ok=True)
            
            # Save data
            with open(self.MANUAL_DATA_PATH, 'w') as f:
                json.dump({
                    'manual_orders': self.manual_orders,
                    'symbol_mappings': self.symbol_mappings
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving manual data: {e}")
    
    def add_manual_order(self, order: Dict) -> bool:
        """
        Add a manual order.
        
        Args:
            order: Order dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = order['symbol']
            
            # Initialize list if needed
            if symbol not in self.manual_orders:
                self.manual_orders[symbol] = []
                
            # Add order
            self.manual_orders[symbol].append(order)
            
            # Save data
            self._save_manual_data()
            
            return True
        except Exception as e:
            print(f"Error adding manual order: {e}")
            return False
    
    def get_manual_orders(self, symbol: str) -> List[Dict]:
        """
        Get manual orders for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of manual orders
        """
        return self.manual_orders.get(symbol, [])
    
    def delete_manual_order(self, symbol: str, order_id: int) -> bool:
        """
        Delete a manual order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if symbol in self.manual_orders:
                # Find and remove order
                self.manual_orders[symbol] = [
                    order for order in self.manual_orders[symbol]
                    if order.get('orderId') != order_id
                ]
                
                # Save data
                self._save_manual_data()
                
                return True
            return False
        except Exception as e:
            print(f"Error deleting manual order: {e}")
            return False
    
    def add_symbol_mapping(self, invalid_symbol: str, valid_symbol: str) -> bool:
        """
        Add a symbol mapping.
        
        Args:
            invalid_symbol: Invalid symbol (e.g., 'AGLDUSDC')
            valid_symbol: Valid symbol (e.g., 'AGLDBTC')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.symbol_mappings[invalid_symbol] = valid_symbol
            self._save_manual_data()
            return True
        except Exception as e:
            print(f"Error adding symbol mapping: {e}")
            return False
    
    def get_mapped_symbol(self, symbol: str) -> str:
        """
        Get mapped symbol if available.
        
        Args:
            symbol: Original symbol
            
        Returns:
            Mapped symbol if available, otherwise original symbol
        """
        return self.symbol_mappings.get(symbol, symbol)
        
    def get_symbol_price(self, symbol: str) -> float:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Current price as float
        
        Raises:
            Exception: If price cannot be retrieved
        """
        try:
            # Check if we have a symbol mapping
            mapped_symbol = self.get_mapped_symbol(symbol)
            
            # Get ticker price
            ticker = self.client.get_symbol_ticker(symbol=mapped_symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            raise
    
    def get_all_trading_pairs(self) -> List[str]:
        """
        Get all available trading pairs.
        
        Returns:
            List of trading pair symbols
        """
        try:
            # Get exchange info
            exchange_info = self.client.get_exchange_info()
            
            # Extract symbols
            return [symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['status'] == 'TRADING']
        except Exception as e:
            print(f"Error getting trading pairs: {e}")
            return []
    
    def _load_preferences(self):
        """Load user preferences from file."""
        try:
            if os.path.exists(self.PREFERENCES_PATH):
                with open(self.PREFERENCES_PATH, 'r') as f:
                    data = json.load(f)
                    self.preferences = data
            else:
                # Initialize with default preferences
                self.preferences = {
                    'preferred_pairs': {}
                }
        except Exception as e:
            print(f"Error loading preferences: {e}")
            self.preferences = {
                'preferred_pairs': {}
            }
    
    def _save_preferences(self):
        """Save user preferences to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.PREFERENCES_PATH), exist_ok=True)
            
            # Save data
            with open(self.PREFERENCES_PATH, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
    
    def set_preferred_pair(self, asset: str, pair: str) -> bool:
        """
        Set preferred trading pair for an asset.
        
        Args:
            asset: Asset name (e.g., 'BTC')
            pair: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract asset from pair if not provided
            if not asset:
                # Try to extract from pair
                base_asset = pair[-4:] if pair[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else pair[-3:]
                asset = pair[:-len(base_asset)]
            
            # Store preference
            if 'preferred_pairs' not in self.preferences:
                self.preferences['preferred_pairs'] = {}
                
            self.preferences['preferred_pairs'][asset] = pair
            
            # Save preferences
            self._save_preferences()
            
            return True
        except Exception as e:
            print(f"Error setting preferred pair: {e}")
            return False
    
    def get_preferred_pair(self, asset: str) -> str:
        """
        Get preferred trading pair for an asset.
        
        Args:
            asset: Asset name (e.g., 'BTC')
            
        Returns:
            Preferred trading pair or empty string if not found
        """
        try:
            return self.preferences.get('preferred_pairs', {}).get(asset, '')
        except Exception as e:
            print(f"Error getting preferred pair: {e}")
            return ''
    
    def close_websockets(self) -> None:
        """
        Close all WebSocket connections.
        """
        if self.socket_manager is not None:
            try:
                # Check if this is the new SpotWebsocketClient
                if hasattr(self.socket_manager, 'close'):
                    self.socket_manager.close()
                else:
                    # New client might handle this differently
                    if hasattr(self.socket_manager, 'disconnect'):
                        self.socket_manager.disconnect()
            except Exception as e:
                print(f"Error closing WebSockets: {e}")
            
            self.socket_manager = None
            self.socket_connections = {}
            self.price_callbacks = {}
            self._ws_thread = None