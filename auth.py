#!/usr/bin/env python3
"""
Authentication for Microsoft Graph API with device flow
"""

import os
from datetime import datetime, timedelta
from msal import PublicClientApplication
import streamlit as st

CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID')
# Use 'common' for device flow - supports both personal and work accounts
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ['Mail.Read', 'Mail.Send']

class Authenticator:
    def __init__(self):
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        if 'device_flow' not in st.session_state:
            st.session_state.device_flow = None
        
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
    
    def get_token(self) -> str:
        """Get valid token"""
        if st.session_state.token and self._is_token_valid():
            return st.session_state.token
        
        # Try silent refresh
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_token(result)
                return st.session_state.token
        
        return None
    
    def authenticate(self) -> bool:
    """Authenticate using device flow"""
    
    # Try silent auth first
    accounts = self.app.get_accounts()
    if accounts:
        result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            self._save_token(result)
            return True
    
    # Start device flow
    if st.session_state.device_flow is None:
        try:
            flow = self.app.initiate_device_flow(scopes=SCOPES)
            
            if "user_code" not in flow:
                # Show the actual error from MSAL
                error = flow.get('error_description', flow.get('error', 'Unknown error'))
                st.error(f"Device flow failed: {error}")
                st.info(f"Full response: {flow}")
                return False
            
            st.session_state.device_flow = flow
            
            # Show instructions
            st.warning(f"""
            ### Authentication Required
            
            **1.** Open: **https://microsoft.com/devicelogin**
            
            **2.** Enter code: **`{flow['user_code']}`**
            
            **3.** Sign in with your Microsoft account
            
            **4.** Return here and click Continue
            """)
            
            return False
            
        except Exception as e:
            st.error(f"Error initiating device flow: {str(e)}")
            st.info("Check your Azure AD app configuration")
            return False
        
        with col2:
            if st.button("❌ Cancel", key="auth_cancel"):
                st.session_state.device_flow = None
                st.rerun()
        
        return False
    
    def _save_token(self, result):
        """Save token to session"""
        token = result['access_token']
        expires_in = result.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        st.session_state.token = token
        st.session_state.token_expires_at = expires_at
    
    def _is_token_valid(self) -> bool:
        """Check token validity"""
        if not st.session_state.token or not st.session_state.token_expires_at:
            return False
        return datetime.now() < st.session_state.token_expires_at
    
    def clear_saved_token(self):
        """Clear tokens"""
        st.session_state.token = None
        st.session_state.token_expires_at = None
        st.session_state.device_flow = None
    
    def get_token_info(self) -> dict:
        """Get token info"""
        expires_at = st.session_state.token_expires_at
        return {
            'has_token': bool(st.session_state.token),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'is_valid': self._is_token_valid()
        }