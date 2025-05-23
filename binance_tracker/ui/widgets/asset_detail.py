import os
import importlib.util
import customtkinter as ctk
from typing import Dict, List, Optional
import threading
import time

# Get the absolute path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
widgets_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(widgets_dir)

# Import modules directly using file paths
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import required modules
core_calculator = import_from_file("calculator", os.path.join(project_root, "core", "calculator.py"))

# Get required functions
format_currency = core_calculator.format_currency
format_crypto_amount = core_calculator.format_crypto_amount
format_percent = core_calculator.format_percent


class AssetDetailFrame(ctk.CTkFrame):
    """
    Frame for displaying detailed information about a selected asset.
    """
    
    def __init__(self, master, **kwargs):
        """
        Initialize asset detail frame.
        
        Args:
            master: Parent widget
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Initialize variables
        self.symbol = None
        self.orders = []
        self.metrics = {}
        self.include_orders = {}
        self._api_client = None  # Reference to the API client
        
        # Create widgets
        self._create_widgets()
    
    def _create_widgets(self):
        """Create frame widgets."""
        # Create main layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header frame
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Symbol frame
        symbol_frame = ctk.CTkFrame(self.header_frame)
        symbol_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        # Symbol label
        self.symbol_label = ctk.CTkLabel(
            symbol_frame,
            text="Select an asset",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.symbol_label.pack(side="left", padx=(0, 5))
        
        # Change pair button
        self.change_pair_btn = ctk.CTkButton(
            symbol_frame,
            text="Change Pair",
            width=100,
            height=25,
            command=self._change_trading_pair
        )
        self.change_pair_btn.pack(side="left", padx=5)
        self.change_pair_btn.configure(state="disabled")  # Initially disabled
        
        # Price label
        self.price_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=ctk.CTkFont(size=20)
        )
        self.price_label.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        
        # Metrics frame
        self.metrics_frame = ctk.CTkFrame(self)
        self.metrics_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.metrics_frame.grid_columnconfigure(0, weight=1)
        self.metrics_frame.grid_columnconfigure(1, weight=1)
        
        # Holdings
        holdings_label = ctk.CTkLabel(
            self.metrics_frame,
            text="Holdings:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        holdings_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.holdings_value = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.holdings_value.grid(row=0, column=1, sticky="e", padx=10, pady=5)
        
        # Available
        available_label = ctk.CTkLabel(
            self.metrics_frame,
            text="Available:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        available_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.available_value = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.available_value.grid(row=1, column=1, sticky="e", padx=10, pady=5)
        
        # Locked
        locked_label = ctk.CTkLabel(
            self.metrics_frame,
            text="Locked:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        locked_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        
        self.locked_value = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.locked_value.grid(row=2, column=1, sticky="e", padx=10, pady=5)
        
        # Average buy price
        avg_buy_label = ctk.CTkLabel(
            self.metrics_frame,
            text="Avg Buy:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        avg_buy_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)
        
        self.avg_buy_value = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.avg_buy_value.grid(row=3, column=1, sticky="e", padx=10, pady=5)
        
        # Break-even price
        break_even_label = ctk.CTkLabel(
            self.metrics_frame,
            text="Break-even:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        break_even_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)
        
        self.break_even_value = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.break_even_value.grid(row=4, column=1, sticky="e", padx=10, pady=5)
        
        # PnL
        pnl_label = ctk.CTkLabel(
            self.metrics_frame,
            text="PnL:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        pnl_label.grid(row=5, column=0, sticky="w", padx=10, pady=5)
        
        self.pnl_value = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.pnl_value.grid(row=5, column=1, sticky="e", padx=10, pady=5)
        
        # Order history frame
        self.order_frame = ctk.CTkFrame(self)
        self.order_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Order history header frame
        order_header_frame = ctk.CTkFrame(self.order_frame)
        order_header_frame.pack(fill="x", padx=10, pady=10)
        
        # Order history label
        order_label = ctk.CTkLabel(
            order_header_frame,
            text="Order History",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        order_label.pack(side="left")
        
        # Control panel frame
        control_panel = ctk.CTkFrame(self.order_frame)
        control_panel.pack(fill="x", padx=10, pady=(0, 10))
        
        # Filter frame
        filter_frame = ctk.CTkFrame(control_panel)
        filter_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        filter_label = ctk.CTkLabel(filter_frame, text="Filter:")
        filter_label.pack(side="left", padx=5)
        
        # Time filter buttons
        self.filter_all_btn = ctk.CTkButton(
            filter_frame,
            text="All",
            width=60,
            command=lambda: self._filter_orders("all")
        )
        self.filter_all_btn.pack(side="left", padx=2)
        
        self.filter_24h_btn = ctk.CTkButton(
            filter_frame,
            text="24h",
            width=60,
            command=lambda: self._filter_orders("24h")
        )
        self.filter_24h_btn.pack(side="left", padx=2)
        
        self.filter_7d_btn = ctk.CTkButton(
            filter_frame,
            text="7d",
            width=60,
            command=lambda: self._filter_orders("7d")
        )
        self.filter_7d_btn.pack(side="left", padx=2)
        
        self.filter_30d_btn = ctk.CTkButton(
            filter_frame,
            text="30d",
            width=60,
            command=lambda: self._filter_orders("30d")
        )
        self.filter_30d_btn.pack(side="left", padx=2)
        
        # Selection buttons frame
        selection_frame = ctk.CTkFrame(control_panel)
        selection_frame.pack(side="left", fill="x", padx=5, pady=5)
        
        # Select/Deselect All button
        self.select_all_btn = ctk.CTkButton(
            selection_frame,
            text="Select All",
            width=100,
            command=self._toggle_select_all
        )
        self.select_all_btn.pack(side="left", padx=5)
        
        # Action buttons frame
        action_frame = ctk.CTkFrame(control_panel)
        action_frame.pack(side="right", fill="x", padx=5, pady=5)
        
        # Calculate selected button
        self.calc_selected_btn = ctk.CTkButton(
            action_frame,
            text="Calculate Selected",
            command=self._calculate_selected
        )
        self.calc_selected_btn.pack(side="left", padx=5)
        
        # Add manual order button
        self.add_order_btn = ctk.CTkButton(
            action_frame,
            text="Add Manual Order",
            command=self._add_manual_order
        )
        self.add_order_btn.pack(side="left", padx=5)
        
        # Price alert button
        self.alert_btn = ctk.CTkButton(
            action_frame,
            text="Set Alert",
            command=self._set_price_alert
        )
        self.alert_btn.pack(side="left", padx=5)
        
        # Order history table
        self.order_table = OrderTable(self.order_frame, self._on_order_toggle)
        self.order_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Open orders section
        self.open_orders_frame = ctk.CTkFrame(self.order_frame)
        self.open_orders_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Open orders header
        open_orders_header = ctk.CTkFrame(self.open_orders_frame)
        open_orders_header.pack(fill="x", pady=(5, 0))
        
        open_orders_label = ctk.CTkLabel(
            open_orders_header,
            text="Open Orders",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        open_orders_label.pack(side="left", padx=10, pady=5)
        
        # Open orders content
        self.open_orders_content = ctk.CTkFrame(self.open_orders_frame)
        self.open_orders_content.pack(fill="x", pady=5)
        
        # No open orders label (initially visible)
        self.no_open_orders_label = ctk.CTkLabel(
            self.open_orders_content,
            text="No open orders",
            font=ctk.CTkFont(size=12)
        )
        self.no_open_orders_label.pack(padx=10, pady=10)
        
        # Loading indicator
        self.loading_label = ctk.CTkLabel(
            self,
            text="Loading...",
            font=ctk.CTkFont(size=16)
        )
        
        # Error label
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#F44336",
            font=ctk.CTkFont(size=14)
        )
    
    def set_loading(self, loading: bool):
        """
        Show or hide loading indicator.
        
        Args:
            loading: Whether to show loading indicator
        """
        if loading:
            # Hide other widgets
            self.header_frame.grid_remove()
            self.metrics_frame.grid_remove()
            self.order_frame.grid_remove()
            self.error_label.grid_remove()
            
            # Show loading indicator
            self.loading_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        else:
            # Hide loading indicator
            self.loading_label.grid_remove()
            
            # Show other widgets
            self.header_frame.grid()
            self.metrics_frame.grid()
            self.order_frame.grid()
    
    def set_error(self, error_message: str):
        """
        Show error message.
        
        Args:
            error_message: Error message to display
        """
        # Hide loading indicator
        self.loading_label.grid_remove()
        
        # Show error message
        self.error_label.configure(text=f"Error: {error_message}")
        self.error_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def update_data(self, symbol: str, orders: List[Dict], metrics: Dict):
        """
        Update asset detail with data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            orders: List of order dictionaries
            metrics: Position metrics dictionary
        """
        # Store data
        self.symbol = symbol
        self.orders = orders
        self.metrics = metrics
        
        # Initialize order inclusion if needed
        if not self.include_orders or symbol not in self.include_orders:
            self.include_orders[symbol] = {order['orderId']: True for order in orders}
        
        # Update UI
        self._update_ui()
        
        # Enable change pair button
        self.change_pair_btn.configure(state="normal")
        
        # Hide loading indicator
        self.set_loading(False)
    
    def update_price(self, price: float):
        """
        Update current price.
        
        Args:
            price: Current price
        """
        if self.symbol:
            # Update price label
            self.price_label.configure(text=format_currency(price))
            
            # Update metrics with new price
            if self.metrics:
                # Calculate new PnL
                holdings = self.metrics.get('holdings', 0)
                avg_buy = self.metrics.get('avg_buy_price', 0)
                
                if holdings > 0 and avg_buy > 0:
                    current_value = holdings * price
                    cost_basis = holdings * avg_buy
                    pnl_amount = current_value - cost_basis
                    pnl_percent = (pnl_amount / cost_basis) * 100 if cost_basis > 0 else 0
                    
                    # Update PnL display
                    self._update_pnl(pnl_amount, pnl_percent)
    
    def _update_ui(self):
        """Update UI with current data."""
        if not self.symbol or not self.metrics:
            return
            
        # Update symbol and price
        base_asset = self.symbol[-4:] if self.symbol[-4:] in ['USDT', 'USDC', 'BUSD'] else self.symbol[-3:]
        quote_asset = self.symbol[:-len(base_asset)]
        
        self.symbol_label.configure(text=f"{quote_asset}/{base_asset}")
        self.price_label.configure(text=format_currency(self.metrics.get('current_price', 0)))
        
        # Update metrics
        self.holdings_value.configure(
            text=f"{format_crypto_amount(self.metrics.get('holdings', 0))} {quote_asset}"
        )
        
        # Update available and locked amounts
        available = self.metrics.get('available', 0)
        locked = self.metrics.get('locked', 0)
        
        self.available_value.configure(
            text=f"{format_crypto_amount(available)} {quote_asset}"
        )
        
        # Show locked amount with different color if non-zero
        if locked > 0:
            self.locked_value.configure(
                text=f"{format_crypto_amount(locked)} {quote_asset}",
                text_color="#FFA500"  # Orange color for locked amounts
            )
        else:
            self.locked_value.configure(
                text=f"{format_crypto_amount(locked)} {quote_asset}",
                text_color=self.holdings_value.cget("text_color")  # Reset to default color
            )
        
        self.avg_buy_value.configure(
            text=format_currency(self.metrics.get('avg_buy_price', 0))
        )
        
        self.break_even_value.configure(
            text=format_currency(self.metrics.get('break_even_price', 0))
        )
        
        # Update PnL
        pnl_amount = self.metrics.get('pnl_amount', 0)
        pnl_percent = self.metrics.get('pnl_percent', 0)
        self._update_pnl(pnl_amount, pnl_percent)
        
        # Update order table
        self.order_table.update_orders(self.orders, self.include_orders.get(self.symbol, {}))
        
        # Update open orders display
        self._update_open_orders()
    
    def _update_pnl(self, pnl_amount: float, pnl_percent: float):
        """
        Update PnL display.
        
        Args:
            pnl_amount: Profit/loss amount
            pnl_percent: Profit/loss percentage
        """
        # Format PnL text
        pnl_text = f"{format_percent(pnl_percent)} ({format_currency(pnl_amount)})"
        
        # Set color based on PnL
        pnl_color = "#4CAF50" if pnl_amount >= 0 else "#F44336"
        
        # Update label
        self.pnl_value.configure(text=pnl_text, text_color=pnl_color)
    
    def _on_order_toggle(self, order_id: int, include: bool):
        """
        Handle order toggle event.
        
        Args:
            order_id: Order ID
            include: Whether to include the order in calculations
        """
        if self.symbol:
            # Update order inclusion
            if self.symbol not in self.include_orders:
                self.include_orders[self.symbol] = {}
                
            self.include_orders[self.symbol][order_id] = include
            
            # Recalculate metrics (in a separate thread to avoid UI freeze)
            def recalculate():
                # TODO: Implement recalculation with API client
                # For now, just update UI
                self.after(0, self._update_ui)
                
            threading.Thread(target=recalculate).start()
    
    def _filter_orders(self, period: str):
        """
        Filter orders by time period.
        
        Args:
            period: Time period to filter by ('all', '24h', '7d', '30d')
        """
        if not self.symbol or not self.orders:
            return
            
        # Highlight active filter button
        self.filter_all_btn.configure(fg_color=("#3B8ED0" if period == "all" else "#1F6AA5"))
        self.filter_24h_btn.configure(fg_color=("#3B8ED0" if period == "24h" else "#1F6AA5"))
        self.filter_7d_btn.configure(fg_color=("#3B8ED0" if period == "7d" else "#1F6AA5"))
        self.filter_30d_btn.configure(fg_color=("#3B8ED0" if period == "30d" else "#1F6AA5"))
        
        # If 'all', show all orders
        if period == "all":
            self.order_table.update_orders(self.orders, self.include_orders.get(self.symbol, {}))
            return
            
        # Calculate cutoff time based on period
        import datetime
        import time
        
        now = datetime.datetime.now()
        
        if period == "24h":
            cutoff = now - datetime.timedelta(hours=24)
        elif period == "7d":
            cutoff = now - datetime.timedelta(days=7)
        elif period == "30d":
            cutoff = now - datetime.timedelta(days=30)
        else:
            # Default to all orders
            self.order_table.update_orders(self.orders, self.include_orders.get(self.symbol, {}))
            return
            
        # Convert cutoff to timestamp
        cutoff_timestamp = cutoff.strftime('%Y-%m-%d %H:%M:%S')
        
        # Filter orders
        filtered_orders = [order for order in self.orders if order.get('time', '') >= cutoff_timestamp]
        
        # Update order table with filtered orders
        self.order_table.update_orders(filtered_orders, self.include_orders.get(self.symbol, {}))
    
    def _calculate_selected(self):
        """Calculate metrics based on selected orders only."""
        if not self.symbol or not self.orders:
            return
            
        # Get selected order IDs
        selected_order_ids = [
            order_id for order_id, include in self.include_orders.get(self.symbol, {}).items()
            if include
        ]
        
        # If no orders are selected, show a message
        if not selected_order_ids:
            self._show_message("Please select at least one order to calculate metrics.")
            return
            
        # Show calculating message
        self._show_message("Calculating metrics for selected orders...")
        
        # Recalculate metrics with selected orders
        def recalculate():
            try:
                if self._api_client:
                    # Check if we need to handle a special case for invalid symbols
                    if "Invalid symbol" in self.get_message():
                        # Show dialog to enter current price manually
                        self.after(0, lambda: self._prompt_manual_price(selected_order_ids))
                    else:
                        # Calculate metrics with selected orders
                        metrics = self._api_client.calculate_position_metrics(self.symbol, selected_order_ids)
                        
                        # Update metrics in UI
                        self.after(0, lambda: self._update_metrics(metrics))
                        
                        # Clear message
                        self.after(500, lambda: self._clear_message())
                else:
                    self.after(0, lambda: self._show_message("API client not available."))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._show_message(f"Error calculating metrics: {error_msg}"))
                
                # If it's an invalid symbol error or price retrieval error, prompt for symbol mapping
                if "Invalid symbol" in error_msg or "price" in error_msg.lower():
                    self.after(100, lambda: self._prompt_symbol_mapping(selected_order_ids))
                
        threading.Thread(target=recalculate).start()
    
    def _add_manual_order(self):
        """Add a manual order to the order history."""
        if not self.symbol:
            return
            
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Manual Order")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Add Manual Order",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create form
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", pady=(0, 20))
        
        # Side selection
        side_label = ctk.CTkLabel(form_frame, text="Side:")
        side_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        side_var = ctk.StringVar(value="BUY")
        side_frame = ctk.CTkFrame(form_frame)
        side_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        buy_radio = ctk.CTkRadioButton(
            side_frame,
            text="BUY",
            variable=side_var,
            value="BUY"
        )
        buy_radio.pack(side="left", padx=10)
        
        sell_radio = ctk.CTkRadioButton(
            side_frame,
            text="SELL",
            variable=side_var,
            value="SELL"
        )
        sell_radio.pack(side="left", padx=10)
        
        # Date selection
        date_label = ctk.CTkLabel(form_frame, text="Date:")
        date_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        # Get current date and time
        import datetime
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        date_entry = ctk.CTkEntry(form_frame, width=200)
        date_entry.insert(0, date_str)
        date_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        # Price
        price_label = ctk.CTkLabel(form_frame, text="Price:")
        price_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        
        price_entry = ctk.CTkEntry(form_frame, width=200)
        price_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        
        # Amount
        amount_label = ctk.CTkLabel(form_frame, text="Amount:")
        amount_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)
        
        amount_entry = ctk.CTkEntry(form_frame, width=200)
        amount_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        
        # Error label
        error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        error_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Add order function
        def toggle_consolidated_view(self):
            """
            Toggle between single pair and consolidated view for this asset
            """
            # Extract base asset from symbol
            base_asset = self.symbol[-4:] if self.symbol[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else self.symbol[-3:]
            asset = self.symbol[:-len(base_asset)]
            
            if not hasattr(self, 'is_consolidated_view') or not self.is_consolidated_view:
                # Switch to consolidated view
                self.is_consolidated_view = True
                
                # Save current symbol for switching back
                self.original_symbol = self.symbol
                
                # Update title
                self.title_label.configure(text=f"{asset} (All Pairs)")
                
                # Get consolidated order history
                if self._api_client:
                    # Show loading message
                    self.set_loading(True)
                    
                    # Get data in a separate thread
                    def fetch_consolidated_data():
                        try:
                            # Get consolidated order history
                            orders = self._api_client.get_consolidated_order_history(asset)
                            
                            # Calculate consolidated metrics
                            metrics = self._api_client.calculate_consolidated_position_metrics(asset)
                            
                            # Update UI in main thread
                            self.after(0, lambda: self._update_consolidated_view(orders, metrics))
                        except Exception as e:
                            self.after(0, lambda: self.set_error(str(e)))
                    
                    import threading
                    threading.Thread(target=fetch_consolidated_data).start()
            else:
                # Switch back to single pair view
                self.is_consolidated_view = False
                
                # Restore original symbol
                if hasattr(self, 'original_symbol'):
                    self.update_data(self.original_symbol, self.orders, self.metrics)
                else:
                    self.update_data(self.symbol, self.orders, self.metrics)
        
        def _update_consolidated_view(self, orders, metrics):
            """
            Update the UI with consolidated data
            
            Args:
                orders: Consolidated order list
                metrics: Consolidated metrics
            """
            # Update orders and metrics
            self.orders = orders
            self.metrics = metrics
            
            # Hide loading indicator
            self.loading_label.grid_remove()
            
            # Update metrics display
            self._update_metrics_display(metrics)
            
            # Update order table
            self.order_table.update_orders(orders, {})
            
            # Show trading pairs used
            if 'trading_pairs' in metrics and metrics['trading_pairs']:
                pairs_text = "Trading pairs: " + ", ".join(metrics['trading_pairs'])
                if not hasattr(self, 'pairs_label'):
                    self.pairs_label = ctk.CTkLabel(
                        self.metrics_frame,
                        text=pairs_text,
                        font=("Roboto", 10)
                    )
                    self.pairs_label.grid(row=10, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 0))
                else:
                    self.pairs_label.configure(text=pairs_text)
                    self.pairs_label.grid()
            elif hasattr(self, 'pairs_label'):
                self.pairs_label.grid_remove()
        
        def add_order():
            try:
                # Get values
                side = side_var.get()
                date = date_entry.get()
                price_str = price_entry.get()
                amount_str = amount_entry.get()
                
                # Validate inputs
                if not date or not price_str or not amount_str:
                    error_label.configure(text="All fields are required")
                    return
                    
                try:
                    price = float(price_str)
                    amount = float(amount_str)
                except ValueError:
                    error_label.configure(text="Price and amount must be numbers")
                    return
                
                # Create order dictionary
                import time
                import random
                
                # Generate a unique order ID (negative to avoid conflicts with real orders)
                order_id = -int(time.time() * 1000) - random.randint(1, 1000)
                
                # Calculate total
                total = price * amount
                
                order = {
                    'orderId': order_id,
                    'symbol': self.symbol,
                    'side': side,
                    'price': price,
                    'avgPrice': price,
                    'executedQty': amount,
                    'cummulativeQuoteQty': total,
                    'time': date,
                    'status': 'FILLED',
                    'isManual': True  # Mark as manual order
                }
                
                # Add to orders list
                self.orders.append(order)
                
                # Include in calculations
                if self.symbol not in self.include_orders:
                    self.include_orders[self.symbol] = {}
                self.include_orders[self.symbol][order_id] = True
                
                # Save to API client for persistence
                if self._api_client:
                    self._api_client.add_manual_order(order)
                
                # Update order table
                self.order_table.update_orders(self.orders, self.include_orders.get(self.symbol, {}))
                
                # Close dialog
                dialog.destroy()
                
                # Show success message
                self._show_message("Manual order added successfully")
                self.after(2000, lambda: self._clear_message())
                
            except Exception as e:
                error_label.configure(text=f"Error: {str(e)}")
        
        add_button = ctk.CTkButton(
            button_frame,
            text="Add Order",
            command=add_order
        )
        add_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _show_message(self, message: str) -> str:
        """
        Show a message in the UI.
        
        Args:
            message: Message to display
            
        Returns:
            The message that was displayed
        """
        # Create message label if it doesn't exist
        if not hasattr(self, 'message_label'):
            self.message_label = ctk.CTkLabel(
                self.order_frame,
                text="",
                font=ctk.CTkFont(size=12)
            )
            self.message_label.pack(fill="x", padx=10, pady=5)
            
        # Show message
        self.message_label.configure(text=message)
        self.message_label.pack(fill="x", padx=10, pady=5)
        
        return message
    
    def get_message(self) -> str:
        """
        Get the current message text.
        
        Returns:
            Current message text
        """
        if hasattr(self, 'message_label'):
            return self.message_label.cget("text")
        return ""
    
    def _clear_message(self):
        """Clear the message in the UI."""
        if hasattr(self, 'message_label'):
            self.message_label.configure(text="")
            self.message_label.pack_forget()
    
    def _prompt_symbol_mapping(self, selected_order_ids: List[int]):
        """
        Prompt user to select the correct trading pair for an invalid symbol.
        
        Args:
            selected_order_ids: List of selected order IDs
        """
        if not self._api_client:
            self._show_message("API client not available.")
            return
            
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Symbol Mapping")
        dialog.geometry("500x500")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Symbol Mapping for {self.symbol}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create info label
        info_label = ctk.CTkLabel(
            main_frame,
            text=f"The symbol '{self.symbol}' is not recognized by the Binance API.\n"
                 "Please select the correct trading pair from the list below:",
            wraplength=450
        )
        info_label.pack(pady=(0, 20))
        
        # Create search frame
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.pack(side="left", padx=10)
        
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, width=300, textvariable=search_var)
        search_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Create list frame
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Create scrollable frame for trading pairs
        pairs_frame = ctk.CTkScrollableFrame(list_frame, width=450, height=200)
        pairs_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Get all trading pairs
        trading_pairs = self._api_client.get_all_trading_pairs()
        
        # Filter by base asset if possible
        base_asset = self.symbol[-4:] if self.symbol[-4:] in ['USDT', 'USDC', 'BUSD'] else self.symbol[-3:]
        quote_asset = self.symbol[:-len(base_asset)]
        
        # Try to find pairs with the same quote asset
        relevant_pairs = [pair for pair in trading_pairs if quote_asset in pair]
        
        # If no relevant pairs found, show all pairs
        if not relevant_pairs:
            relevant_pairs = trading_pairs
        
        # Sort pairs by relevance
        relevant_pairs.sort(key=lambda x: (0 if quote_asset in x else 1, x))
        
        # Create radio buttons for trading pairs
        pair_var = ctk.StringVar(value="")
        pair_buttons = []
        
        def update_pairs(*args):
            search_text = search_var.get().upper()
            
            # Hide all buttons
            for button in pair_buttons:
                button.pack_forget()
            
            # Show matching buttons
            for button in pair_buttons:
                if search_text in button.cget("text"):
                    button.pack(anchor="w", padx=10, pady=2)
        
        # Create radio buttons
        for pair in relevant_pairs:
            radio = ctk.CTkRadioButton(
                pairs_frame,
                text=pair,
                variable=pair_var,
                value=pair
            )
            radio.pack(anchor="w", padx=10, pady=2)
            pair_buttons.append(radio)
        
        # Bind search entry to update pairs
        search_var.trace_add("write", update_pairs)
        
        # Manual price option
        manual_price_frame = ctk.CTkFrame(main_frame)
        manual_price_frame.pack(fill="x", pady=(0, 20))
        
        manual_price_label = ctk.CTkLabel(manual_price_frame, text="Or enter current price manually:")
        manual_price_label.pack(side="left", padx=10)
        
        manual_price_entry = ctk.CTkEntry(manual_price_frame, width=150)
        manual_price_entry.pack(side="right", padx=10)
        
        # Error label
        error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        error_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Save mapping function
        def save_mapping():
            try:
                selected_pair = pair_var.get()
                manual_price_str = manual_price_entry.get()
                
                # Check if a pair is selected or manual price is entered
                if not selected_pair and not manual_price_str:
                    error_label.configure(text="Please select a trading pair or enter a manual price")
                    return
                
                # If manual price is entered, validate it
                manual_price = None
                if manual_price_str:
                    try:
                        manual_price = float(manual_price_str)
                        if manual_price <= 0:
                            error_label.configure(text="Price must be greater than zero")
                            return
                    except ValueError:
                        error_label.configure(text="Price must be a number")
                        return
                
                # If a pair is selected, add symbol mapping
                if selected_pair:
                    self._api_client.add_symbol_mapping(self.symbol, selected_pair)
                    
                    # Calculate metrics with the mapped symbol
                    metrics = self._api_client.calculate_position_metrics(self.symbol, selected_order_ids)
                    
                    # Update metrics in UI
                    self._update_metrics(metrics)
                    
                    # Show success message
                    self._show_message(f"Using {selected_pair} for {self.symbol}")
                    self.after(2000, lambda: self._clear_message())
                else:
                    # Calculate with manual price
                    metrics = self._api_client.calculate_position_metrics(
                        self.symbol,
                        selected_order_ids,
                        manual_price=manual_price
                    )
                    
                    # Update metrics in UI
                    self._update_metrics(metrics)
                    
                    # Show success message
                    self._show_message(f"Using manual price: {format_currency(manual_price)}")
                    self.after(2000, lambda: self._clear_message())
                
                # Close dialog
                dialog.destroy()
                
            except Exception as e:
                error_label.configure(text=f"Error: {str(e)}")
        
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=save_mapping
        )
        save_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set focus to search entry
        search_entry.focus_set()
    
    def _prompt_manual_price(self, selected_order_ids: List[int]):
        """
        Prompt user to enter current price manually for invalid symbols.
        
        Args:
            selected_order_ids: List of selected order IDs
        """
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Manual Price Entry")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Manual Price Entry for {self.symbol}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create info label
        info_label = ctk.CTkLabel(
            main_frame,
            text="This symbol cannot be queried through the Binance API.\n"
                 "Please enter the current price manually:",
            wraplength=350
        )
        info_label.pack(pady=(0, 20))
        
        # Price entry
        price_frame = ctk.CTkFrame(main_frame)
        price_frame.pack(fill="x", pady=(0, 20))
        
        price_label = ctk.CTkLabel(price_frame, text="Current Price:")
        price_label.pack(side="left", padx=10)
        
        price_entry = ctk.CTkEntry(price_frame, width=150)
        price_entry.pack(side="right", padx=10)
        
        # Error label
        error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        error_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Calculate function
        def calculate_with_manual_price():
            try:
                # Get price
                price_str = price_entry.get()
                
                # Validate price
                if not price_str:
                    error_label.configure(text="Price is required")
                    return
                    
                try:
                    price = float(price_str)
                except ValueError:
                    error_label.configure(text="Price must be a number")
                    return
                
                if price <= 0:
                    error_label.configure(text="Price must be greater than zero")
                    return
                
                # Calculate metrics with manual price
                if self._api_client:
                    metrics = self._api_client.calculate_position_metrics(
                        self.symbol,
                        selected_order_ids,
                        manual_price=price,
                        manual_orders=self.orders
                    )
                    
                    # Update metrics in UI
                    self._update_metrics(metrics)
                    
                    # Close dialog
                    dialog.destroy()
                    
                    # Show success message
                    self._show_message(f"Calculated with manual price: {format_currency(price)}")
                    self.after(2000, lambda: self._clear_message())
                else:
                    error_label.configure(text="API client not available")
            except Exception as e:
                error_label.configure(text=f"Error: {str(e)}")
        
        calculate_button = ctk.CTkButton(
            button_frame,
            text="Calculate",
            command=calculate_with_manual_price
        )
        calculate_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _change_trading_pair(self):
        """Open dialog to select a different trading pair for the same asset."""
        if not self.symbol or not self._api_client:
            return
            
        # Extract base and quote assets
        base_asset = self.symbol[-4:] if self.symbol[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else self.symbol[-3:]
        quote_asset = self.symbol[:-len(base_asset)]
        
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Trading Pair")
        dialog.geometry("500x500")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Select Trading Pair for {quote_asset}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create info label
        info_label = ctk.CTkLabel(
            main_frame,
            text=f"Current pair: {quote_asset}/{base_asset}\n"
                 "Select a different trading pair from the list below:",
            wraplength=450
        )
        info_label.pack(pady=(0, 20))
        
        # Create search frame
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.pack(side="left", padx=10)
        
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, width=300, textvariable=search_var)
        search_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Create list frame
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Create scrollable frame for trading pairs
        pairs_frame = ctk.CTkScrollableFrame(list_frame, width=450, height=200)
        pairs_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Get all trading pairs
        trading_pairs = self._api_client.get_all_trading_pairs()
        
        # Filter by quote asset
        relevant_pairs = [pair for pair in trading_pairs if quote_asset in pair]
        
        # Add BTC pairs if not already included
        btc_pairs = [pair for pair in trading_pairs if pair.endswith('BTC') and quote_asset in pair]
        for pair in btc_pairs:
            if pair not in relevant_pairs:
                relevant_pairs.append(pair)
        
        # If no relevant pairs found, show all pairs
        if not relevant_pairs:
            relevant_pairs = trading_pairs
        
        # Sort pairs by relevance
        relevant_pairs.sort(key=lambda x: (0 if quote_asset in x else 1, x))
        
        # Create radio buttons for trading pairs
        pair_var = ctk.StringVar(value=self.symbol)
        pair_buttons = []
        
        def update_pairs(*args):
            search_text = search_var.get().upper()
            
            # Hide all buttons
            for button in pair_buttons:
                button.pack_forget()
            
            # Show matching buttons
            for button in pair_buttons:
                if search_text in button.cget("text"):
                    button.pack(anchor="w", padx=10, pady=2)
        
        # Create radio buttons
        for pair in relevant_pairs:
            radio = ctk.CTkRadioButton(
                pairs_frame,
                text=pair,
                variable=pair_var,
                value=pair
            )
            radio.pack(anchor="w", padx=10, pady=2)
            pair_buttons.append(radio)
        
        # Bind search entry to update pairs
        search_var.trace_add("write", update_pairs)
        
        # Error label
        error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        error_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Switch pair function
        def switch_pair():
            try:
                selected_pair = pair_var.get()
                
                # Check if a different pair is selected
                if selected_pair == self.symbol:
                    error_label.configure(text="Please select a different trading pair")
                    return
                
                # Get the current asset detail
                asset_detail = self
                
                # Get the main window
                main_window = self.winfo_toplevel()
                
                # Save as preferred pair
                if self._api_client:
                    # Extract base and quote assets from the selected pair
                    base_asset = selected_pair[-4:] if selected_pair[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else selected_pair[-3:]
                    quote_asset = selected_pair[:-len(base_asset)]
                    
                    # Save preference
                    self._api_client.set_preferred_pair(quote_asset, selected_pair)
                
                # Switch to the new pair
                if hasattr(main_window, '_update_asset'):
                    main_window._update_asset(selected_pair)
                    
                    # Show success message
                    self._show_message(f"Switched to {quote_asset}/{base_asset} and set as preferred pair")
                    self.after(2000, lambda: self._clear_message())
                    
                    # Close dialog
                    dialog.destroy()
                else:
                    error_label.configure(text="Could not switch trading pair")
            except Exception as e:
                error_label.configure(text=f"Error: {str(e)}")
        
        switch_button = ctk.CTkButton(
            button_frame,
            text="Switch Pair",
            command=switch_pair
        )
        switch_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set focus to search entry
        search_entry.focus_set()
    
    def _set_price_alert(self):
        """Open dialog to set a price alert."""
        if not self.symbol or not self.metrics:
            return
            
        # Get current price
        current_price = self.metrics.get('current_price', 0)
        if current_price <= 0:
            self._show_message("Cannot set alert: Current price not available")
            return
            
        # Extract base and quote assets
        base_asset = self.symbol[-4:] if self.symbol[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else self.symbol[-3:]
        quote_asset = self.symbol[:-len(base_asset)]
        
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Set Price Alert")
        dialog.geometry("400x400")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Set Price Alert for {quote_asset}/{base_asset}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Current price info
        current_price_frame = ctk.CTkFrame(main_frame)
        current_price_frame.pack(fill="x", pady=(0, 20))
        
        current_price_label = ctk.CTkLabel(
            current_price_frame,
            text=f"Current Price: {format_currency(current_price)}"
        )
        current_price_label.pack(pady=10)
        
        # Alert type frame
        alert_type_frame = ctk.CTkFrame(main_frame)
        alert_type_frame.pack(fill="x", pady=(0, 20))
        
        alert_type_label = ctk.CTkLabel(alert_type_frame, text="Alert Type:")
        alert_type_label.pack(anchor="w", padx=10, pady=5)
        
        alert_type_var = ctk.StringVar(value="above")
        
        above_radio = ctk.CTkRadioButton(
            alert_type_frame,
            text="Price rises above",
            variable=alert_type_var,
            value="above"
        )
        above_radio.pack(anchor="w", padx=20, pady=2)
        
        below_radio = ctk.CTkRadioButton(
            alert_type_frame,
            text="Price drops below",
            variable=alert_type_var,
            value="below"
        )
        below_radio.pack(anchor="w", padx=20, pady=2)
        
        # Price entry frame
        price_frame = ctk.CTkFrame(main_frame)
        price_frame.pack(fill="x", pady=(0, 20))
        
        price_label = ctk.CTkLabel(price_frame, text="Alert Price:")
        price_label.pack(side="left", padx=10)
        self.is_consolidated_view = False
        self.original_symbol = ""
        
        # Add title label
        self.title_label = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5))
        
        # Add title label
        self.title_label = ctk.CTkLabel(
            self.metrics_frame,
            text="",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5))
        
        price_entry = ctk.CTkEntry(price_frame, width=150)
        price_entry.insert(0, str(current_price))  # Default to current price
        price_entry.pack(side="right", padx=10)
        
        # Notification options
        notification_frame = ctk.CTkFrame(main_frame)
        notification_frame.pack(fill="x", pady=(0, 20))
        
        notification_label = ctk.CTkLabel(notification_frame, text="Notification Options:")
        notification_label.pack(anchor="w", padx=10, pady=5)
        
        sound_var = ctk.BooleanVar(value=True)
        sound_cb = ctk.CTkCheckBox(
            notification_frame,
            text="Play sound",
            variable=sound_var
        )
        sound_cb.pack(anchor="w", padx=20, pady=2)
        
        popup_var = ctk.BooleanVar(value=True)
        popup_cb = ctk.CTkCheckBox(
            notification_frame,
            text="Show popup",
            variable=popup_var
        )
        popup_cb.pack(anchor="w", padx=20, pady=2)
        
        # Error label
        error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        error_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Set alert function
        def set_alert():
            try:
                # Get values
                alert_type = alert_type_var.get()
                price_str = price_entry.get()
                play_sound = sound_var.get()
                show_popup = popup_var.get()
                
                # Validate price
                if not price_str:
                    error_label.configure(text="Price is required")
                    return
                    
                try:
                    price = float(price_str)
                except ValueError:
                    error_label.configure(text="Price must be a number")
                    return
                
                if price <= 0:
                    error_label.configure(text="Price must be greater than zero")
                    return
                
                # Validate alert makes sense
                if alert_type == "above" and price <= current_price:
                    error_label.configure(text="Alert price must be above current price")
                    return
                    
                if alert_type == "below" and price >= current_price:
                    error_label.configure(text="Alert price must be below current price")
                    return
                
                # Create alert
                alert = {
                    'symbol': self.symbol,
                    'type': alert_type,
                    'price': price,
                    'current_price': current_price,
                    'sound': play_sound,
                    'popup': show_popup,
                    'created_at': time.time()
                }
                
                # Store alert
                if not hasattr(self, 'price_alerts'):
                    self.price_alerts = []
                    
                self.price_alerts.append(alert)
                
                # Start alert checking if not already running
                self._start_alert_checking()
                
                # Close dialog
                dialog.destroy()
                
                # Show success message
                self._show_message(f"Price alert set: {alert_type} {format_currency(price)}")
                self.after(2000, lambda: self._clear_message())
                
            except Exception as e:
                error_label.configure(text=f"Error: {str(e)}")
        
        set_button = ctk.CTkButton(
            button_frame,
            text="Set Alert",
            command=set_alert
        )
        set_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _start_alert_checking(self):
        """Start checking for price alerts."""
        if hasattr(self, '_alert_checking') and self._alert_checking:
            return  # Already running
            
        self._alert_checking = True
        
        def check_alerts():
            while hasattr(self, '_alert_checking') and self._alert_checking:
                try:
                    if hasattr(self, 'price_alerts') and self.price_alerts and self.symbol:
                        current_price = self.metrics.get('current_price', 0)
                        if current_price > 0:
                            # Check each alert
                            triggered_alerts = []
                            for alert in self.price_alerts:
                                if alert['symbol'] == self.symbol:
                                    if alert['type'] == 'above' and current_price >= alert['price']:
                                        triggered_alerts.append(alert)
                                    elif alert['type'] == 'below' and current_price <= alert['price']:
                                        triggered_alerts.append(alert)
                            
                            # Handle triggered alerts
                            for alert in triggered_alerts:
                                self._trigger_alert(alert, current_price)
                                self.price_alerts.remove(alert)
                                
                except Exception as e:
                    print(f"Error checking alerts: {e}")
                    
                # Sleep for 1 second
                time.sleep(1)
        
        # Start checking thread
        threading.Thread(target=check_alerts, daemon=True).start()
    
    def _trigger_alert(self, alert: Dict, current_price: float):
        """
        Trigger a price alert.
        
        Args:
            alert: Alert dictionary
            current_price: Current price
        """
        # Extract info
        symbol = alert['symbol']
        alert_type = alert['type']
        alert_price = alert['price']
        play_sound = alert.get('sound', True)
        show_popup = alert.get('popup', True)
        
        # Extract base and quote assets
        base_asset = symbol[-4:] if symbol[-4:] in ['USDT', 'USDC', 'BUSD', 'USDK'] else symbol[-3:]
        quote_asset = symbol[:-len(base_asset)]
        
        # Create message
        message = f"PRICE ALERT: {quote_asset}/{base_asset}\n"
        if alert_type == 'above':
            message += f"Price has risen above {format_currency(alert_price)}\n"
        else:
            message += f"Price has dropped below {format_currency(alert_price)}\n"
        message += f"Current price: {format_currency(current_price)}"
        
        # Show popup
        if show_popup:
            self.after(0, lambda: self._show_alert_popup(message))
        
        # Play sound
        if play_sound:
            self.after(0, lambda: self._play_alert_sound())
    
    def _show_alert_popup(self, message: str):
        """
        Show alert popup.
        
        Args:
            message: Alert message
        """
        # Create popup
        popup = ctk.CTkToplevel(self)
        popup.title("Price Alert")
        popup.geometry("400x200")
        popup.resizable(False, False)
        popup.attributes('-topmost', True)  # Keep on top
        
        # Create main frame
        main_frame = ctk.CTkFrame(popup)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create alert icon
        alert_label = ctk.CTkLabel(
            main_frame,
            text="🔔",
            font=ctk.CTkFont(size=32)
        )
        alert_label.pack(pady=(0, 10))
        
        # Create message
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            wraplength=350
        )
        message_label.pack(pady=(0, 20))
        
        # Close button
        close_button = ctk.CTkButton(
            main_frame,
            text="Close",
            command=popup.destroy
        )
        close_button.pack(pady=(0, 10))
        
        # Center popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")
        
        # Auto-close after 10 seconds
        popup.after(10000, popup.destroy)
    
    def _play_alert_sound(self):
        """Play alert sound."""
        try:
            # Try to use winsound on Windows
            import winsound
            winsound.Beep(1000, 500)  # 1000 Hz for 500 ms
        except:
            try:
                # Try to use system bell
                import os
                os.system('echo -e "\a"')
            except:
                # If all else fails, print to console
                print("\a")  # ASCII bell character
    
    def _toggle_select_all(self):
        """Toggle select/deselect all orders."""
        if not self.symbol or not self.orders:
            return
            
        # Get current button text
        is_select_all = self.select_all_btn.cget("text") == "Select All"
        
        # Update button text
        self.select_all_btn.configure(text="Deselect All" if is_select_all else "Select All")
        
        # Update order inclusion
        if self.symbol not in self.include_orders:
            self.include_orders[self.symbol] = {}
            
        # Toggle all orders
        for order in self.orders:
            order_id = order['orderId']
            self.include_orders[self.symbol][order_id] = is_select_all
            
        # Update order table
        self.order_table.update_orders(self.orders, self.include_orders.get(self.symbol, {}))
        
        # Recalculate metrics if selecting all
        if is_select_all:
            self._calculate_selected()
    
    def _update_open_orders(self):
        """Update open orders display."""
        if not self.symbol or not self.metrics or not hasattr(self, 'open_orders_content'):
            return
            
        # Get open orders from metrics
        open_orders = self.metrics.get('open_orders', [])
        
        # Clear existing content
        for widget in self.open_orders_content.winfo_children():
            widget.destroy()
            
        # Show "No open orders" if there are none
        if not open_orders:
            self.no_open_orders_label = ctk.CTkLabel(
                self.open_orders_content,
                text="No open orders",
                font=ctk.CTkFont(size=12)
            )
            self.no_open_orders_label.pack(padx=10, pady=10)
            return
            
        # Extract base and quote assets
        base_asset = self.symbol[-4:] if self.symbol[-4:] in ['USDT', 'USDC', 'BUSD'] else self.symbol[-3:]
        quote_asset = self.symbol[:-len(base_asset)]
        
        # Create a table for open orders
        order_table = ctk.CTkFrame(self.open_orders_content)
        order_table.pack(fill="x", padx=10, pady=5)
        
        # Configure grid
        order_table.grid_columnconfigure(0, weight=1)  # Side
        order_table.grid_columnconfigure(1, weight=1)  # Price
        order_table.grid_columnconfigure(2, weight=1)  # Amount
        order_table.grid_columnconfigure(3, weight=1)  # Total
        
        # Create header
        ctk.CTkLabel(order_table, text="Side", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(order_table, text="Price", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(order_table, text="Amount", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkLabel(order_table, text="Total", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=5)
        
        # Add rows for each open order
        for i, order in enumerate(open_orders):
            # Side (with color)
            side = order.get('side', '')
            side_color = "#4CAF50" if side == "BUY" else "#F44336"
            side_label = ctk.CTkLabel(order_table, text=side, text_color=side_color)
            side_label.grid(row=i+1, column=0, padx=5, pady=5)
            
            # Price
            price = float(order.get('price', 0))
            price_label = ctk.CTkLabel(order_table, text=format_currency(price))
            price_label.grid(row=i+1, column=1, padx=5, pady=5)
            
            # Amount (locked quantity)
            locked_qty = float(order.get('lockedQty', 0))
            amount_label = ctk.CTkLabel(
                order_table,
                text=f"{format_crypto_amount(locked_qty)} {quote_asset}",
                text_color="#FFA500"  # Orange color for locked amounts
            )
            amount_label.grid(row=i+1, column=2, padx=5, pady=5)
            
            # Total
            total = price * locked_qty
            total_label = ctk.CTkLabel(order_table, text=format_currency(total))
            total_label.grid(row=i+1, column=3, padx=5, pady=5)
    
    def _update_metrics(self, metrics: Dict):
        """
        Update metrics display with new metrics.
        
        Args:
            metrics: New metrics dictionary
        """
        self.metrics = metrics
        self._update_ui()


class OrderTable(ctk.CTkScrollableFrame):
    """
    Table for displaying order history.
    """
    
    def __init__(self, master, toggle_callback, **kwargs):
        """
        Initialize order table.
        
        Args:
            master: Parent widget
            toggle_callback: Callback for order toggle
            **kwargs: Additional arguments for CTkScrollableFrame
        """
        super().__init__(master, **kwargs)
        
        # Store callback
        self.toggle_callback = toggle_callback
        
        # Create header
        self._create_header()
        
        # Store order rows
        self.order_rows = {}
    
    def _create_header(self):
        """Create table header."""
        # Create header frame
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=(0, 5))
        
        # Configure grid
        header.grid_columnconfigure(0, weight=0)  # Include checkbox
        header.grid_columnconfigure(1, weight=1)  # Date
        header.grid_columnconfigure(2, weight=1)  # Side
        header.grid_columnconfigure(3, weight=1)  # Price
        header.grid_columnconfigure(4, weight=1)  # Amount
        header.grid_columnconfigure(5, weight=1)  # Total
        header.grid_columnconfigure(6, weight=0)  # Actions
        
        # Create header labels
        ctk.CTkLabel(header, text="", width=30).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(header, text="Date", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(header, text="Side", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkLabel(header, text="Price", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkLabel(header, text="Amount", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=5, pady=5)
        ctk.CTkLabel(header, text="Total", font=ctk.CTkFont(weight="bold")).grid(row=0, column=5, padx=5, pady=5)
        ctk.CTkLabel(header, text="Actions", font=ctk.CTkFont(weight="bold")).grid(row=0, column=6, padx=5, pady=5)
    
    def update_orders(self, orders: List[Dict], include_orders: Dict[int, bool]):
        """
        Update order table with new orders.
        
        Args:
            orders: List of order dictionaries
            include_orders: Dictionary of order inclusion status
        """
        # Clear existing rows
        for row in self.order_rows.values():
            row.destroy()
        self.order_rows = {}
        
        # Add new rows
        for i, order in enumerate(orders):
            order_id = order['orderId']
            include = include_orders.get(order_id, True)
            
            # Create row
            row = OrderRow(
                self,
                order,
                include,
                lambda oid=order_id, inc=include: self.toggle_callback(oid, not inc)
            )
            row.pack(fill="x", pady=2)
            
            self.order_rows[order_id] = row


class OrderRow(ctk.CTkFrame):
    """
    Row in the order table.
    """
    
    def __init__(self, master, order: Dict, include: bool, toggle_callback, **kwargs):
        """
        Initialize order row.
        
        Args:
            master: Parent widget
            order: Order dictionary
            include: Whether to include the order in calculations
            toggle_callback: Callback for order toggle
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Store properties
        self.order = order
        self.include = include
        self.toggle_callback = toggle_callback
        
        # Configure frame
        self.configure(corner_radius=6)
        
        # Create widgets
        self._create_widgets()
    
    def _create_widgets(self):
        """Create row widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)  # Include checkbox
        self.grid_columnconfigure(1, weight=1)  # Date
        self.grid_columnconfigure(2, weight=1)  # Side
        self.grid_columnconfigure(3, weight=1)  # Price
        self.grid_columnconfigure(4, weight=1)  # Amount
        self.grid_columnconfigure(5, weight=1)  # Total
        self.grid_columnconfigure(6, weight=0)  # Delete button (for manual orders)
        
        # Include checkbox
        self.include_var = ctk.BooleanVar(value=self.include)
        include_cb = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.include_var,
            command=self.toggle_callback,
            width=30,
            checkbox_width=20,
            checkbox_height=20
        )
        include_cb.grid(row=0, column=0, padx=5, pady=5)
        self.is_consolidated_view = False
        self.original_symbol = ""
        
        # Date
        date_label = ctk.CTkLabel(self, text=self.order.get('time', ''))
        date_label.grid(row=0, column=1, padx=5, pady=5)
        
        # Side (with color)
        side = self.order.get('side', '')
        side_color = "#4CAF50" if side == "BUY" else "#F44336"
        side_label = ctk.CTkLabel(self, text=side, text_color=side_color)
        side_label.grid(row=0, column=2, padx=5, pady=5)
        
        # Price
        price = float(self.order.get('avgPrice', 0))
        price_label = ctk.CTkLabel(self, text=format_currency(price))
        price_label.grid(row=0, column=3, padx=5, pady=5)
        
        # Amount
        amount = float(self.order.get('executedQty', 0))
        amount_label = ctk.CTkLabel(self, text=format_crypto_amount(amount))
        amount_label.grid(row=0, column=4, padx=5, pady=5)
        
        # Total
        total = float(self.order.get('cummulativeQuoteQty', 0))
        total_label = ctk.CTkLabel(self, text=format_currency(total))
        total_label.grid(row=0, column=5, padx=5, pady=5)
        
        # Delete button (only for manual orders)
        if self.order.get('isManual', False):
            delete_button = ctk.CTkButton(
                self,
                text="Delete",
                width=60,
                height=24,
                fg_color="#F44336",
                hover_color="#D32F2F",
                command=self._delete_order
            )
            delete_button.grid(row=0, column=6, padx=5, pady=5)
    
    def _delete_order(self):
        """Delete this manual order."""
        # Get the parent widget (OrderTable)
        order_table = self.master
        
        # Get the parent of OrderTable (AssetDetailFrame)
        asset_detail = order_table.master
        
        # Confirm deletion
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Deletion")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create message
        message = ctk.CTkLabel(
            main_frame,
            text="Are you sure you want to delete this manual order?\nThis action cannot be undone.",
            wraplength=350
        )
        message.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Delete function
        def confirm_delete():
            try:
                # Delete from API client
                if hasattr(asset_detail, '_api_client') and asset_detail._api_client:
                    asset_detail._api_client.delete_manual_order(
                        self.order['symbol'],
                        self.order['orderId']
                    )
                
                # Remove from orders list
                if hasattr(asset_detail, 'orders'):
                    asset_detail.orders = [
                        order for order in asset_detail.orders
                        if order.get('orderId') != self.order['orderId']
                    ]
                
                # Remove from include_orders
                if hasattr(asset_detail, 'include_orders') and self.order['symbol'] in asset_detail.include_orders:
                    if self.order['orderId'] in asset_detail.include_orders[self.order['symbol']]:
                        del asset_detail.include_orders[self.order['symbol']][self.order['orderId']]
                
                # Update order table
                order_table.update_orders(asset_detail.orders, asset_detail.include_orders.get(self.order['symbol'], {}))
                
                # Show success message
                asset_detail._show_message("Manual order deleted successfully")
                asset_detail.after(2000, lambda: asset_detail._clear_message())
                
                # Close dialog
                dialog.destroy()
                
            except Exception as e:
                # Show error message
                error_label = ctk.CTkLabel(
                    main_frame,
                    text=f"Error: {str(e)}",
                    text_color="#F44336"
                )
                error_label.pack(pady=(0, 10))
        
        delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            fg_color="#F44336",
            hover_color="#D32F2F",
            command=confirm_delete
        )
        delete_button.pack(side="right", padx=10, pady=10, expand=True)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_toplevel().winfo_rootx() + (self.winfo_toplevel().winfo_width() // 2) - (width // 2)
        y = self.winfo_toplevel().winfo_rooty() + (self.winfo_toplevel().winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")