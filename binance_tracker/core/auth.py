import os
import json
import base64
from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from binance.client import Client

# Constants
VAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vault.dat")
SALT_SIZE = 16
ITERATIONS = 100000


def _derive_key(pin: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive a Fernet key from a 4-digit PIN using PBKDF2.
    
    Args:
        pin: 4-digit PIN
        salt: Optional salt bytes, generated if not provided
        
    Returns:
        Tuple of (key, salt)
    """
    if not pin.isdigit() or len(pin) != 4:
        raise ValueError("PIN must be a 4-digit number")
        
    # Convert PIN to bytes
    pin_bytes = pin.encode()
    
    # Generate salt if not provided
    if salt is None:
        salt = os.urandom(SALT_SIZE)
    
    # Derive key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(pin_bytes))
    return key, salt


def encrypt_credentials(api_key: str, api_secret: str, pin: str) -> bool:
    """
    Encrypt Binance API credentials using a 4-digit PIN and save to vault.dat.
    
    Args:
        api_key: Binance API key
        api_secret: Binance API secret
        pin: 4-digit PIN for encryption
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Derive encryption key from PIN
        key, salt = _derive_key(pin)
        
        # Create Fernet cipher
        cipher = Fernet(key)
        
        # Prepare data to encrypt
        credentials = {
            "api_key": api_key,
            "api_secret": api_secret
        }
        
        # Encrypt the credentials
        encrypted_data = cipher.encrypt(json.dumps(credentials).encode())
        
        # Create vault data structure
        vault_data = {
            "salt": base64.b64encode(salt).decode(),
            "data": base64.b64encode(encrypted_data).decode()
        }
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(VAULT_PATH), exist_ok=True)
        
        # Save to vault file
        with open(VAULT_PATH, "w") as f:
            json.dump(vault_data, f)
            
        return True
    except Exception as e:
        print(f"Error encrypting credentials: {e}")
        return False


def decrypt_credentials(pin: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Decrypt Binance API credentials using the provided PIN.
    
    Args:
        pin: 4-digit PIN for decryption
        
    Returns:
        Tuple of (api_key, api_secret) or (None, None) if decryption fails
    """
    try:
        # Check if vault file exists
        if not os.path.exists(VAULT_PATH):
            print("Vault file not found")
            return None, None
            
        # Read vault data
        with open(VAULT_PATH, "r") as f:
            vault_data = json.load(f)
            
        # Extract salt and encrypted data
        salt = base64.b64decode(vault_data["salt"])
        encrypted_data = base64.b64decode(vault_data["data"])
        
        # Derive key from PIN and salt
        key, _ = _derive_key(pin, salt)
        
        # Create Fernet cipher
        cipher = Fernet(key)
        
        # Decrypt the data
        decrypted_data = cipher.decrypt(encrypted_data).decode()
        credentials = json.loads(decrypted_data)
        
        return credentials["api_key"], credentials["api_secret"]
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return None, None


def validate_permissions(api_key: str, api_secret: str) -> bool:
    """
    Validate that the API key has at least READ permissions.
    The API can have more permissions, but the app will only use read operations.
    
    Args:
        api_key: Binance API key
        api_secret: Binance API secret
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Create Binance client
        client = Client(api_key, api_secret)
        
        # Check if the get_api_permission_status method exists
        if hasattr(client, 'get_api_permission_status'):
            try:
                # Get API key permissions
                api_permissions = client.get_api_permission_status()
                
                # Check for withdrawal permissions (warn but don't block)
                withdraw_enabled = api_permissions.get("enableWithdrawals", False)
                trading_enabled = api_permissions.get("enableSpotAndMarginTrading", False)
                futures_enabled = api_permissions.get("enableFutures", False)
                margin_enabled = api_permissions.get("enableMargin", False)
                
                # Warn if the API has more permissions than needed
                if withdraw_enabled or trading_enabled or futures_enabled or margin_enabled:
                    print("WARNING: This API key has trading or withdrawal permissions. " +
                          "For security, consider using a read-only key. " +
                          "This app will NEVER perform any trading or withdrawal operations.")
            except Exception as e:
                print(f"Could not check API permissions: {e}")
                print("Continuing with basic validation...")
        else:
            print("API permission status check not available in this version of python-binance.")
            print("Continuing with basic validation...")
        
        # Test a simple read operation to verify the API works
        client.get_account()
        
        return True
    except Exception as e:
        print(f"Error validating API key: {e}")
        return False


def delete_credentials() -> bool:
    """
    Delete stored API credentials.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(VAULT_PATH):
            os.remove(VAULT_PATH)
            return True
        return False
    except Exception as e:
        print(f"Error deleting credentials: {e}")
        return False


def credentials_exist() -> bool:
    """
    Check if encrypted credentials exist.
    
    Returns:
        True if credentials exist, False otherwise
    """
    return os.path.exists(VAULT_PATH)