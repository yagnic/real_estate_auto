#!/usr/bin/env python3
"""
Authentication module for Microsoft Graph API with Streamlit Cloud support
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from msal import PublicClientApplication
import streamlit as st

# Detect environment
IS_STREAMLIT_CLOUD = os.getenv('STREAMLIT_SHARING_MODE') or os.getenv('STREAMLIT_RUNTIME_ENV')

# Import config
try:
    from config import CLIENT_ID, AUTHORITY, SCOPES
except ImportError:
    # Fallback to environment variables
    CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID')
    TENANT_ID = os.getenv('OUTLOOK_TENANT_ID')
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    SCOPES = ['Mail.Read', 'Mail.Send']


class Authenticator:
    def __init__(self):
        # Use session state for Streamlit Cloud, file for local
        if IS_STREAMLIT_CLOUD:
            self._init_session_state()
        else:
            self.token = None
            self.refresh_token = None
            self.token_expires_at = None
            self.token_file = "auth_token.pkl"
        
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
    
    def _init_session_state(self):
        """Initialize session state for Streamlit Cloud"""
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'refresh_token' not in st.session_state:
            st.session_state.refresh_token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        if 'device_flow' not in st.session_state:
            st.session_state.device_flow = None
    
    def get_token(self) -> str:
        """Get authentication token, refreshing if necessary"""
        # Try to load existing token
        if self._load_saved_token():
            # Check if token is still valid
            if self._is_token_valid():
                return self._get_token_value()
        
        # Token expired or doesn't exist, need to authenticate
        return None
    
    def authenticate(self) -> bool:
        """Authenticate user and get access token"""
        
        # First try silent authentication with cached account
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            
            if result and "access_token" in result:
                self._save_token(result)
                return True
        
        # Use different auth method based on environment
        if IS_STREAMLIT_CLOUD:
            return self._authenticate_device_flow()
        else:
            return self._authenticate_interactive()
    
    def _authenticate_device_flow(self) -> bool:
        """Authenticate using device code flow (for Streamlit Cloud)"""
        
        # Check if we already have a flow in progress
        if st.session_state.device_flow is None:
            # Initiate device flow
            flow = self.app.initiate_device_flow(scopes=SCOPES)
            
            if "user_code" not in flow:
                st.error("Failed to create device flow")
                return False
            
            st.session_state.device_flow = flow
            
            # Display instructions
            st.warning("""
            ### Authentication Required
            
            Please complete these steps:
            
            1. Open a new tab and go to: **https://microsoft.com/devicelogin**
            2. Enter this code: **{}**
            3. Sign in with your Microsoft account
            4. After signing in, return here and click the button below
            """.format(flow['user_code']))
            
            return False  # Not authenticated yet
        
        # Check if user clicked the continue button
        if st.button("I've completed authentication - Continue", type="primary"):
            # Complete device flow
            result = self.app.acquire_token_by_device_flow(st.session_state.device_flow)
            
            if "access_token" in result:
                self._save_token(result)
                st.session_state.device_flow = None  # Clear flow
                st.success("Authentication successful!")
                st.rerun()
                return True
            else:
                error = result.get('error_description', 'Unknown error')
                st.error(f"Authentication failed: {error}")
                st.session_state.device_flow = None  # Clear flow to retry
                return False
        
        return False  # Still waiting for user
    
    def _authenticate_interactive(self) -> bool:
        """Authenticate using interactive flow (for local development)"""
        result = self.app.acquire_token_interactive(SCOPES)
        
        if "access_token" not in result:
            error_msg = result.get('error_description', 'Unknown error')
            print(f"Authentication failed: {error_msg}")
            return False
        
        self._save_token(result)
        print("Authentication successful")
        return True
    
    def _save_token(self, result):
        """Save token (to session state or file depending on environment)"""
        token = result['access_token']
        refresh_token = result.get('refresh_token')
        
        # Calculate expiry time
        expires_in = result.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        if IS_STREAMLIT_CLOUD:
            # Save to session state
            st.session_state.token = token
            st.session_state.refresh_token = refresh_token
            st.session_state.token_expires_at = expires_at
        else:
            # Save to instance and file
            self.token = token
            self.refresh_token = refresh_token
            self.token_expires_at = expires_at
            
            # Save to file
            token_data = {
                'access_token': token,
                'refresh_token': refresh_token,
                'expires_at': expires_at.isoformat(),
                'saved_at': datetime.now().isoformat()
            }
            
            try:
                with open(self.token_file, 'wb') as f:
                    pickle.dump(token_data, f)
                print(f"Token saved to {self.token_file}")
            except Exception as e:
                print(f"Failed to save token: {e}")
    
    def _load_saved_token(self) -> bool:
        """Load token from storage"""
        if IS_STREAMLIT_CLOUD:
            # Load from session state
            if st.session_state.token:
                return True
            return False
        else:
            # Load from file
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
    
    def _get_token_value(self) -> str:
        """Get token value from storage"""
        if IS_STREAMLIT_CLOUD:
            return st.session_state.token
        else:
            return self.token
    
    def _get_expires_at(self):
        """Get token expiry time"""
        if IS_STREAMLIT_CLOUD:
            return st.session_state.token_expires_at
        else:
            return self.token_expires_at
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        token = self._get_token_value()
        expires_at = self._get_expires_at()
        
        if not token or not expires_at:
            return False
        
        if datetime.now() >= expires_at:
            print("Token expired, need to refresh")
            return False
        
        print(f"Token valid until: {expires_at}")
        return True
    
    def clear_saved_token(self):
        """Clear saved token"""
        if IS_STREAMLIT_CLOUD:
            st.session_state.token = None
            st.session_state.refresh_token = None
            st.session_state.token_expires_at = None
            st.session_state.device_flow = None
        else:
            try:
                if os.path.exists(self.token_file):
                    os.remove(self.token_file)
                    print("Saved token cleared")
            except Exception as e:
                print(f"Error clearing token: {e}")
    
    def get_token_info(self) -> dict:
        """Get information about current token"""
        token = self._get_token_value()
        expires_at = self._get_expires_at()
        
        return {
            'has_token': bool(token),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'is_valid': self._is_token_valid(),
            'time_until_expiry': str(expires_at - datetime.now()) if expires_at else None
        }