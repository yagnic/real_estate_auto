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
import sys

# Better environment detection for Streamlit Cloud
IS_STREAMLIT_CLOUD = (
    os.getenv('STREAMLIT_SHARING_MODE') == '1' or 
    os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or
    'streamlit.io' in os.getenv('HOSTNAME', '') or
    not sys.stdin.isatty()  # No terminal = cloud environment
)

# Import config
try:
    from config import CLIENT_ID, AUTHORITY, SCOPES
except ImportError:
    CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID')
    TENANT_ID = os.getenv('OUTLOOK_TENANT_ID')
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    SCOPES = ['Mail.Read', 'Mail.Send']


class Authenticator:
    def __init__(self):
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'refresh_token' not in st.session_state:
            st.session_state.refresh_token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        if 'device_flow' not in st.session_state:
            st.session_state.device_flow = None
        
        self.token_file = "auth_token.pkl"
        
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
    
    def get_token(self) -> str:
        """Get authentication token"""
        # Check session state first (always)
        if st.session_state.token and self._is_token_valid():
            return st.session_state.token
        
        # Try loading from file (local only)
        if not IS_STREAMLIT_CLOUD and self._load_from_file():
            if self._is_token_valid():
                return st.session_state.token
        
        return None
    
    def authenticate(self) -> bool:
        """Authenticate user - ALWAYS use device flow in Streamlit"""
        
        # First try silent auth with cached account
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_token(result)
                return True
        
        # ALWAYS use device flow (works everywhere)
        return self._authenticate_device_flow()
    
    def _authenticate_device_flow(self) -> bool:
        """Device code flow authentication"""
        
        # Initiate flow if not already started
        if st.session_state.device_flow is None:
            flow = self.app.initiate_device_flow(scopes=SCOPES)
            
            if "user_code" not in flow:
                st.error("Failed to create device flow")
                return False
            
            st.session_state.device_flow = flow
            
            # Show instructions with better formatting
            st.info(f"""
            ### 🔐 Authentication Required
            
            **Step 1:** Open this link in a new tab:  
            👉 **https://microsoft.com/devicelogin**
            
            **Step 2:** Enter this code:  
            ### `{flow['user_code']}`
            
            **Step 3:** Sign in with your Microsoft account
            
            **Step 4:** Return here and click Continue below
            """)
            
            return False
        
        # Check if user completed authentication
        if st.button("✅ I've completed authentication - Continue", type="primary", key="auth_continue"):
            result = self.app.acquire_token_by_device_flow(st.session_state.device_flow)
            
            if "access_token" in result:
                self._save_token(result)
                st.session_state.device_flow = None
                st.success("✅ Authentication successful!")
                st.rerun()
                return True
            else:
                error = result.get('error_description', 'Unknown error')
                st.error(f"❌ Authentication failed: {error}")
                st.session_state.device_flow = None
                return False
        
        return False
    
    def _save_token(self, result):
        """Save token to session state and file"""
        token = result['access_token']
        refresh_token = result.get('refresh_token')
        expires_in = result.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        # Always save to session state
        st.session_state.token = token
        st.session_state.refresh_token = refresh_token
        st.session_state.token_expires_at = expires_at
        
        # Also save to file (local only, for persistence across sessions)
        if not IS_STREAMLIT_CLOUD:
            token_data = {
                'access_token': token,
                'refresh_token': refresh_token,
                'expires_at': expires_at.isoformat(),
            }
            try:
                with open(self.token_file, 'wb') as f:
                    pickle.dump(token_data, f)
            except:
                pass
    
    def _load_from_file(self) -> bool:
        """Load token from file (local only)"""
        if not os.path.exists(self.token_file):
            return False
        
        try:
            with open(self.token_file, 'rb') as f:
                token_data = pickle.load(f)
            
            st.session_state.token = token_data.get('access_token')
            st.session_state.refresh_token = token_data.get('refresh_token')
            
            expires_at_str = token_data.get('expires_at')
            if expires_at_str:
                st.session_state.token_expires_at = datetime.fromisoformat(expires_at_str)
            
            return True
        except:
            return False
    
    def _is_token_valid(self) -> bool:
        """Check if token is valid"""
        if not st.session_state.token or not st.session_state.token_expires_at:
            return False
        
        return datetime.now() < st.session_state.token_expires_at
    
    def clear_saved_token(self):
        """Clear all saved tokens"""
        st.session_state.token = None
        st.session_state.refresh_token = None
        st.session_state.token_expires_at = None
        st.session_state.device_flow = None
        
        if not IS_STREAMLIT_CLOUD and os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
            except:
                pass
    
    def get_token_info(self) -> dict:
        """Get token information"""
        expires_at = st.session_state.token_expires_at
        
        return {
            'has_token': bool(st.session_state.token),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'is_valid': self._is_token_valid(),
            'time_until_expiry': str(expires_at - datetime.now()) if expires_at else None
        }