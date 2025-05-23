import os
import importlib.util
import customtkinter as ctk
from typing import Optional, Dict, List, Callable
import json
import threading

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

# Get required functions
encrypt_credentials = core_auth.encrypt_credentials


class PinDialog(ctk.CTkToplevel):
    """
    Dialog for entering PIN to decrypt API credentials.
    """
    
    def __init__(self, parent):
        """
        Initialize PIN dialog.
        
        Args:
            parent: Parent window
        """
        super().__init__(parent)
        
        # Set dialog properties
        self.title("Enter PIN")
        self.geometry("300x200")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Initialize result
        self.pin = None
        
        # Create widgets
        self._create_widgets()
        
        # Center dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set focus to PIN entry
        self.pin_entry.focus_set()
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Create main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create label
        label = ctk.CTkLabel(
            main_frame,
            text="Enter your 4-digit PIN",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.pack(pady=(0, 20))
        
        # Create PIN entry
        self.pin_entry = ctk.CTkEntry(main_frame, show="*", width=100)
        self.pin_entry.pack(pady=(0, 20))
        
        # Create error label
        self.error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        self.error_label.pack(pady=(0, 20))
        
        # Create buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy
        )
        cancel_button.pack(side="left", padx=5, pady=5, expand=True)
        
        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            command=self._on_ok
        )
        ok_button.pack(side="right", padx=5, pady=5, expand=True)
        
        # Bind enter key to OK button
        self.bind("<Return>", lambda event: self._on_ok())
    
    def _on_ok(self):
        """Handle OK button click."""
        pin = self.pin_entry.get()
        
        # Validate PIN
        if not pin.isdigit() or len(pin) != 4:
            self.error_label.configure(text="PIN must be 4 digits")
            return
        
        # Set result and close dialog
        self.pin = pin
        self.destroy()


class SetupDialog(ctk.CTkToplevel):
    """
    Dialog for initial setup of API credentials.
    """
    
    def __init__(self, parent):
        """
        Initialize setup dialog.
        
        Args:
            parent: Parent window
        """
        super().__init__(parent)
        
        # Set dialog properties
        self.title("Setup Binance API")
        self.geometry("400x400")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Initialize result
        self.api_key = None
        self.api_secret = None
        self.pin = None
        
        # Create widgets
        self._create_widgets()
        
        # Center dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set focus to API key entry
        self.api_key_entry.focus_set()
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Create main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title label
        title_label = ctk.CTkLabel(
            main_frame,
            text="Binance API Setup",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create info label
        info_label = ctk.CTkLabel(
            main_frame,
            text="Please enter your Binance API credentials.\n"
                 "For security, use READ-ONLY API keys only.",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        info_label.pack(pady=(0, 20), fill="x")
        
        # Create API key entry
        api_key_label = ctk.CTkLabel(main_frame, text="API Key:")
        api_key_label.pack(anchor="w")
        
        self.api_key_entry = ctk.CTkEntry(main_frame, width=360, show="•")
        self.api_key_entry.pack(pady=(0, 10), fill="x")
        
        # Create API secret entry
        api_secret_label = ctk.CTkLabel(main_frame, text="API Secret:")
        api_secret_label.pack(anchor="w")
        
        self.api_secret_entry = ctk.CTkEntry(main_frame, width=360, show="•")
        self.api_secret_entry.pack(pady=(0, 20), fill="x")
        
        # Create PIN entry
        pin_label = ctk.CTkLabel(main_frame, text="Create 4-digit PIN:")
        pin_label.pack(anchor="w")
        
        self.pin_entry = ctk.CTkEntry(main_frame, width=100, show="*")
        self.pin_entry.pack(pady=(0, 10))
        
        # Create PIN confirmation entry
        pin_confirm_label = ctk.CTkLabel(main_frame, text="Confirm PIN:")
        pin_confirm_label.pack(anchor="w")
        
        self.pin_confirm_entry = ctk.CTkEntry(main_frame, width=100, show="*")
        self.pin_confirm_entry.pack(pady=(0, 20))
        
        # Create error label
        self.error_label = ctk.CTkLabel(
            main_frame,
            text="",
            text_color="#F44336"
        )
        self.error_label.pack(pady=(0, 20))
        
        # Create buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy
        )
        cancel_button.pack(side="left", padx=5, pady=5, expand=True)
        
        ok_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save
        )
        ok_button.pack(side="right", padx=5, pady=5, expand=True)
    
    def _on_save(self):
        """Handle Save button click."""
        api_key = self.api_key_entry.get()
        api_secret = self.api_secret_entry.get()
        pin = self.pin_entry.get()
        pin_confirm = self.pin_confirm_entry.get()
        
        # Validate inputs
        if not api_key:
            self.error_label.configure(text="API Key is required")
            return
        
        if not api_secret:
            self.error_label.configure(text="API Secret is required")
            return
        
        if not pin.isdigit() or len(pin) != 4:
            self.error_label.configure(text="PIN must be 4 digits")
            return
        
        if pin != pin_confirm:
            self.error_label.configure(text="PINs do not match")
            return
        
        # Encrypt and save credentials
        if encrypt_credentials(api_key, api_secret, pin):
            # Set result and close dialog
            self.api_key = api_key
            self.api_secret = api_secret
            self.pin = pin
            self.destroy()
        else:
            self.error_label.configure(text="Failed to save credentials")


