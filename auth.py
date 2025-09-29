#!/usr/bin/env python3
"""
Authentication module with Supabase token persistence
"""

import os
from datetime import datetime, timedelta
from msal import PublicClientApplication
from config import CLIENT_ID, AUTHORITY, SCOPES
from supabase import create_client

class Authenticator:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.user_id = "default_user"  # Can be customized per user
        
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
        
        # Initialize Supabase
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            self.supabase = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"Warning: Could not initialize Supabase: {e}")
            self.supabase = None
    
    def get_token(self) -> str:
        """Get authentication token, refreshing if necessary"""
        if self._load_saved_token():
            if self._is_token_valid():
                return self.token
        
        if self.authenticate():
            return self.token
        
        return None
    
    def authenticate(self) -> bool:
        """Authenticate user and get access token"""
        print("Authenticating...")
        
        accounts = self.app.get_accounts()
        if accounts:
            print("Found cached account, attempting silent authentication...")
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            
            if result and "access_token" in result:
                self._save_token(result)
                return True
        
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
        """Save token to Supabase"""
        self.token = result['access_token']
        self.refresh_token = result.get('refresh_token')
        
        expires_in = result.get('expires_in', 3600)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        if not self.supabase:
            print("Supabase not available, token not persisted")
            return
        
        token_data = {
            'user_id': self.user_id,
            'access_token': self.token,
            'refresh_token': self.refresh_token,
            'expires_at': self.token_expires_at.isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            # Upsert (insert or update)
            self.supabase.table('auth_tokens').upsert(
                token_data,
                on_conflict='user_id'
            ).execute()
            print(f"Token saved to Supabase for user: {self.user_id}")
        except Exception as e:
            print(f"Failed to save token to Supabase: {e}")
    
    def _load_saved_token(self) -> bool:
        """Load token from Supabase"""
        if not self.supabase:
            return False
        
        try:
            response = self.supabase.table('auth_tokens').select('*').eq('user_id', self.user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return False
            
            token_data = response.data[0]
            
            self.token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            expires_at_str = token_data.get('expires_at')
            if expires_at_str:
                self.token_expires_at = datetime.fromisoformat(expires_at_str)
            
            print("Loaded saved authentication token from Supabase")
            return True
            
        except Exception as e:
            print(f"Failed to load saved token from Supabase: {e}")
            return False
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.token or not self.token_expires_at:
            return False
        
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
        """Clear saved token from Supabase"""
        if not self.supabase:
            return
        
        try:
            self.supabase.table('auth_tokens').delete().eq('user_id', self.user_id).execute()
            print("Saved token cleared from Supabase")
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