#!/usr/bin/env python3
"""
Simple Real Estate Deal Processor with Supabase
Flow: Background Processing → Supabase → Pending/Approved → Excel on Demand → Approve & Send
Uses Microsoft Graph API for sending emails
"""

import streamlit as st
import pandas as pd
import os
import json
import subprocess
import sys
from datetime import datetime
from io import BytesIO
import tempfile
import requests
import base64

from supabase_client import SupabaseDealsClient
from template import *
from dynamic_excel_generator import DealAppraisalExcelGenerator
from auth_status import show_auth_status, require_authentication
from auth import Authenticator


try:
    for key, value in st.secrets.items():
        if key not in os.environ:  # Don't override existing env vars
            os.environ[key] = str(value)
except (AttributeError, FileNotFoundError):
    # No secrets file found (running locally with .env)
    pass

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
# Page config
st.set_page_config(
    page_title="Real Estate Deal Processor",
    page_icon="🏢",
    layout="wide"
)


class RealEstateApp:
    """Simplified Real Estate Application"""
    
    def __init__(self):
        self.supabase = SupabaseDealsClient()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state"""
        if 'selected_deal_id' not in st.session_state:
            st.session_state.selected_deal_id = None
        if 'generated_excel' not in st.session_state:
            st.session_state.generated_excel = {}
    
    def _get_graph_token(self):
        """Get Microsoft Graph API token from auth module"""
        try:
            from auth import Authenticator
            auth = Authenticator()
            token = auth.get_token()
            return token
        except Exception as e:
            st.error(f"Error getting token: {e}")
            return None
    
    def run(self):
        """Main application"""
        # Show auth status
        show_auth_status()
        
        if not require_authentication():
            st.title("🏢 Real Estate Deal Processor")
            auth = Authenticator()
            auth.authenticate()  # Show auth UI
            return
            
        # Sidebar navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Go to",
            ["Dashboard", "Pending Deals", "Approved Deals", "Automation", "Settings"]
        )
        
        # Render selected page
        if page == "Dashboard":
            self.render_dashboard()
        elif page == "Pending Deals":
            self.render_pending_deals()
        elif page == "Approved Deals":
            self.render_approved_deals()
        elif page == "Automation":
            self.render_automation()
        elif page == "Settings":
            self.render_settings()
    
    def render_dashboard(self):
        """Dashboard with stats and overview"""
        st.title("🏢 Dashboard")
        
        # Get stats
        stats = self.supabase.get_stats()
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Deals", stats['total'])
        
        with col2:
            st.metric("Pending Review", stats['pending'], delta=None, delta_color="off")
        
        with col3:
            st.metric("Approved", stats['approved'])
        
        with col4:
            approval_rate = (stats['approved'] / stats['total'] * 100) if stats['total'] > 0 else 0
            st.metric("Approval Rate", f"{approval_rate:.1f}%")
        
        # Automation status
        st.subheader("Background Automation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if self._check_automation_active():
                st.success("✓ Automation is running")
                st.info("Processing emails every minute")
            else:
                st.warning("⚠ Automation is not active")
                if st.button("Start Automation"):
                    if self._start_automation():
                        st.success("Automation started!")
                        st.rerun()
        
        with col2:
            last_run = self._get_last_run_time()
            st.info(f"Last run: {last_run}")
            
            if st.button("Run Now"):
                with st.spinner("Processing emails..."):
                    if self._run_once():
                        st.success("Processing completed!")
                        st.rerun()
        
        # Recent deals
        st.subheader("Recent Deals")
        
        pending_deals = self.supabase.get_pending_deals()[:5]
        approved_deals = self.supabase.get_approved_deals()[:5]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Recent Pending**")
            if pending_deals:
                for deal in pending_deals:
                    with st.container():
                        st.write(f"📧 {deal['subject'][:40]}...")
                        st.caption(f"Confidence: {deal['confidence']}% | {deal['deal_type']}")
            else:
                st.info("No pending deals")
        
        with col2:
            st.write("**Recent Approved**")
            if approved_deals:
                for deal in approved_deals:
                    with st.container():
                        st.write(f"✅ {deal['subject'][:40]}...")
                        st.caption(f"{deal['deal_type']}")
            else:
                st.info("No approved deals")
    
    def render_pending_deals(self):
        """Show all pending deals"""
        st.title("📋 Pending Deals")
        
        pending_deals = self.supabase.get_pending_deals()
        
        if not pending_deals:
            st.info("No pending deals. All caught up!")
            return
        
        st.write(f"**{len(pending_deals)} deals pending review**")
        
        # Show deals as cards
        for deal in pending_deals:
            with st.expander(f"📧 {deal['subject']}", expanded=False):
                self._render_deal_card(deal, is_pending=True)
    
    def render_approved_deals(self):
        """Show all approved deals"""
        st.title("✅ Approved Deals")
        
        approved_deals = self.supabase.get_approved_deals()
        
        if not approved_deals:
            st.info("No approved deals yet")
            return
        
        st.write(f"**{len(approved_deals)} approved deals**")
        
        # Show deals as cards
        for deal in approved_deals:
            with st.expander(f"✅ {deal['subject']}", expanded=False):
                self._render_deal_card(deal, is_pending=False)
    
    def _render_deal_card(self, deal, is_pending=True):
        """Render a deal card with actions"""
        deal_id = deal['id']
        
        # Parse JSON data
        email_data = json.loads(deal['email_data']) if isinstance(deal['email_data'], str) else deal['email_data']
        analysis_data = json.loads(deal['analysis_data']) if deal['analysis_data'] and isinstance(deal['analysis_data'], str) else deal.get('analysis_data', {})
        
        # Deal info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("**Deal Information**")
            st.write(f"**Type:** {deal['deal_type']}")
            st.write(f"**Confidence:** {deal['confidence']}%")
            st.write(f"**From:** {deal['sender_name']} ({deal['sender']})")
            st.write(f"**Received:** {deal['received_date'][:10]}")
            st.write(f"**Processed:** {deal['processed_date'][:10]}")
        
        with col2:
            st.write("**Financial Summary**")
            if analysis_data and 'net_profit_analysis' in analysis_data:
                net_profit = analysis_data['net_profit_analysis'].get('net_profit') or 0
                profit_margin = analysis_data['net_profit_analysis'].get('net_profit_on_gdv') or 0
                
                try:
                    st.metric("Net Profit", f"£{float(net_profit):,.0f}")
                    st.metric("Profit Margin", f"{float(profit_margin)*100:.1f}%")
                except (TypeError, ValueError):
                    st.metric("Net Profit", "Not calculated")
                    st.metric("Profit Margin", "Not calculated")
                
                if 'kpis' in analysis_data:
                    roi = analysis_data['kpis'].get('return_on_own_funds_per_annum') or 0
                    try:
                        st.metric("ROI (p.a.)", f"{float(roi)*100:.1f}%")
                    except (TypeError, ValueError):
                        st.metric("ROI (p.a.)", "Not calculated")
        
        # Actions
        st.write("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Generate Excel", key=f"excel_{deal_id}"):
                with st.spinner("Generating Excel..."):
                    excel_path = self._generate_excel(email_data, analysis_data, deal_id)
                    if excel_path:
                        st.session_state.generated_excel[deal_id] = excel_path
                        st.success("Excel generated!")
                        st.rerun()
        
        with col2:
            # Download Excel if generated
            if deal_id in st.session_state.generated_excel:
                excel_path = st.session_state.generated_excel[deal_id]
                if os.path.exists(excel_path):
                    with open(excel_path, 'rb') as f:
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=f.read(),
                            file_name=f"deal_{deal['subject'][:20]}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_{deal_id}"
                        )
        
        with col3:
            if is_pending:
                if st.button("✅ Approve", key=f"approve_{deal_id}", type="primary"):
                    if self.supabase.update_deal_status(deal_id, "approved", approved_by="Current User"):
                        st.success("Deal approved!")
                        st.rerun()
            else:
                if st.button("↩️ Move to Pending", key=f"pending_{deal_id}"):
                    if self.supabase.update_deal_status(deal_id, "pending"):
                        st.success("Moved to pending!")
                        st.rerun()
        
        with col4:
            if st.button("📧 Send Email", key=f"send_{deal_id}"):
                if self._send_email_directly(deal):
                    st.success("✅ Email sent successfully!")
                else:
                    st.error("❌ Failed to send email")
        
        # Show notes
        with st.expander("📝 Notes"):
            current_notes = deal.get('notes', '')
            notes = st.text_area("Add notes", value=current_notes, key=f"notes_{deal_id}")
            
            if st.button("Save Notes", key=f"save_notes_{deal_id}"):
                if self.supabase.update_deal_notes(deal_id, notes):
                    st.success("Notes saved!")
        
        # Show email content
        with st.expander("📄 View Email Content"):
            content = email_data.get('combined_content', '')
            st.text_area("Email Content", content[:2000] + "..." if len(content) > 2000 else content, 
                        height=300, disabled=True, key=f"content_{deal_id}")
    
    def _generate_excel(self, email_data, analysis_data, deal_id):
        """Generate Excel file on demand"""
        try:
            # Combine data
            combined_data = {
                'original_email_data': email_data,
                **analysis_data
            }
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            subject_clean = "".join(c for c in email_data.get('subject', 'deal') if c.isalnum() or c in (' ', '-', '_'))[:30]
            filename = f"deal_{subject_clean}_{timestamp}.xlsx"
            
            # Create output directory
            os.makedirs('./generated_excels', exist_ok=True)
            output_path = os.path.join('./generated_excels', filename)
            
            # Generate Excel
            generator = DealAppraisalExcelGenerator(combined_data)
            excel_path = generator.generate_excel(output_path)
            
            if excel_path:
                # Update Supabase with Excel path
                self.supabase.update_excel_path(deal_id, excel_path)
                return excel_path
            
            return None
            
        except Exception as e:
            st.error(f"Error generating Excel: {e}")
            return None
    
    def _send_email_directly(self, deal):
        """Send email directly via Microsoft Graph API with Excel attachment"""
        try:
            # Get access token
            access_token = self._get_graph_token()
            if not access_token:
                st.error("⚠️ Microsoft Graph API token not available. Please authenticate.")
                return False
            
            # Check if Excel exists
            deal_id = deal['id']
            if deal_id not in st.session_state.generated_excel:
                st.info("Generating Excel file first...")
                email_data = json.loads(deal['email_data']) if isinstance(deal['email_data'], str) else deal['email_data']
                analysis_data = json.loads(deal['analysis_data']) if deal['analysis_data'] and isinstance(deal['analysis_data'], str) else deal.get('analysis_data', {})
                
                excel_path = self._generate_excel(email_data, analysis_data, deal_id)
                if not excel_path:
                    st.error("Failed to generate Excel file")
                    return False
                st.session_state.generated_excel[deal_id] = excel_path
            
            excel_path = st.session_state.generated_excel[deal_id]
            if not os.path.exists(excel_path):
                st.error("Excel file not found. Please regenerate.")
                return False
            
            # Get analysis data for email body
            analysis_data = json.loads(deal['analysis_data']) if deal['analysis_data'] and isinstance(deal['analysis_data'], str) else deal.get('analysis_data', {})
            
            net_profit = "Not calculated"
            profit_margin = "Not calculated"
            roi = "Not calculated"
            
            if analysis_data and 'net_profit_analysis' in analysis_data:
                try:
                    np_val = analysis_data['net_profit_analysis'].get('net_profit') or 0
                    net_profit = f"£{float(np_val):,.0f}"
                    
                    pm_val = analysis_data['net_profit_analysis'].get('net_profit_on_gdv') or 0
                    profit_margin = f"{float(pm_val)*100:.1f}%"
                except:
                    pass
                
                if 'kpis' in analysis_data:
                    try:
                        roi_val = analysis_data['kpis'].get('return_on_own_funds_per_annum') or 0
                        roi = f"{float(roi_val)*100:.1f}%"
                    except:
                        pass
            
            # Email body
            body_content = f"""Dear {deal['sender_name']},

