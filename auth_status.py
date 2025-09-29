#!/usr/bin/env python3
"""
Authentication status management for Streamlit
"""

import streamlit as st
from datetime import datetime
from auth import Authenticator

def show_auth_status():
    """Show authentication status in Streamlit sidebar"""
    
    st.sidebar.subheader("Authentication Status")
    
    try:
        auth = Authenticator()
        token_info = auth.get_token_info()
        
        if token_info['has_token'] and token_info['is_valid']:
            st.sidebar.success("Authenticated")
            if token_info['expires_at']:
                expires_at = datetime.fromisoformat(token_info['expires_at'])
                st.sidebar.write(f"Expires: {expires_at.strftime('%H:%M:%S')}")
        else:
            st.sidebar.warning("Authentication Required")
            
            # Show authenticate button
            if st.sidebar.button("Authenticate Now", key="auth_button_sidebar"):
                # This will trigger the device flow
                st.session_state.start_auth = True
            
            # If auth started, show device flow in main area (not sidebar)
            if st.session_state.get('start_auth') or st.session_state.get('device_flow'):
                auth.authenticate()
        
        # Add clear token option
        if token_info['has_token']:
            if st.sidebar.button("Clear Saved Token", key="clear_token_button"):
                auth.clear_saved_token()
                st.sidebar.success("Token cleared")
                st.rerun()
        
    except Exception as e:
        st.sidebar.error(f"Auth error: {e}")
def require_authentication():
    """Decorator-like function to require authentication for operations"""
    
    auth = Authenticator()
    token = auth.get_token()
    
    if not token:
        st.error("Authentication required. Please authenticate in the sidebar.")
        return False
    
    return True

def get_authenticated_processor():
    """Get an authenticated email processor"""
    
    if not require_authentication():
        return None
    
    from email_processor import EmailProcessor
    return EmailProcessor()