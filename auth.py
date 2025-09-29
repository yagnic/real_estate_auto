import os
from datetime import datetime, timedelta
from msal import PublicClientApplication
import streamlit as st

CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID')
TENANT_ID = os.getenv('OUTLOOK_TENANT_ID')  # Use your actual tenant
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ['Mail.Read', 'Mail.Send']

class Authenticator:
    def __init__(self):
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None
        if 'device_flow' not in st.session_state:
            st.session_state.device_flow = None
        
        # Use PublicClientApplication (not ConfidentialClientApplication)
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY
        )
    
    def get_token(self) -> str:
        if st.session_state.token and self._is_token_valid():
            return st.session_state.token
        
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_token(result)
                return st.session_state.token
        
        return None
    
    def authenticate(self) -> bool:
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_token(result)
                return True
        
        if st.session_state.device_flow is None:
            try:
                flow = self.app.initiate_device_flow(scopes=SCOPES)
                
                if "user_code" not in flow:
                    error = flow.get('error_description', flow.get('error', 'Unknown error'))
                    st.error(f"Device flow failed: {error}")
                    return False
                
                st.session_state.device_flow = flow
                
                st.warning(f"""
                ### Authentication Required
                
                **1.** Visit: https://microsoft.com/devicelogin
                
                **2.** Enter code: `{flow['user_code']}`
                
                **3.** Sign in with your account
                
                **4.** Click Continue below
                """)
                
                return False
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                return False
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Continue", type="primary", key="auth_continue"):
                result = self.app.acquire_token_by_device_flow(st.session_state.device_flow)
                
                if "access_token" in result:
                    self._save_token(result)
                    st.session_state.device_flow = None
                    st.success("Authentication successful!")
                    st.rerun()
                    return True
                else:
                    error = result.get('error_description', 'Authentication failed')
                    st.error(f"Failed: {error}")
                    st.session_state.device_flow = None
                    return False
        
        with col2:
            if st.button("Cancel", key="auth_cancel"):
                st.session_state.device_flow = None
                st.rerun()
        
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
        st.session_state.device_flow = None
    
    def get_token_info(self) -> dict:
        expires_at = st.session_state.token_expires_at
        return {
            'has_token': bool(st.session_state.token),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'is_valid': self._is_token_valid()
        }