Please find attached the comprehensive analysis for your property deal.

Deal Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Property: {deal['subject']}
Deal Type: {deal['deal_type']}
Confidence Score: {deal['confidence']}%

Financial Highlights:
• Net Profit: {net_profit}
• Profit Margin: {profit_margin}
• ROI (per annum): {roi}

The attached Excel file contains:
✓ Detailed financial analysis
✓ GDV and cost breakdown
✓ Funding requirements
✓ Key performance indicators
✓ Comprehensive deal metrics

Please review the attached analysis and let us know if you have any questions.

Best regards,
Real Estate Analysis Team

---
This is an automated analysis generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}
"""
            
            # Read Excel file and encode to base64
            with open(excel_path, 'rb') as f:
                excel_content = f.read()
                excel_base64 = base64.b64encode(excel_content).decode('utf-8')
            
            filename = os.path.basename(excel_path)
            
            # Prepare email message for Graph API
            email_message = {
                "message": {
                    "subject": f"Deal Analysis: {deal['subject']}",
                    "body": {
                        "contentType": "Text",
                        "content": body_content
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": deal['sender']
                            }
                        }
                    ],
                    "attachments": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": filename,
                            "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "contentBytes": excel_base64
                        }
                    ]
                },
                "saveToSentItems": "true"
            }
            
            # Send email via Graph API
            with st.spinner("Sending email..."):
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                
                response = requests.post(
                    'https://graph.microsoft.com/v1.0/me/sendMail',
                    headers=headers,
                    json=email_message
                )
                if response.status_code == 202:
                    return True
                else:
                    st.error(f"Graph API error: {response.status_code} - {response.text}")
                    return False
            
        except Exception as e:
            st.error(f"❌ Error sending email: {str(e)}")
            return False
    
    def render_automation(self):
        """Automation management page"""
        st.title("🤖 Background Automation")
        
        # Status
        st.subheader("Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if self._check_automation_active():
                st.success("✓ Active")
            else:
                st.warning("⚠ Inactive")
        
        with col2:
            stats = self.supabase.get_stats()
            st.metric("Total Processed", stats['total'])
        
        with col3:
            last_run = self._get_last_run_time()
            st.info(f"Last run: {last_run}")
        
        # Controls
        st.subheader("Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("▶️ Start Automation", type="primary"):
                if self._start_automation():
                    st.success("Automation started! Will run every minute.")
                    st.rerun()
                else:
                    st.error("Failed to start automation")
        
        with col2:
            if st.button("⏸️ Stop Automation"):
                if self._stop_automation():
                    st.success("Automation stopped")
                    st.rerun()
                else:
                    st.error("Failed to stop automation")
        
        with col3:
            if st.button("▶️ Run Once Now"):
                with st.status("Processing emails...", expanded=True) as status:
                    if self._run_once_with_output():
                        status.update(label="✓ Processing completed!", state="complete")
                        st.rerun()
                    else:
                        status.update(label="✗ Processing failed", state="error")
        
        # Live logs with auto-refresh
        st.subheader("Live Activity Log")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            auto_refresh = st.checkbox("Auto-refresh (every 5 seconds)", value=False)
        with col2:
            if st.button("🔄 Refresh Now"):
                st.rerun()
        
        # Show logs with better formatting
        log_file = './logs/background_processor.log'
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    all_logs = f.read()
                    
                    if not all_logs.strip():
                        st.warning("Log file is empty. Run the processor to see logs.")
                    else:
                        # Get last N lines
                        log_lines = all_logs.split('\n')
                        
                        # Show options
                        num_lines = st.slider("Number of lines to show", 10, 200, 50)
                        recent_logs = log_lines[-num_lines:]
                        
                        # Color code logs
                        formatted_logs = []
                        for line in recent_logs:
                            if '✓' in line or 'SUCCESS' in line:
                                formatted_logs.append(f"🟢 {line}")
                            elif '✗' in line or 'ERROR' in line or 'FAILED' in line:
                                formatted_logs.append(f"🔴 {line}")
                            elif '⚠' in line or 'WARNING' in line or 'SKIPPED' in line:
                                formatted_logs.append(f"🟡 {line}")
                            elif '>>>' in line:
                                formatted_logs.append(f"\n{line}\n")
                            elif '===' in line:
                                formatted_logs.append(f"\n{line}")
                            else:
                                formatted_logs.append(line)
                        
                        st.code('\n'.join(formatted_logs), language='log')
                        
                        # Show log stats
                        st.caption(f"Total lines in log: {len(log_lines)} | Showing last {num_lines}")
                        
            except Exception as e:
                st.error(f"Error reading logs: {e}")
        else:
            st.warning("No log file found. The processor hasn't run yet.")
            st.info("Click 'Run Once Now' to generate logs.")
        
        # Auto-refresh
        if auto_refresh:
            import time
            time.sleep(5)
            st.rerun()
        
        # Setup instructions
        with st.expander("📚 Setup Instructions"):
            st.markdown("""
            ### Automation Setup (Linux)
            
            The background processor runs every minute and:
            1. ✉️ Fetches new unread emails
            2. 🔍 Checks for duplicates (skips if already in Supabase)
            3. 📊 Runs comprehensive financial analysis (15 steps)
            4. 💾 Saves to Supabase with auto status assignment
            
            **Prerequisites:**
            - SUPABASE_URL and SUPABASE_KEY environment variables must be set
            - Authentication must be configured
            - `background_processor.py` must be in the same directory
            
            **Setup with Crontab:**
            ```bash
            # Edit crontab
            crontab -e
            
            # Add this line (replace with your actual path):
            * * * * * cd /path/to/your/app && /usr/bin/python3 background_processor.py >> logs/cron.log 2>&1
            ```
            
            **Setup with systemd timer (recommended):**
            ```bash
            # Create service file: /etc/systemd/system/deal-processor.service
            [Unit]
            Description=Real Estate Deal Processor
            
            [Service]
            Type=oneshot
            WorkingDirectory=/path/to/your/app
            ExecStart=/usr/bin/python3 /path/to/your/app/background_processor.py
            User=yourusername
            
            # Create timer file: /etc/systemd/system/deal-processor.timer
            [Unit]
            Description=Run Deal Processor every minute
            
            [Timer]
            OnCalendar=*:0/1
            Persistent=true
            
            [Install]
            WantedBy=timers.target
            
            # Enable and start
            sudo systemctl enable deal-processor.timer
            sudo systemctl start deal-processor.timer
            ```
            
            **Log File Location:** `./logs/background_processor.log`
            """)
    
    def render_settings(self):
        """Settings page"""
        st.title("⚙️ Settings")
        
        st.subheader("🔐 Microsoft Graph API")
        
        st.info("""
        This application uses the same Microsoft Graph API authentication that you're already using 
        for reading emails. To send emails, you need to add the **Mail.Send** permission.
        """)
        
        with st.expander("🔧 How to Add Mail.Send Permission"):
            st.markdown("""
            ### Add Mail.Send Permission to Your Azure AD App
            
            1. **Go to Azure Portal**
               - Visit: https://portal.azure.com
               - Navigate to "Azure Active Directory" → "App registrations"
            
            2. **Select Your App**
               - Find and click on your application (the one used for email authentication)
            
            3. **Add API Permissions**
               - Click "API permissions" in the left menu
               - Click "+ Add a permission"
               - Select "Microsoft Graph"
               - Choose "Delegated permissions"
               - Search for and check: **`Mail.Send`**
               - Click "Add permissions"
            
            4. **Grant Admin Consent** (if required by your organization)
               - Click "Grant admin consent for [Your Organization]"
               - Confirm by clicking "Yes"
            
            5. **Update Your Code** (if needed)
               - Check your `auth.py` file where you define scopes
               - Make sure `Mail.Send` is included in the scopes list:
               ```python
               SCOPES = [
                   'https://graph.microsoft.com/Mail.Read',
                   'https://graph.microsoft.com/Mail.Send',  # Add this line
                   'offline_access'
               ]
               ```
            
            6. **Re-authenticate**
               - Come back to this app
               - Click "Clear Saved Token" in the sidebar
               - Click "Authenticate Now" to get a new token with the updated permissions
            
            ### Required Permissions Summary:
            - ✅ `Mail.Read` - Already granted (for reading emails)
            - ⚠️ `Mail.Send` - **NEEDED** (for sending emails)
            - 📌 Optional: `Mail.Send.Shared` - If you need to send on behalf of shared mailboxes
            """)
        
        st.divider()
        
        # Test Graph API connection
        if st.button("🧪 Test Graph API Connection"):
            token = self._get_graph_token()
            if token:
                try:
                    headers = {'Authorization': f'Bearer {token}'}
                    
                    # Test basic connection
                    response = requests.get(
                        'https://graph.microsoft.com/v1.0/me',
                        headers=headers
                    )
                    if response.status_code == 200:
                        user_data = response.json()
                        st.success(f"✅ Connected as: {user_data.get('mail', user_data.get('userPrincipalName'))}")
                    else:
                        st.error(f"❌ API Error: {response.status_code}")
                        return
                    
                    # Check token permissions
                    st.write("**Checking permissions...**")
                    
                    # Try to access mailbox (read permission)
                    response = requests.get(
                        'https://graph.microsoft.com/v1.0/me/messages?$top=1',
                        headers=headers
                    )
                    if response.status_code == 200:
                        st.success("✅ Mail.Read permission: OK")
                    else:
                        st.warning("⚠️ Mail.Read permission: Not granted")
                    
                    # Try to check send permission by getting mail folders
                    response = requests.get(
                        'https://graph.microsoft.com/v1.0/me/mailFolders/sentitems',
                        headers=headers
                    )
                    if response.status_code == 200:
                        st.success("✅ Can access Sent Items")
                    else:
                        st.warning("⚠️ Cannot access Sent Items")
                    
                    # Check if we can send (this won't actually send, just checks permission)
                    st.info("💡 To send emails, you need to add **Mail.Send** permission to your Azure AD app")
                    
                    with st.expander("📋 Current Token Info"):
                        # Decode token to show scopes (if it's a JWT)
                        try:
                            import base64
                            # JWT tokens have 3 parts separated by dots
                            parts = token.split('.')
                            if len(parts) == 3:
                                # Decode the payload (second part)
                                payload = parts[1]
                                # Add padding if needed
                                padding = 4 - len(payload) % 4
                                if padding != 4:
                                    payload += '=' * padding
                                decoded = base64.urlsafe_b64decode(payload)
                                import json
                                token_data = json.loads(decoded)
                                st.json({
                                    'scopes': token_data.get('scp', 'Not found'),
                                    'app_id': token_data.get('appid', 'Not found'),
                                    'expires': datetime.fromtimestamp(token_data.get('exp', 0)).isoformat()
                                })
                        except:
                            st.write("Could not decode token")
                    
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
            else:
                st.error("❌ No access token found. Please authenticate first.")
        
        st.divider()
        
        # Supabase Configuration Section
        st.subheader("🗄️ Supabase Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            supabase_url = st.text_input(
                "Supabase URL",
                value=os.getenv("SUPABASE_URL", ""),
                type="password"
            )
        
        with col2:
            supabase_key = st.text_input(
                "Supabase Key",
                value=os.getenv("SUPABASE_KEY", ""),
                type="password"
            )
        
        if st.button("Test Supabase Connection"):
            if supabase_url and supabase_key:
                try:
                    os.environ["SUPABASE_URL"] = supabase_url
                    os.environ["SUPABASE_KEY"] = supabase_key
                    
                    test_client = SupabaseDealsClient()
                    stats = test_client.get_stats()
                    st.success(f"✓ Connection successful! Total deals: {stats['total']}")
                except Exception as e:
                    st.error(f"Connection failed: {e}")
            else:
                st.warning("Please enter both URL and Key")
        
        st.subheader("Database Setup")
        
        with st.expander("Create Table SQL"):
            st.code("""
