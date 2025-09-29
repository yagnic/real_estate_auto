#!/usr/bin/env python3
"""
Authentication using client credentials flow (daemon app)
"""

import os
from datetime import datetime, timedelta
from msal import ConfidentialClientApplication
import streamlit as st

CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID')
CLIENT_SECRET = os.getenv('OUTLOOK_CLIENT_SECRET')
TENANT_ID = os.getenv('OUTLOOK_TENANT_ID')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ['https://graph.microsoft.com/.default']  # Note: different scope format

class Authenticator:
    def __init__(self):
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        
        self.app = ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=AUTHORITY
        )
    
    def get_token(self) -> str:
        """Get token - auto-refreshes"""
        if st.session_state.token and self._is_token_valid():
            return st.session_state.token
        
        # Auto-authenticate
        if self.authenticate():
            return st.session_state.token
        
        return None
    
    def authenticate(self) -> bool:
        """Authenticate using client credentials (no user interaction)"""
        try:
            result = self.app.acquire_token_for_client(scopes=SCOPES)
            
            if "access_token" in result:
                self._save_token(result)
                return True
            else:
                error = result.get('error_description', result.get('error', 'Unknown error'))
                st.error(f"Authentication failed: {error}")
                return False
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return False
    
    def _save_token(self, result):
        token = result['access_token']
        expires_in = result.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        st.session_state.token = token
        st.session_state.token_expires_at = expires_at
    
    def _is_token_valid(self) -> bool:
        if not st.session_state.token or not st.session_state.token_expires_at:
            return False
        return datetime.now() < st.session_state.token_expires_at
    
    def clear_saved_token(self):
        st.session_state.token = None
        st.session_state.token_expires_at = None
    
    def get_token_info(self) -> dict:
        expires_at = st.session_state.token_expires_at
        return {
            'has_token': bool(st.session_state.token),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'is_valid': self._is_token_valid()
        }