"""
Supabase Client for Real Estate Deal Storage
"""

import os
import json
from datetime import datetime
from supabase import create_client, Client
from typing import Optional, List, Dict

from dotenv import load_dotenv

load_dotenv()


class SupabaseDealsClient:
    """Handle all Supabase operations for deals"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.url, self.key)
        self.table_name = "deals"
    
    def deal_exists(self, email_id: str) -> bool:
        """Check if a deal with this email_id already exists"""
        try:
            response = self.client.table(self.table_name)\
                .select("id")\
                .eq("email_id", email_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error checking if deal exists: {e}")
            return False
    
    def insert_deal(self, email_data: Dict, analysis_data: Optional[Dict] = None) -> Optional[Dict]:
        """Insert a new deal into database"""
        try:
            if self.deal_exists(email_data.get('id')):
                print(f"Deal with email_id {email_data.get('id')} already exists")
                return None



            deal = {
                'email_id': email_data.get('id'),
                'subject': email_data.get('subject'),
                'sender': email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                'sender_name': email_data.get('from', {}).get('emailAddress', {}).get('name', 'Unknown'),
                'received_date': email_data.get('receivedDateTime'),
                'deal_type': email_data.get('deal_type'),
                'confidence': email_data.get('confidence', 0),
                'status':  'pending',
                'email_data': json.dumps(email_data),
                'analysis_data': json.dumps(analysis_data) if analysis_data else None,
                'property_details': json.dumps(email_data.get('property_details', {})),
                'processed_date': datetime.now().isoformat()
            }
            
            response = self.client.table(self.table_name).insert(deal).execute()
            
            if response.data:
                print(f"Deal inserted successfully: {email_data.get('subject')}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            print(f"Error inserting deal: {e}")
            return None
    
    def get_pending_deals(self) -> List[Dict]:
        """Get all deals with pending status"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("status", "pending")\
                .order("processed_date", desc=True)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"Error getting pending deals: {e}")
            return []
    
    def get_approved_deals(self) -> List[Dict]:
        """Get all deals with approved status"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("status", "approved")\
                .order("processed_date", desc=True)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"Error getting approved deals: {e}")
            return []
    
    def get_deal_by_id(self, deal_id: str) -> Optional[Dict]:
        """Get a specific deal by ID"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("id", deal_id)\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting deal: {e}")
            return None
    
    def update_deal_status(self, deal_id: str, status: str, approved_by: Optional[str] = None) -> bool:
        """Update deal status"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if status == 'approved' and approved_by:
                update_data['approved_by'] = approved_by
                update_data['approved_date'] = datetime.now().isoformat()
            
            response = self.client.table(self.table_name)\
                .update(update_data)\
                .eq("id", deal_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating deal status: {e}")
            return False
    
    def update_excel_path(self, deal_id: str, excel_path: str) -> bool:
        """Update the Excel file path for a deal"""
        try:
            response = self.client.table(self.table_name)\
                .update({
                    'excel_file_path': excel_path,
                    'updated_at': datetime.now().isoformat()
                })\
                .eq("id", deal_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating Excel path: {e}")
            return False
    
    def update_deal_notes(self, deal_id: str, notes: str) -> bool:
        """Update notes for a deal"""
        try:
            response = self.client.table(self.table_name)\
                .update({
                    'notes': notes,
                    'updated_at': datetime.now().isoformat()
                })\
                .eq("id", deal_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating notes: {e}")
            return False
    
    def delete_deal(self, deal_id: str) -> bool:
        """Delete a deal"""
        try:
            response = self.client.table(self.table_name)\
                .delete()\
                .eq("id", deal_id)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error deleting deal: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get statistics about deals"""
        try:
            total = self.client.table(self.table_name).select("id", count="exact").execute()
            pending = self.client.table(self.table_name).select("id", count="exact").eq("status", "pending").execute()
            approved = self.client.table(self.table_name).select("id", count="exact").eq("status", "approved").execute()
            
            return {
                'total': total.count,
                'pending': pending.count,
                'approved': approved.count
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'total': 0, 'pending': 0, 'approved': 0}