CREATE TABLE IF NOT EXISTS deals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email_id TEXT UNIQUE NOT NULL,
    subject TEXT,
    sender TEXT,
    sender_name TEXT,
    received_date TIMESTAMP,
    deal_type TEXT,
    confidence INTEGER,
    status TEXT DEFAULT 'pending',
    email_data JSONB,
    analysis_data JSONB,
    property_details JSONB,
    excel_file_path TEXT,
    approved_by TEXT,
    approved_date TIMESTAMP,
    processed_date TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deals_email_id ON deals(email_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
CREATE INDEX IF NOT EXISTS idx_deals_processed_date ON deals(processed_date DESC);
            """, language="sql")
            
            st.info("Copy and run this SQL in your Supabase SQL Editor")
    
    def _check_automation_active(self):
        """Check if automation is running"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0 and 'background_processor.py' in result.stdout:
                return True
            
            # Check systemd timer
            result = subprocess.run(
                ['systemctl', 'is-active', 'deal-processor.timer'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _get_last_run_time(self):
        """Get last run time from logs"""
        try:
            log_file = './logs/background_processor.log'
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if 'Timestamp:' in line:
                            return line.split('Timestamp:')[1].strip()[:19]
            return "Never"
        except:
            return "Unknown"
    
    def _start_automation(self):
        """Start background automation"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            processor_script = os.path.join(script_dir, "background_processor.py")
            python_path = sys.executable
            
            # Check if script exists
            if not os.path.exists(processor_script):
                st.error("background_processor.py not found")
                return False
            
            cron_entry = f"* * * * * cd {script_dir} && {python_path} {processor_script} >> {script_dir}/logs/cron.log 2>&1"
            
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            if 'background_processor.py' not in current_crontab:
                new_crontab = current_crontab.rstrip() + '\n' + cron_entry + '\n'
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_crontab)
                return process.returncode == 0
            return True
            
        except Exception as e:
            st.error(f"Error starting automation: {e}")
            return False
    
    def _stop_automation(self):
        """Stop background automation"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                filtered = [l for l in lines if 'background_processor.py' not in l]
                new_crontab = '\n'.join(filtered)
                
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_crontab)
                return True
            return False
        except:
            return False
    
    def _run_once(self):
        """Run processor once manually"""
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_processor.py")
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except:
            return False
    
    def _run_once_with_output(self):
        """Run processor once with live output in Streamlit"""
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_processor.py")
            
            st.write("Starting background processor...")
            
            # Run and capture output
            result = subprocess.run(
                [sys.executable, script_path], 
                capture_output=True, 
                text=True, 
                timeout=300
            )
            
            # Show output
            if result.stdout:
                st.write("**Output:**")
                st.code(result.stdout, language='log')
            
            if result.stderr and result.returncode != 0:
                st.error("**Errors:**")
                st.code(result.stderr, language='log')
            
            if result.returncode == 0:
                st.success("✓ Processing completed successfully")
                
                # Show summary from logs
                log_file = './logs/background_processor.log'
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        logs = f.read()
                        # Extract summary
                        if 'PROCESSING SUMMARY' in logs:
                            summary_start = logs.rfind('PROCESSING SUMMARY')
                            summary_section = logs[summary_start:summary_start+500]
                            st.write("**Summary:**")
                            st.text(summary_section)
                
                return True
            else:
                st.error("✗ Processing failed")
                return False
                
        except subprocess.TimeoutExpired:
            st.error("⏱ Processing timed out (5 minutes)")
            return False
        except Exception as e:
            st.error(f"Error: {e}")
            return False


def main():
    """Main entry point"""
    app = RealEstateApp()
    app.run()


if __name__ == "__main__":
    main()