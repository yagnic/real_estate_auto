#!/usr/bin/env python3
"""
Authentication module for Microsoft Graph API with token persistence
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from msal import PublicClientApplication
from config import CLIENT_ID, AUTHORITY, SCOPES


class Authenticator:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.token_file = "auth_token.pkl"
        
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
    
    def get_token(self) -> str:
        """Get authentication token, refreshing if necessary"""
        # Try to load existing token
        if self._load_saved_token():
            # Check if token is still valid
            if self._is_token_valid():
                return self.token
        
        # Token expired or doesn't exist, authenticate
        if self.authenticate():
            return self.token
        
        return None
    
    def authenticate(self) -> bool:
        """Authenticate user and get access token"""
        print("Authenticating...")
        
        # First try silent authentication with cached account
        accounts = self.app.get_accounts()
        if accounts:
            print("Found cached account, attempting silent authentication...")
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            
            if result and "access_token" in result:
                self._save_token(result)
                return True
        
        # If silent auth fails, try interactive
        print("Silent authentication failed, opening browser...")
        result = self.app.acquire_token_interactive(SCOPES)
        
        if "access_token" not in result:
            error_msg = result.get('error_description', 'Unknown error')
            print(f"Authentication failed: {error_msg}")
            return False
        
        self._save_token(result)
        print("Authentication successful")
        return True
    
    def _save_token(self, result):
        """Save token and refresh token to file"""
        self.token = result['access_token']
        self.refresh_token = result.get('refresh_token')
        
        # Calculate expiry time
        expires_in = result.get('expires_in', 3600)  # Default 1 hour
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
        
        # Save to file
        token_data = {
            'access_token': self.token,
            'refresh_token': self.refresh_token,
            'expires_at': self.token_expires_at.isoformat(),
            'saved_at': datetime.now().isoformat()
        }
        
        try:
            with open(self.token_file, 'wb') as f:
                pickle.dump(token_data, f)
            print(f"Token saved to {self.token_file}")
        except Exception as e:
            print(f"Failed to save token: {e}")
    
    def _load_saved_token(self) -> bool:
        """Load token from saved file"""
        if not os.path.exists(self.token_file):
            return False
        
        try:
            with open(self.token_file, 'rb') as f:
                token_data = pickle.load(f)
            
            self.token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            expires_at_str = token_data.get('expires_at')
            if expires_at_str:
                self.token_expires_at = datetime.fromisoformat(expires_at_str)
            
            print("Loaded saved authentication token")
            return True
            
        except Exception as e:
            print(f"Failed to load saved token: {e}")
            return False
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.token or not self.token_expires_at:
            return False
        
        # Check if token expires within next 5 minutes
        if datetime.now() >= self.token_expires_at:
            print("Token expired, need to refresh")
            return False
        
        print(f"Token valid until: {self.token_expires_at}")
        return True
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            print("No refresh token available")
            return False
        
        try:
            # Use refresh token to get new access token
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
                
                if result and "access_token" in result:
                    self._save_token(result)
                    print("Token refreshed successfully")
                    return True
            
            print("Token refresh failed")
            return False
            
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return False
    
    def clear_saved_token(self):
        """Clear saved token file"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                print("Saved token cleared")
        except Exception as e:
            print(f"Error clearing token: {e}")
    
    def get_token_info(self) -> dict:
        """Get information about current token"""
        return {
            'has_token': bool(self.token),
            'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'is_valid': self._is_token_valid(),
            'time_until_expiry': str(self.token_expires_at - datetime.now()) if self.token_expires_at else None
        }