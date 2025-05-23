import os
import json
import threading
import importlib.util
import customtkinter as ctk
from typing import Dict, List, Optional, Callable

# Get the absolute path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Import modules directly using file paths
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import required modules
core_auth = import_from_file("auth", os.path.join(project_root, "core", "auth.py"))
core_api_client = import_from_file("api_client", os.path.join(project_root, "core", "api_client.py"))
core_calculator = import_from_file("calculator", os.path.join(project_root, "core", "calculator.py"))
ui_dialogs = import_from_file("dialogs", os.path.join(current_dir, "dialogs.py"))
ui_asset_button = import_from_file("asset_button", os.path.join(current_dir, "widgets", "asset_button.py"))
ui_asset_detail = import_from_file("asset_detail", os.path.join(current_dir, "widgets", "asset_detail.py"))

# Get required classes and functions
credentials_exist = core_auth.credentials_exist
decrypt_credentials = core_auth.decrypt_credentials
validate_permissions = core_auth.validate_permissions
BinanceApiClient = core_api_client.BinanceApiClient
format_currency = core_calculator.format_currency
format_crypto_amount = core_calculator.format_crypto_amount
format_percent = core_calculator.format_percent
SetupDialog = ui_dialogs.SetupDialog
PinDialog = ui_dialogs.PinDialog
PairSelectionDialog = ui_dialogs.PairSelectionDialog
AssetButton = ui_asset_button.AssetButton
AssetDetailFrame = ui_asset_detail.AssetDetailFrame


