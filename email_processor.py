#!/usr/bin/env python3
"""
Main email processing module that coordinates fetching, content processing, and classification
"""

import json
from datetime import datetime
from typing import Dict, List
from auth import Authenticator
from email_fetcher import EmailFetcher
from content_processor import ContentProcessor
from deal_classifier import DealClassifier
from config import TARGET_EMAIL, DEFAULT_EMAIL_LIMIT


class EmailProcessor:
    def __init__(self):
        self.authenticator = Authenticator()
        self.email_fetcher = EmailFetcher(self.authenticator)
        self.content_processor = ContentProcessor(self.email_fetcher)
        self.deal_classifier = DealClassifier()
    
    def process_single_email(self, email: Dict) -> Dict:
        """Process a single email: fetch content and classify"""
        email_id = email['id']
        subject = email.get('subject', 'No Subject')
        
        print(f"\nProcessing email: {subject}")
        print(f"From: {email.get('from', {}).get('emailAddress', {}).get('name', 'Unknown')}")
        print(f"Date: {email.get('receivedDateTime', 'Unknown')}")
        
        # Get full email content to ensure we have complete body
        full_email = self.email_fetcher.get_full_email(email_id)
        if full_email:
            email = full_email  # Use the full email data
        
        # Enhanced attachment detection
        attachment_info = self.email_fetcher.check_all_attachments(email_id)
        if attachment_info["has_attachments"]:
            print(f"Attachments: Yes ({attachment_info['attachment_count']} total)")
            print(f"  - Inline images: {attachment_info['inline_images']}")
            print(f"  - File attachments: {attachment_info['file_attachments']}")
        else:
            print(f"Attachments: {email.get('hasAttachments', False)}")
        
        # Concatenate all content
        combined_content = self.content_processor.concatenate_email_content(email)
        
        # Classify deal type
        classification = self.deal_classifier.classify_deal_type(combined_content)
        
        # Prepare result - convert Pydantic model to dict for compatibility
        result = {
            'email_id': email_id,
            'subject': subject,
            'sender': email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
            'sender_name': email.get('from', {}).get('emailAddress', {}).get('name', 'Unknown'),
            'received_date': email.get('receivedDateTime'),
            'has_attachments': email.get('hasAttachments', False),
            'combined_content': combined_content,
            'deal_type': classification.deal_type,
            'confidence': classification.confidence,
            'reasoning': classification.reasoning,
            'key_indicators': classification.key_indicators,
            'property_details': classification.property_details.dict(),
            'processed_date': datetime.now().isoformat()
        }
        
        return result
    
    def process_all_unread_emails(self, limit: int = DEFAULT_EMAIL_LIMIT) -> List[Dict]:
        """Main function: fetch unread emails and classify each one"""
        print(f"Starting email processing and classification for {TARGET_EMAIL} (limit: {limit})...")
        
        # Fetch unread emails from specific sender with limit
        emails = self.email_fetcher.fetch_unread_emails(sender_email=TARGET_EMAIL, limit=limit)
        
        if not emails:
            print(f"No unread emails from {TARGET_EMAIL} to process")
            return []
        
        # results = []
        
        # print(f"\nProcessing {len(emails)} emails...")
        
        # for i, email in enumerate(emails, 1):
        #     print(f"\nProcessing email {i}/{len(emails)}")
            
        #     try:
        #         result = self.process_single_email(email)
        #         results.append(result)
                
        #         print(f"Email {i} processed successfully!")
        #         print(f"Deal Type: {result['deal_type']}")
        #         print(f"Confidence: {result['confidence']}%")
                
        #     except Exception as e:
        #         print(f"Error processing email {i}: {e}")
        #         continue
        
        return emails
    
    def save_results(self, results: List[Dict]) -> str:
        """Save results to JSON file"""
        if not results:
            return ""
        
        filename = f"email_classifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {filename}")
        return filename
    
    def print_summary(self, results: List[Dict]):
        """Print processing summary"""
        if not results:
            return
        
        print(f"\n{'='*60}")
        print(f"PROCESSING SUMMARY:")
        print(f"Successfully processed: {len(results)} emails")
        
        # Show deal type distribution
        deal_type_counts = {}
        for result in results:
            deal_type = result['deal_type']
            deal_type_counts[deal_type] = deal_type_counts.get(deal_type, 0) + 1
        
        print(f"\nDEAL TYPE DISTRIBUTION:")
        for deal_type, count in deal_type_counts.items():
            confidence_avg = sum(r['confidence'] for r in results if r['deal_type'] == deal_type) / count
            print(f"  {deal_type}: {count} email(s) (avg confidence: {confidence_avg:.1f}%)")
    
    def print_detailed_results(self, results: List[Dict]):
        """Print detailed results for each email"""
        if not results:
            return
        
        print(f"\nDETAILED RESULTS:")
        print("=" * 60)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['subject'][:60]}...")
            print(f"   From: {result['sender_name']}")
            print(f"   Deal Type: {result['deal_type']}")
            print(f"   Confidence: {result['confidence']}%")
            print(f"   Reasoning: {result['reasoning']}")
            if result['key_indicators']:
                print(f"   Key Indicators: {', '.join(result['key_indicators'])}")