class PairSelectionDialog(ctk.CTkToplevel):
    """
    Dialog for selecting trading pairs to display.
    """
    
    def __init__(self, parent, api_client, balances: List[Dict], callback: Callable):
        """
        Initialize pair selection dialog.
        
        Args:
            parent: Parent window
            api_client: API client instance
            balances: List of balance dictionaries
            callback: Callback function to call with selected pairs
        """
        super().__init__(parent)
        
        # Set dialog properties
        self.title("Select Trading Pairs")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Store parameters
        self.api_client = api_client
        self.balances = balances
        self.callback = callback
        
        # Initialize variables
        self.selected_pairs = {}  # asset -> pair
        self.pair_vars = {}  # asset -> StringVar
        self.asset_frames = {}  # asset -> frame
        
        # Load saved preferences
        self._load_preferences()
        
        # Create widgets
        self._create_widgets()
        
        # Center dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _load_preferences(self):
        """Load saved pair preferences."""
        if self.api_client and hasattr(self.api_client, 'preferences'):
            self.saved_preferences = self.api_client.preferences.get('preferred_pairs', {})
        else:
            self.saved_preferences = {}
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Create main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create title label
        title_label = ctk.CTkLabel(
            main_frame,
            text="Select Trading Pairs to Display",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Create info label
        info_label = ctk.CTkLabel(
            main_frame,
            text="Choose which trading pair to display for each asset in your portfolio.",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        info_label.pack(pady=(0, 10), fill="x")
        
        # Create load saved button
        if self.saved_preferences:
            load_saved_button = ctk.CTkButton(
                main_frame,
                text="Load Saved Pairs",
                command=self._load_saved_pairs
            )
            load_saved_button.pack(pady=(0, 10))
        
        # Create scrollable frame for assets
        assets_frame = ctk.CTkScrollableFrame(main_frame, width=560, height=300)
        assets_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create asset frames
        self._create_asset_frames(assets_frame)
        
        # Create buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy
        )
        cancel_button.pack(side="left", padx=5, pady=5, expand=True)
        
        ok_button = ctk.CTkButton(
            button_frame,
            text="Apply",
            command=self._on_apply
        )
        ok_button.pack(side="right", padx=5, pady=5, expand=True)
    
    def _create_asset_frames(self, parent):
        """
        Create frames for each asset.
        
        Args:
            parent: Parent frame
        """
        # Get all trading pairs
        all_pairs = []
        if self.api_client:
            try:
                all_pairs = self.api_client.get_all_trading_pairs()
            except Exception as e:
                print(f"Error getting trading pairs: {e}")
        
        # Create frames for each asset
        for balance in self.balances:
            asset = balance['asset']
            
            # Skip stablecoins and very small balances
            if asset in ['USDT', 'USDC', 'BUSD', 'TUSD']:
                continue
                
            if float(balance['free']) < 0.00001 and float(balance['locked']) < 0.00001:
                continue
            
            # Create asset frame
            asset_frame = ctk.CTkFrame(parent)
            asset_frame.pack(fill="x", padx=5, pady=5)
            
            # Configure grid
            asset_frame.grid_columnconfigure(0, weight=0)  # Asset label
            asset_frame.grid_columnconfigure(1, weight=1)  # Pair dropdown
            
            # Create asset label
            asset_label = ctk.CTkLabel(
                asset_frame,
                text=f"{asset}:",
                font=ctk.CTkFont(weight="bold"),
                width=100
            )
            asset_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            
            # Find available pairs for this asset
            available_pairs = []
            base_currencies = ["USDT", "USDC", "BUSD", "BTC"]
            
            for base in base_currencies:
                pair = f"{asset}{base}"
                if pair in all_pairs:
                    available_pairs.append(pair)
            
            # If no pairs found, add a placeholder
            if not available_pairs:
                available_pairs = [f"{asset}USDT"]
            
            # Create pair variable
            pair_var = ctk.StringVar()
            
            # Set default value from saved preferences or first available pair
            default_pair = self.saved_preferences.get(asset, available_pairs[0])
            if default_pair not in available_pairs:
                default_pair = available_pairs[0]
                
            pair_var.set(default_pair)
            
            # Create pair dropdown
            pair_dropdown = ctk.CTkOptionMenu(
                asset_frame,
                values=available_pairs,
                variable=pair_var,
                width=200
            )
            pair_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            
            # Store references
            self.pair_vars[asset] = pair_var
            self.asset_frames[asset] = asset_frame
    
    def _load_saved_pairs(self):
        """Load saved pair preferences."""
        for asset, pair in self.saved_preferences.items():
            if asset in self.pair_vars:
                # Get available values
                dropdown = self.asset_frames[asset].winfo_children()[1]
                available_values = dropdown.cget("values")
                
                # Set value if available
                if pair in available_values:
                    self.pair_vars[asset].set(pair)
    
    def _on_apply(self):
        """Handle Apply button click."""
        # Collect selected pairs
        selected_pairs = {}
        for asset, var in self.pair_vars.items():
            selected_pairs[asset] = var.get()
        
        # Save preferences
        if self.api_client:
            for asset, pair in selected_pairs.items():
                self.api_client.set_preferred_pair(asset, pair)
        
        # Call callback
        self.callback(selected_pairs)
        
        # Close dialog
        self.destroy()