class MainWindow(ctk.CTk):
    """
    Main application window for the Binance Portfolio Tracker.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Set window properties
        self.title("Binance Portfolio Tracker")
        self.geometry("1000x600")
        self.minsize(800, 500)
        
        # Initialize variables
        self.api_client = None
        self.config = self._load_config()
        self.selected_asset = None
        self.asset_buttons = {}
        self.update_thread = None
        self.stop_update = False
        
        # Set theme
        ctk.set_appearance_mode(self.config.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        
        # Create UI components
        self._create_menu()
        self._create_layout()
        
        # Bind events
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Initialize authentication
        self._initialize_auth()
    
    def _load_config(self) -> Dict:
        """
        Load configuration from file or create default.
        
        Returns:
            Configuration dictionary
        """
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")
        
        # Default configuration
        default_config = {
            "theme": "dark",
            "base_currency": "USDT",
            "window_size": "1000x600",
            "pinned_tokens": []
        }
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Load existing config or create default
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return default_config
        else:
            # Save default config
            with open(config_path, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")
        
        # Update window size
        self.config["window_size"] = f"{self.winfo_width()}x{self.winfo_height()}"
        
        # Save config
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=4)
    
    def _create_menu(self) -> None:
        """Create application menu."""
        # Create menu bar
        self.menu = ctk.CTkFrame(self)
        self.menu.pack(side="top", fill="x")
        
        # Theme toggle
        theme_label = ctk.CTkLabel(self.menu, text="Theme:")
        theme_label.pack(side="left", padx=10, pady=5)
        
        theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        theme_menu = ctk.CTkOptionMenu(
            self.menu,
            values=["dark", "light"],
            variable=theme_var,
            command=self._change_theme
        )
        theme_menu.pack(side="left", padx=5, pady=5)
        
        # Base currency selection
        currency_label = ctk.CTkLabel(self.menu, text="Base Currency:")
        currency_label.pack(side="left", padx=10, pady=5)
        
        currency_var = ctk.StringVar(value=self.config.get("base_currency", "USDT"))
        currency_menu = ctk.CTkOptionMenu(
            self.menu,
            values=["USDT", "USDC", "BUSD"],
            variable=currency_var,
            command=self._change_base_currency
        )
        currency_menu.pack(side="left", padx=5, pady=5)
        
        # API Management button
        api_button = ctk.CTkButton(
            self.menu,
            text="Manage API",
            command=self._show_api_management
        )
        api_button.pack(side="right", padx=10, pady=5)
        
        # Refresh button
        refresh_button = ctk.CTkButton(
            self.menu,
            text="Refresh",
            command=self._refresh_data
        )
        refresh_button.pack(side="right", padx=10, pady=5)
    
    def _create_layout(self) -> None:
        """Create main application layout."""
        # Create main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create sidebar for asset list
        self.sidebar = ctk.CTkScrollableFrame(self.main_container, width=200)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        
        # Create sidebar label
        sidebar_label = ctk.CTkLabel(
            self.sidebar,
            text="Assets",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        sidebar_label.pack(pady=(0, 10))
        
        # Create main content area
        self.content = ctk.CTkFrame(self.main_container)
        self.content.pack(side="left", fill="both", expand=True)
        
        # Create asset detail frame
        self.asset_detail = AssetDetailFrame(self.content)
        self.asset_detail.pack(fill="both", expand=True)
        
        # Create status bar
        self.status_bar = ctk.CTkFrame(self)
        self.status_bar.pack(side="bottom", fill="x")
        
        # Status label
        self.status_label = ctk.CTkLabel(self.status_bar, text="Not connected")
        self.status_label.pack(side="left", padx=10, pady=5)
        
        # Portfolio summary
        self.portfolio_frame = ctk.CTkFrame(self.status_bar)
        self.portfolio_frame.pack(side="right", padx=10, pady=5)
        
        self.portfolio_value_label = ctk.CTkLabel(
            self.portfolio_frame,
            text="Total: $0.00",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.portfolio_value_label.pack(side="left", padx=5)
        
        self.portfolio_pnl_label = ctk.CTkLabel(
            self.portfolio_frame,
            text="PnL: $0.00 (0.00%)",
            font=ctk.CTkFont(size=12)
        )
        self.portfolio_pnl_label.pack(side="left", padx=5)
    
    def _initialize_auth(self) -> None:
        """Initialize authentication and API client."""
        if credentials_exist():
            # Show PIN dialog
            dialog = PinDialog(self)
            self.wait_window(dialog)
            
            if dialog.pin:
                # Decrypt credentials
                api_key, api_secret = decrypt_credentials(dialog.pin)
                
                if api_key and api_secret:
                    # Validate permissions
                    if validate_permissions(api_key, api_secret):
                        # Initialize API client
                        self.api_client = BinanceApiClient(api_key, api_secret)
                        self.status_label.configure(text="Connected to Binance")
                        
                        # Load data
                        self._load_assets()
                    else:
                        self.status_label.configure(
                            text="Error: Could not validate API permissions. Please check your API key."
                        )
                else:
                    self.status_label.configure(text="Error: Invalid PIN or corrupted credentials")
        else:
            # Show setup dialog
            dialog = SetupDialog(self)
            self.wait_window(dialog)
            
            if dialog.api_key and dialog.api_secret and dialog.pin:
                # Validate permissions
                if validate_permissions(dialog.api_key, dialog.api_secret):
                    # Initialize API client
                    self.api_client = BinanceApiClient(dialog.api_key, dialog.api_secret)
                    self.status_label.configure(text="Connected to Binance")
                    
                    # Load data
                    self._load_assets()
                else:
                    self.status_label.configure(
                        text="Error: Could not validate API permissions. Please check your API key."
                    )
    
    def _load_assets(self) -> None:
        """Load assets from Binance account."""
        if not self.api_client:
            return
            
        # Clear existing asset buttons
        for button in self.asset_buttons.values():
            button.destroy()
        self.asset_buttons = {}
        
        # Show loading message
        self.status_label.configure(text="Loading assets...")
        
        # Get balances in a separate thread
        def fetch_balances():
            try:
                # Get non-zero balances with minimum value of $1
                balances = self.api_client.get_spot_balances(min_value=1.0)
                
                # Update UI in main thread
                self.after(0, lambda: self._update_asset_list(balances))
            except Exception as e:
                print(f"Error loading assets: {e}")
                self.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}"))
        
        threading.Thread(target=fetch_balances).start()
    
    def _update_asset_list(self, balances: List[Dict]) -> None:
        """
        Update asset list with balances.
        
        Args:
            balances: List of balance dictionaries
        """
        # Store balances for later use
        self.balances = balances
        
        # Show pair selection dialog
        self._show_pair_selection_dialog(balances)
    
    def _show_pair_selection_dialog(self, balances: List[Dict]) -> None:
        """
        Show dialog to select trading pairs.
        
        Args:
            balances: List of balance dictionaries
        """
        # Create dialog
        dialog = PairSelectionDialog(
            self,
            self.api_client,
            balances,
            self._on_pairs_selected
        )
        
        # Set focus to dialog
        dialog.focus_set()
    
    def _on_pairs_selected(self, selected_pairs: Dict[str, str]) -> None:
        """
        Handle selected pairs from dialog.
        
        Args:
            selected_pairs: Dictionary of asset -> pair
        """
        # Clear existing asset buttons
        for button in self.asset_buttons.values():
            button.destroy()
        self.asset_buttons = {}
        
        # Create asset buttons for selected pairs
        for asset, pair in selected_pairs.items():
            # Find balance for this asset
            balance = next((b for b in self.balances if b['asset'] == asset), None)
            if not balance:
                continue
            
            # Create button
            button = AssetButton(
                self.sidebar,
                asset=asset,
                symbol=pair,
                balance=balance['total'],
                usd_value=balance['usd_value'],
                command=lambda s=pair: self._select_asset(s)
            )
            button.pack(fill="x", pady=2)
            self.asset_buttons[pair] = button
        
        # Update status
        self.status_label.configure(text=f"Loaded {len(self.asset_buttons)} assets")
        
        # Select first asset if available
        if self.asset_buttons:
            first_symbol = next(iter(self.asset_buttons))
            self._select_asset(first_symbol)
            
        # Start portfolio update thread
        self._start_portfolio_updates()
    
    def _select_asset(self, symbol: str) -> None:
        """
        Select an asset and display its details.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
        """
        # Update selected asset
        self.selected_asset = symbol
        
        # Highlight selected button
        for s, button in self.asset_buttons.items():
            button.set_selected(s == symbol)
        
        # Update asset detail view
        if self.api_client:
            # Show loading message
            self.asset_detail.set_loading(True)
            
            # Get asset details in a separate thread
            def fetch_details():
                try:
                    # Get order history
                    orders = self.api_client.get_order_history(symbol)
                    
                    # Get open orders
                    open_orders = self.api_client.get_open_orders(symbol)
                    
                    # Calculate position metrics
                    metrics = self.api_client.calculate_position_metrics(symbol)
                    
                    # Add open orders to metrics
                    metrics['open_orders'] = open_orders
                    
                    # Update UI in main thread
                    self.after(0, lambda: self._update_asset_detail(symbol, orders, metrics))
                except Exception as e:
                    print(f"Error loading asset details: {e}")
                    self.after(0, lambda: self.asset_detail.set_error(str(e)))
            
            threading.Thread(target=fetch_details).start()
    
    def _update_asset_detail(self, symbol: str, orders: List[Dict], metrics: Dict) -> None:
        """
        Update asset detail view with data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            orders: List of order dictionaries
            metrics: Position metrics dictionary
        """
        # Update asset detail view
        self.asset_detail.update_data(symbol, orders, metrics)
        
        # Set API client reference for the asset detail frame to use
        if hasattr(self.asset_detail, '_api_client'):
            self.asset_detail._api_client = self.api_client
        
        # Start price updates via WebSocket
        if self.api_client:
            # Stop existing WebSocket if any
            for s in list(self.asset_buttons.keys()):
                if s != symbol and s in self.asset_buttons:
                    self.api_client.stop_symbol_ticker_websocket(s)
            
            # Start new WebSocket
            def price_update(data):
                if data['symbol'] == symbol:
                    price = data['price']
                    self.asset_detail.update_price(price)
            
            self.api_client.start_symbol_ticker_websocket(symbol, price_update)
    
    def _update_asset(self, symbol: str) -> None:
        """
        Update asset view with a different trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
        """
        # Check if the symbol is already in the asset buttons
        if symbol in self.asset_buttons:
            # Just click the existing button
            self.asset_buttons[symbol].invoke()
            return
            
        # Otherwise, we need to fetch the asset data
        if self.api_client:
            # Show loading message
            self.asset_detail.set_loading(True)
            
            # Get asset details in a separate thread
            def fetch_details():
                try:
                    # Get order history
                    orders = self.api_client.get_order_history(symbol)
                    
                    # Get open orders
                    open_orders = self.api_client.get_open_orders(symbol)
                    
                    # Calculate position metrics
                    metrics = self.api_client.calculate_position_metrics(symbol)
                    
                    # Add open orders to metrics
                    metrics['open_orders'] = open_orders
                    
                    # Update UI in main thread
                    self.after(0, lambda: self._update_asset_detail(symbol, orders, metrics))
                    
                    # Add a button for this asset if it doesn't exist
                    if symbol not in self.asset_buttons:
                        self.after(0, lambda: self._add_asset_button(symbol, metrics))
                except Exception as e:
                    print(f"Error loading asset details: {e}")
                    self.after(0, lambda: self.asset_detail.set_error(str(e)))
            
            threading.Thread(target=fetch_details).start()
    
    def _add_asset_button(self, symbol: str, metrics: Dict) -> None:
        """
        Add a new asset button to the sidebar.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            metrics: Position metrics dictionary
        """
        if symbol in self.asset_buttons:
            return
            
        # Extract base and quote assets
        base_asset = symbol[-4:] if symbol[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else symbol[-3:]
        quote_asset = symbol[:-len(base_asset)]
        
        # Create button text
        button_text = f"{quote_asset}/{base_asset}"
        
        # Create button
        from binance_tracker.ui.widgets.asset_button import AssetButton
        
        button = AssetButton(
            self.sidebar_content,
            text=button_text,
            symbol=symbol,
            holdings=metrics.get('holdings', 0),
            command=lambda s=symbol: self._update_asset_view(s)
        )
        button.pack(fill="x", padx=10, pady=5)
        
        # Store button reference
        self.asset_buttons[symbol] = button
    
    def _start_portfolio_updates(self) -> None:
        """Start periodic portfolio updates."""
        if self.update_thread is not None:
            return
            
        self.stop_update = False
        
        def update_loop():
            while not self.stop_update:
                try:
                    if self.api_client:
                        # Get all position metrics
                        positions = []
                        for symbol in self.asset_buttons.keys():
                            metrics = self.api_client.calculate_position_metrics(symbol)
                            positions.append(metrics)
                        
                        # Calculate portfolio summary
                        total_cost = sum(p['total_cost'] for p in positions)
                        total_value = sum(p['current_value'] for p in positions)
                        pnl_amount = total_value - total_cost
                        pnl_percent = (pnl_amount / total_cost) * 100 if total_cost > 0 else 0
                        
                        # Update UI in main thread
                        self.after(0, lambda: self._update_portfolio_summary(
                            total_value, pnl_amount, pnl_percent
                        ))
                except Exception as e:
                    print(f"Error updating portfolio: {e}")
                
                # Sleep for 30 seconds
                for _ in range(30):
                    if self.stop_update:
                        break
                    threading.Event().wait(1)
        
        self.update_thread = threading.Thread(target=update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def _update_portfolio_summary(self, total_value: float, pnl_amount: float, pnl_percent: float) -> None:
        """
        Update portfolio summary labels.
        
        Args:
            total_value: Total portfolio value
            pnl_amount: Profit/loss amount
            pnl_percent: Profit/loss percentage
        """
        # Update labels
        self.portfolio_value_label.configure(text=f"Total: {format_currency(total_value)}")
        
        # Format PnL with color
        pnl_text = f"PnL: {format_currency(pnl_amount)} ({format_percent(pnl_percent)})"
        pnl_color = "#4CAF50" if pnl_amount >= 0 else "#F44336"
        
        self.portfolio_pnl_label.configure(text=pnl_text, text_color=pnl_color)
    
    def _refresh_data(self) -> None:
        """Refresh all data."""
        if self.api_client:
            self._load_assets()
    
    def _change_theme(self, theme: str) -> None:
        """
        Change application theme.
        
        Args:
            theme: Theme name ('dark' or 'light')
        """
        ctk.set_appearance_mode(theme)
        self.config["theme"] = theme
        self._save_config()
    
    def _change_base_currency(self, currency: str) -> None:
        """
        Change base currency.
        
        Args:
            currency: Base currency code (e.g., 'USDT')
        """
        self.config["base_currency"] = currency
        self._save_config()
        
        # Reload assets
        if self.api_client:
            self._load_assets()
    
    def _show_api_management(self) -> None:
        """Show API management dialog."""
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("API Management")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title
        title_label = ctk.CTkLabel(
            main_frame,
            text="API Management",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Status frame
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="x", pady=(0, 20))
        
        # API status
        status_label = ctk.CTkLabel(
            status_frame,
            text="API Status:",
            font=ctk.CTkFont(weight="bold")
        )
        status_label.pack(side="left", padx=10, pady=10)
        
        status_value = ctk.CTkLabel(
            status_frame,
            text="Connected" if self.api_client else "Not Connected"
        )
        status_value.pack(side="left", padx=10, pady=10)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", pady=(0, 20))
        
        # Add new API button
        new_api_button = ctk.CTkButton(
            buttons_frame,
            text="Add New API",
            command=lambda: self._add_new_api(dialog)
        )
        new_api_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Forget API button
        forget_api_button = ctk.CTkButton(
            buttons_frame,
            text="Forget API",
            command=lambda: self._forget_api(dialog)
        )
        forget_api_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Reconnect button (New)
        reconnect_frame = ctk.CTkFrame(main_frame)
        reconnect_frame.pack(fill="x", pady=(0, 20))
        
        reconnect_button = ctk.CTkButton(
            reconnect_frame,
            text="Reconnect to Last API",
            command=lambda: self._reconnect_api(dialog),
            fg_color="#2E7D32",  # Green color
            hover_color="#1B5E20"  # Darker green on hover
        )
        reconnect_button.pack(pady=10, fill="x")
        
        # Close button
        close_button = ctk.CTkButton(
            main_frame,
            text="Close",
            command=dialog.destroy
        )
        close_button.pack(pady=(0, 10))
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _add_new_api(self, parent_dialog) -> None:
        """
        Add new API credentials.
        
        Args:
            parent_dialog: Parent dialog
        """
        # Close parent dialog
        parent_dialog.destroy()
        
        # Show setup dialog
        dialog = SetupDialog(self)
        self.wait_window(dialog)
        
        if dialog.api_key and dialog.api_secret and dialog.pin:
            # Validate permissions
            if validate_permissions(dialog.api_key, dialog.api_secret):
                # Initialize API client
                self.api_client = BinanceApiClient(dialog.api_key, dialog.api_secret)
                self.status_label.configure(text="Connected to Binance")
                
                # Load data
                self._load_assets()
    
    def _forget_api(self, parent_dialog) -> None:
        """
        Forget API credentials.
        
        Args:
            parent_dialog: Parent dialog
        """
        # Import delete_credentials function
        delete_credentials = core_auth.delete_credentials
        
        # Confirm dialog
        confirm_dialog = ctk.CTkToplevel(parent_dialog)
        confirm_dialog.title("Confirm")
        confirm_dialog.geometry("300x150")
        confirm_dialog.resizable(False, False)
        
        # Make dialog modal
        confirm_dialog.transient(parent_dialog)
        confirm_dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(confirm_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create label
        label = ctk.CTkLabel(
            main_frame,
            text="Are you sure you want to forget the API credentials?",
            wraplength=250
        )
        label.pack(pady=(0, 20))
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x")
        
        # Cancel button
        cancel_button = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=confirm_dialog.destroy
        )
        cancel_button.pack(side="left", padx=5, pady=5, expand=True)
        
        # Confirm button
        def confirm_forget():
            # Delete credentials
            if delete_credentials():
                # Close WebSockets
                if self.api_client:
                    self.api_client.close_websockets()
                
                # Reset client
                self.api_client = None
                
                # Clear UI
                for button in self.asset_buttons.values():
                    button.destroy()
                self.asset_buttons = {}
                
                # Update status
                self.status_label.configure(text="API credentials removed")
                
                # Close dialogs
                confirm_dialog.destroy()
                parent_dialog.destroy()
                
                # Show setup dialog to add new API
                self._initialize_auth()
        
        confirm_button = ctk.CTkButton(
            buttons_frame,
            text="Forget API",
            command=confirm_forget
        )
        confirm_button.pack(side="right", padx=5, pady=5, expand=True)
        
        # Center dialog
        confirm_dialog.update_idletasks()
        width = confirm_dialog.winfo_width()
        height = confirm_dialog.winfo_height()
        x = parent_dialog.winfo_rootx() + (parent_dialog.winfo_width() // 2) - (width // 2)
        y = parent_dialog.winfo_rooty() + (parent_dialog.winfo_height() // 2) - (height // 2)
        confirm_dialog.geometry(f"{width}x{height}+{x}+{y}")
            
    def _reconnect_api(self, parent_dialog) -> None:
            """
            Reconnect to the last used API using stored credentials.
            
            Args:
                parent_dialog: Parent dialog
            """
            # Import necessary functions from core_auth
            get_stored_credentials = core_auth.get_stored_credentials
            
            # Create PIN entry dialog
            pin_dialog = ctk.CTkToplevel(parent_dialog)
            pin_dialog.title("Enter PIN")
            pin_dialog.geometry("300x180")
            pin_dialog.resizable(False, False)
            
            # Make dialog modal
            pin_dialog.transient(parent_dialog)
            pin_dialog.grab_set()
            
            # Create main frame
            main_frame = ctk.CTkFrame(pin_dialog)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Create label
            label = ctk.CTkLabel(
                main_frame,
                text="Enter your 4-digit PIN to reconnect:",
                wraplength=250
            )
            label.pack(pady=(0, 20))
            
            # PIN entry
            pin_entry = ctk.CTkEntry(main_frame, width=100, show="*")
            pin_entry.pack(pady=(0, 20))
            pin_entry.focus_set()
            
            # Error label
            error_label = ctk.CTkLabel(
                main_frame,
                text="",
                text_color="#F44336"  # Red color for errors
            )
            error_label.pack(pady=(0, 10))
            
            # Buttons frame
            buttons_frame = ctk.CTkFrame(main_frame)
            buttons_frame.pack(fill="x")
            
            # Cancel button
            cancel_button = ctk.CTkButton(
                buttons_frame,
                text="Cancel",
                command=pin_dialog.destroy
            )
            cancel_button.pack(side="left", padx=5, pady=5, expand=True)
            
            # Connect function
            def try_connect():
                pin = pin_entry.get()
                
                # Validate PIN
                if not pin.isdigit() or len(pin) != 4:
                    error_label.configure(text="PIN must be 4 digits")
                    return
                
                # Try to get stored credentials
                try:
                    api_key, api_secret = get_stored_credentials(pin)
                    
                    if api_key and api_secret:
                        # Close existing WebSockets if any
                        if self.api_client:
                            self.api_client.close_websockets()
                        
                        # Initialize API client
                        self.api_client = BinanceApiClient(api_key, api_secret)
                        self.status_label.configure(text="Connected to Binance")
                        
                        # Load data
                        self._load_assets()
                        
                        # Close dialogs
                        pin_dialog.destroy()
                        parent_dialog.destroy()
                    else:
                        error_label.configure(text="Invalid PIN or no credentials stored")
                except Exception as e:
                    error_label.configure(text=f"Error: {str(e)}")
            
            # Connect button
            connect_button = ctk.CTkButton(
                buttons_frame,
                text="Connect",
                command=try_connect,
                fg_color="#2E7D32",  # Green color
                hover_color="#1B5E20"  # Darker green on hover
            )
            connect_button.pack(side="right", padx=5, pady=5, expand=True)
            
            # Bind Enter key to try_connect
            pin_entry.bind("<Return>", lambda event: try_connect())
            
            # Center dialog
            pin_dialog.update_idletasks()
            width = pin_dialog.winfo_width()
            height = pin_dialog.winfo_height()
            x = parent_dialog.winfo_rootx() + (parent_dialog.winfo_width() // 2) - (width // 2)
            y = parent_dialog.winfo_rooty() + (parent_dialog.winfo_height() // 2) - (height // 2)
            pin_dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _on_close(self) -> None:
        """Handle window close event."""
        # Stop update thread
        self.stop_update = True
        
        # Close WebSockets
        if self.api_client:
            self.api_client.close_websockets()
        
        # Save config
        self._save_config()
        
        # Destroy window
        self.destroy()