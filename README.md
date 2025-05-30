# Binance Portfolio Tracker A first try on fully AI generated software experiment.

A secure desktop Python application that connects to the Binance Spot API in read-only mode to track your cryptocurrency portfolio.

## Features

- **Secure API Access**: Stores API credentials with encryption using a 4-digit PIN
- **API Management**: Easily add new API keys or forget existing ones
- **Real-Time Portfolio Dashboard**: Shows current prices, holdings, and PnL calculations
- **Break-Even Price Calculation**: Calculates average buy price and break-even price
- **Order History**: View and filter your order history
- **Persistent Settings**: Saves your preferences and settings
- **Read-Only Operation**: Uses only read operations for security (works with any API permission level)

## Screenshots

(Screenshots will be added after the first release)

## Installation

### Prerequisites

- Python 3.10 or higher
- Binance account with API key (read-only permissions)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/binance-portfolio-tracker.git
   cd binance-portfolio-tracker
   ```

2. Install the required dependencies:
   ```
   pip install -r binance_tracker/requirements.txt
   ```

3. Run the application using the provided run script:
   ```
   python run_binance_tracker.py
   ```

## Import Structure and Compatibility

The application uses direct file imports rather than package-style imports to avoid common import issues in Python IDEs like PyCharm. This approach:

1. Makes the application more robust against import errors
2. Allows running the application from any directory
3. Eliminates the need for package installation or PYTHONPATH configuration

Each module uses a helper function `import_from_file()` to import other modules directly by file path, ensuring reliable imports regardless of how the application is launched.

## API Compatibility

The application is designed to work with different versions of the python-binance library:

1. **WebSocket Compatibility**: The code includes fallback mechanisms for different WebSocket implementations across various versions of the python-binance library
2. **API Method Compatibility**: Handles differences in API methods between versions (e.g., presence or absence of `get_api_permission_status`)
3. **Graceful Degradation**: If WebSocket functionality is not available, the application will automatically fall back to polling for price updates
4. **Error Handling**: Comprehensive error handling ensures the application continues to function even if certain API features are unavailable

These compatibility features make the application more resilient to changes in the underlying API and ensure it works across different environments.

## First-Time Setup

When you run the application for the first time, you'll need to:

1. Create an API key on Binance:
   - Log in to your Binance account
   - Go to API Management
   - Create a new API key
   - **Recommended**: For security, only enable "Read Info" permissions
   - Copy the API Key and Secret Key

2. Enter your API credentials in the setup dialog
3. Create a 4-digit PIN to secure your credentials
4. Your credentials will be encrypted and stored locally

## Usage

### Main Dashboard

- The sidebar shows all your assets with non-zero balances
- Click on an asset to view detailed information
- The main panel shows:
  - Current price (real-time updates)
  - Holdings amount
  - Average buy price
  - Break-even price
  - Profit/Loss calculation

### Order History

- View your order history for each asset
- Toggle orders to include/exclude them from calculations
- Select/deselect all orders with a single click
- Filter orders by time period (24h, 7d, 30d)
- Calculate metrics based on selected orders only
- Add manual orders for tracking off-exchange transactions
- Delete manual orders that are no longer needed
- Display open orders and locked amounts for each asset
- Support for Alpha tokens and other special symbols not available via API
- Symbol mapping for tokens with different trading pairs (e.g., AGLD/BTC instead of AGLD/USDC)
- Trading pair selection dialog at startup to choose which pairs to display
- Multiple base currencies including BTC, USDT, USDC, and BUSD
- Option to load previously saved pair preferences
- Persistent preferred trading pairs that are remembered between sessions
- Improved price fetching with multiple fallback methods for better reliability
- Enhanced decimal precision (8 decimal places) for all crypto values and amounts
- Price alerts with sound and popup notifications when price thresholds are reached
- Manual price entry for symbols that can't be queried through the API
- Persistent storage of manual orders and symbol mappings
- Sort orders by date, price, or amount

### API Management

- Click the "Manage API" button in the top menu
- View the current API connection status
- Add a new API key if needed
- Forget existing API credentials for security
- The application will automatically prompt for new API credentials if none are available

### Settings

- Switch between light and dark themes
- Change base currency (USDT, USDC, BUSD)
- Customize other preferences

## Security

This application is designed with security in mind:

- API credentials are encrypted using Fernet encryption
- Read-only API permissions are recommended but not required
- The application will never perform any trading or withdrawal operations
- API keys can be easily forgotten/removed through the API management interface
- All data is stored locally on your computer
- No data is sent to any external servers (except Binance API)

## Development

### Directory Structure

```
binance_tracker/
├── main.py                    # Entry point
├── core/
│   ├── auth.py                # PIN, encryption, credential validation
│   ├── api_client.py          # Binance API abstraction
│   └── calculator.py          # PnL, break-even, avg cost
├── data/
│   ├── config.json            # GUI and user settings
│   └── vault.dat              # Encrypted credentials
├── ui/
│   ├── main_window.py         # App layout
│   ├── widgets/               # Reusable GUI elements
│   └── dialogs.py             # PIN prompt, setup wizard
├── utils/
│   ├── logger.py              # Local debug log
│   └── threader.py            # Thread helper
└── requirements.txt
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is for informational purposes only. It is not financial advice. Use at your own risk.

The application is not affiliated with Binance. "Binance" is a trademark of Binance Holdings Limited.
