#!/usr/bin/env python3
"""
Authentication with persistent token storage in Supabase
"""

import os
import json
from datetime import datetime, timedelta
from msal import PublicClientApplication
import streamlit as st
from supabase import create_client

CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID')
TENANT_ID = os.getenv('OUTLOOK_TENANT_ID')
AUTHORITY = f"https://login.microsoftonline.com/common"
SCOPES = ['Mail.Read', 'Mail.Send']

class Authenticator:
    def __init__(self):
        # Initialize session state
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        if 'device_flow' not in st.session_state:
            st.session_state.device_flow = None
        if 'user_email' not in st.session_state:
            st.session_state.user_email = None
        
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
        
        # Initialize Supabase for token storage
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            self.supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
        except:
            self.supabase = None
    
    def get_token(self) -> str:
        """Get valid token"""
        # Check if current token is valid
        if st.session_state.token and self._is_token_valid():
            return st.session_state.token
        
        # Try to refresh from stored refresh token
        if self._refresh_from_storage():
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
            flow = self.app.initiate_device_flow(scopes=SCOPES)
            
            if "user_code" not in flow:
                st.error("Failed to create device flow")
                return False
            
            st.session_state.device_flow = flow
            
            # Display instructions in main area
            st.info(f"""
            ### Authentication Required
            
            **Step 1:** Visit: https://microsoft.com/devicelogin
            
            **Step 2:** Enter code: `{flow['user_code']}`
            
            **Step 3:** Sign in with your account
            
            **Step 4:** Click Continue below after signing in
            """)
            
            return False
        
        # Show continue button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Continue", type="primary", key="device_flow_continue"):
                result = self.app.acquire_token_by_device_flow(st.session_state.device_flow)
                
                if "access_token" in result:
                    self._save_token(result)
                    st.session_state.device_flow = None
                    st.success("Authentication successful!")
                    st.rerun()
                    return True
                else:
                    error = result.get('error_description', 'Authentication timed out or failed')
                    st.error(f"Failed: {error}")
                    st.info("Click 'Clear Saved Token' in sidebar and try again")
                    st.session_state.device_flow = None
                    return False
        
        with col2:
            if st.button("Cancel", key="device_flow_cancel"):
                st.session_state.device_flow = None
                st.rerun()
        
        return False
    
    def _save_token(self, result):
        """Save token to session and Supabase"""
        token = result['access_token']
        refresh_token = result.get('refresh_token')
        expires_in = result.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        # Get user info
        user_info = result.get('id_token_claims', {})
        user_email = user_info.get('preferred_username') or user_info.get('email') or 'unknown'
        
        # Save to session
        st.session_state.token = token
        st.session_state.token_expires_at = expires_at
        st.session_state.user_email = user_email
        
        # Save refresh token to Supabase for persistence
        if self.supabase and refresh_token:
            try:
                self.supabase.table('auth_tokens').upsert({
                    'user_email': user_email,
                    'refresh_token': refresh_token,
                    'expires_at': expires_at.isoformat(),
                    'updated_at': datetime.now().isoformat()
                }).execute()
            except:
                pass  # Fail silently
    
    def _refresh_from_storage(self) -> bool:
        """Try to refresh token from stored refresh token"""
        if not self.supabase:
            return False
        
        try:
            # Get stored refresh token (you'll need to identify user somehow)
            # For now, get the most recent one
            response = self.supabase.table('auth_tokens').select('*').order('updated_at', desc=True).limit(1).execute()
            
            if not response.data:
                return False
            
            refresh_token = response.data[0].get('refresh_token')
            if not refresh_token:
                return False
            
            # Try to refresh
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
                if result and "access_token" in result:
                    self._save_token(result)
                    return True
            
            return False
        except:
            return False
    
    def _is_token_valid(self) -> bool:
        """Check token validity"""
        if not st.session_state.token or not st.session_state.token_expires_at:
            return False
        return datetime.now() < st.session_state.token_expires_at
    
    def clear_saved_token(self):
        """Clear all tokens"""
        st.session_state.token = None
        st.session_state.token_expires_at = None
        st.session_state.device_flow = None
        st.session_state.user_email = None
        st.session_state.start_auth = False
    
    def get_token_info(self) -> dict:
        """Get token info"""
        expires_at = st.session_state.token_expires_at
        return {
            'has_token': bool(st.session_state.token),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'is_valid': self._is_token_valid()
        }