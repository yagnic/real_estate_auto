#!/usr/bin/env python3
"""
Email fetching module for Microsoft Graph API
"""

import requests
from typing import List, Dict, Optional
from auth import Authenticator


class EmailFetcher:
    def __init__(self, authenticator: Authenticator):
        self.auth = authenticator
    
    def fetch_unread_emails(self, sender_email: str = None, limit: int = None) -> List[Dict]:
        """Fetch unread emails from Outlook, optionally filtered by sender and limited by count"""
        token = self.auth.get_token()
        if not token:
            return []
        
        if sender_email and limit:
            print(f"Fetching up to {limit} unread emails from {sender_email}...")
        elif sender_email:
            print(f"Fetching unread emails from {sender_email}...")
        elif limit:
            print(f"Fetching up to {limit} unread emails...")
        else:
            print("Fetching unread emails...")
        
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://graph.microsoft.com/v1.0/me/messages"
        
        # Build filter conditions - try without sender filter first if it fails
        if sender_email:
            filter_query = f"isRead eq false and from/emailAddress/address eq '{sender_email}'"
        else:
            filter_query = "isRead eq false"
        
        params = {
            "$filter": filter_query,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,hasAttachments,importance"
        }
        
        # Add limit if specified
        if limit:
            params["$top"] = limit
        
        print(f"Debug: Filter query = {filter_query}")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            emails = data.get("value", [])
            
            # If we filtered by sender but got no results, try without filter and filter locally
            if sender_email and len(emails) == 0:
                print(f"No emails found with server-side filter. Trying client-side filtering...")
                return self._fetch_and_filter_locally(sender_email, limit, headers, url)
            
            if sender_email and limit:
                print(f"Found {len(emails)} unread emails from {sender_email} (limited to {limit})")
            elif sender_email:
                print(f"Found {len(emails)} unread emails from {sender_email}")
            elif limit:
                print(f"Found {len(emails)} unread emails (limited to {limit})")
            else:
                print(f"Found {len(emails)} unread emails")
            return emails
        else:
            print(f"Failed to fetch emails: {response.status_code}")
            print(f"Error response: {response.text}")
            
            # If server-side filtering failed, try without sender filter
            if sender_email:
                print("Trying without sender filter...")
                return self._fetch_and_filter_locally(sender_email, limit, headers, url)
            
            return []
    
    def _fetch_and_filter_locally(self, sender_email: str, limit: int, headers: dict, url: str) -> List[Dict]:
        """Fallback method: fetch all unread emails and filter locally"""
        params = {
            "$filter": "isRead eq false",
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,hasAttachments,importance"
        }
        
        # Fetch more emails if we need to filter locally
        if limit:
            params["$top"] = limit * 3  # Get more to account for filtering
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            all_emails = data.get("value", [])
            
            # Filter by sender locally
            filtered_emails = []
            for email in all_emails:
                email_from = email.get('from', {}).get('emailAddress', {}).get('address', '').lower()
                if email_from == sender_email.lower():
                    filtered_emails.append(email)
                    if limit and len(filtered_emails) >= limit:
                        break
            
            print(f"Found {len(filtered_emails)} unread emails from {sender_email} (client-side filtered)")
            return filtered_emails
        else:
            print(f"Fallback fetch also failed: {response.status_code}")
            return []
    
    def get_email_attachments(self, email_id: str) -> List[Dict]:
        """Get attachments for a specific email including inline content"""
        token = self.auth.get_token()
        if not token:
            return []
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments"
        
        print(f"Fetching attachments for email {email_id[:8]}...")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            attachments = response.json().get("value", [])
            print(f"API returned {len(attachments)} attachments")
            
            # Debug each attachment
            for i, att in enumerate(attachments):
                print(f"  Attachment {i+1}:")
                print(f"    ID: {att.get('id', 'No ID')[:20]}...")
                print(f"    Name: {att.get('name', 'No name')}")
                print(f"    Content Type: {att.get('contentType', 'Unknown')}")
                print(f"    Size: {att.get('size', 0)} bytes")
                print(f"    Is Inline: {att.get('isInline', False)}")
                print(f"    Has Content Bytes: {'Yes' if 'contentBytes' in att else 'No'}")
            
            return attachments
        else:
            print(f"Failed to get attachments for email {email_id[:8]}: {response.status_code}")
            print(f"Error: {response.text}")
            return []
    
    def get_full_email(self, email_id: str) -> Optional[Dict]:
        """Get complete email with full body content"""
        token = self.auth.get_token()
        if not token:
            return None
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
        params = {
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,hasAttachments,importance"
        }
        
        print(f"Fetching full email content for {email_id[:8]}...")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            email_data = response.json()
            
            # Debug body information
            body = email_data.get('body', {})
            print(f"Email body debug:")
            print(f"  Body type: {type(body)}")
            if isinstance(body, dict):
                print(f"  Content type: {body.get('contentType', 'Not specified')}")
                content = body.get('content', '')
                print(f"  Content length: {len(content)} characters")
                if content:
                    print(f"  Content preview (first 500 chars): {content[:500]}...")
                    print(f"  Content preview (last 200 chars): ...{content[-200:]}")
            print(f"  Has attachments flag: {email_data.get('hasAttachments', False)}")
            
            # Also check if there are other body-related fields
            for key in email_data.keys():
                if 'body' in key.lower() or 'content' in key.lower():
                    print(f"  Found body-related field: {key}")
            
            return email_data
        else:
            print(f"Failed to get full email: {response.status_code}")
            return None
    
    def download_attachment(self, email_id: str, attachment_id: str) -> Optional[Dict]:
        """Download specific attachment including inline images"""
        token = self.auth.get_token()
        if not token:
            return None
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments/{attachment_id}"
        
        print(f"Downloading attachment {attachment_id[:8]}...")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            attachment_data = response.json()
            
            # Debug information
            print(f"Downloaded attachment:")
            print(f"  Name: {attachment_data.get('name', 'Unknown')}")
            print(f"  Type: {attachment_data.get('contentType', 'Unknown')}")
            print(f"  Size: {attachment_data.get('size', 0)} bytes")
            print(f"  IsInline: {attachment_data.get('isInline', False)}")
            print(f"  Has content: {'Yes' if attachment_data.get('contentBytes') else 'No'}")
            
            return attachment_data
        else:
            print(f"Failed to download attachment {attachment_id[:8]}: {response.status_code}")
            if response.status_code == 403:
                print("  Error: Insufficient permissions to download attachment")
            elif response.status_code == 404:
                print("  Error: Attachment not found")
            return None
    
    def check_all_attachments(self, email_id: str) -> Dict:
        """Check all types of attachments including inline images"""
        token = self.auth.get_token()
        if not token:
            return {"has_attachments": False, "attachment_count": 0, "attachment_types": []}
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get regular attachments
        attachments_url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments"
        response = requests.get(attachments_url, headers=headers)
        
        attachments_info = {
            "has_attachments": False,
            "attachment_count": 0,
            "attachment_types": [],
            "inline_images": 0,
            "file_attachments": 0
        }
        
        if response.status_code == 200:
            attachments = response.json().get("value", [])
            attachments_info["attachment_count"] = len(attachments)
            attachments_info["has_attachments"] = len(attachments) > 0
            
            for att in attachments:
                att_type = att.get('contentType', '').lower()
                att_name = att.get('name', 'Unknown')
                is_inline = att.get('isInline', False)
                
                attachments_info["attachment_types"].append({
                    "name": att_name,
                    "type": att_type,
                    "is_inline": is_inline,
                    "size": att.get('size', 0)
                })
                
                if is_inline and 'image' in att_type:
                    attachments_info["inline_images"] += 1
                else:
                    attachments_info["file_attachments"] += 1
        
        print(f"Debug: Attachment analysis - Total: {attachments_info['attachment_count']}, "
              f"Inline images: {attachments_info['inline_images']}, "
              f"File attachments: {attachments_info['file_attachments']}")
        
        return attachments_info
        """Get complete email with full body content"""
        token = self.auth.get_token()
        if not token:
            return None
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
        params = {
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,hasAttachments,importance"
        }
        
        print(f"Fetching full email content for {email_id[:8]}...")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            email_data = response.json()
            
            # Debug body information
            body = email_data.get('body', {})
            print(f"Email body debug:")
            print(f"  Body type: {type(body)}")
            if isinstance(body, dict):
                print(f"  Content type: {body.get('contentType', 'Not specified')}")
                content = body.get('content', '')
                print(f"  Content length: {len(content)} characters")
                if content:
                    print(f"  Content preview: {content[:200]}...")
            print(f"  Has attachments flag: {email_data.get('hasAttachments', False)}")
            
            return email_data
        else:
            print(f"Failed to get full email: {response.status_code}")
            return None
        """Check all types of attachments including inline images"""
        token = self.auth.get_token()
        if not token:
            return {"has_attachments": False, "attachment_count": 0, "attachment_types": []}
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get regular attachments
        attachments_url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments"
        response = requests.get(attachments_url, headers=headers)
        
        attachments_info = {
            "has_attachments": False,
            "attachment_count": 0,
            "attachment_types": [],
            "inline_images": 0,
            "file_attachments": 0
        }
        
        if response.status_code == 200:
            attachments = response.json().get("value", [])
            attachments_info["attachment_count"] = len(attachments)
            attachments_info["has_attachments"] = len(attachments) > 0
            
            for att in attachments:
                att_type = att.get('contentType', '').lower()
                att_name = att.get('name', 'Unknown')
                is_inline = att.get('isInline', False)
                
                attachments_info["attachment_types"].append({
                    "name": att_name,
                    "type": att_type,
                    "is_inline": is_inline,
                    "size": att.get('size', 0)
                })
                
                if is_inline and 'image' in att_type:
                    attachments_info["inline_images"] += 1
                else:
                    attachments_info["file_attachments"] += 1
        
        print(f"Debug: Attachment analysis - Total: {attachments_info['attachment_count']}, "
              f"Inline images: {attachments_info['inline_images']}, "
              f"File attachments: {attachments_info['file_attachments']}")
        
        return attachments_info