import os
import importlib.util
import customtkinter as ctk
from typing import Callable, Optional

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


class AssetButton(ctk.CTkFrame):
    """
    Custom button widget for displaying an asset in the sidebar.
    """
    
    def __init__(
        self,
        master,
        asset: str,
        symbol: str,
        balance: float,
        usd_value: float,
        command: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize asset button.
        
        Args:
            master: Parent widget
            asset: Asset code (e.g., 'BTC')
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            balance: Asset balance
            usd_value: USD value of the balance
            command: Callback function when button is clicked
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Store properties
        self.asset = asset
        self.symbol = symbol
        self.balance = balance
        self.usd_value = usd_value
        self.command = command
        self.selected = False
        
        # Configure frame
        self.configure(
            corner_radius=6,
            border_width=1,
            border_color=self._get_border_color(False)
        )
        
        # Create layout
        self._create_widgets()
        
        # Bind events
        self.bind("<Button-1>", self._on_click)
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)
    
    def _create_widgets(self):
        """Create button widgets."""
        # Create grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Asset name
        self.asset_label = ctk.CTkLabel(
            self,
            text=self.asset,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.asset_label.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))
        
        # USD value
        self.value_label = ctk.CTkLabel(
            self,
            text=format_currency(self.usd_value),
            font=ctk.CTkFont(size=12)
        )
        self.value_label.grid(row=0, column=1, sticky="e", padx=10, pady=(5, 0))
        
        # Balance
        self.balance_label = ctk.CTkLabel(
            self,
            text=format_crypto_amount(self.balance),
            font=ctk.CTkFont(size=12)
        )
        self.balance_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))
    
    def _on_click(self, event):
        """
        Handle click event.
        
        Args:
            event: Click event
        """
        if self.command:
            self.command()
    
    def set_selected(self, selected: bool):
        """
        Set selected state.
        
        Args:
            selected: Whether the button is selected
        """
        self.selected = selected
        self.configure(border_color=self._get_border_color(selected))
    
    def _get_border_color(self, selected: bool) -> str:
        """
        Get border color based on selected state.
        
        Args:
            selected: Whether the button is selected
            
        Returns:
            Border color
        """
        if selected:
            return "#1F6AA5"  # Blue
        else:
            return "#2B2B2B" if ctk.get_appearance_mode() == "dark" else "#DBDBDB"
    
    def update_balance(self, balance: float, usd_value: float):
        """
        Update balance and value.
        
        Args:
            balance: New balance
            usd_value: New USD value
        """
        self.balance = balance
        self.usd_value = usd_value
        
        self.balance_label.configure(text=format_crypto_amount(balance))
        self.value_label.configure(text=format_currency(usd_value))