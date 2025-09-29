#!/usr/bin/env python3
"""
Background Email Processor with Clear Logging
"""

import os
import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_status import get_authenticated_processor
from supabase_client import SupabaseDealsClient
from template import *

# Create logs directory
os.makedirs('./logs', exist_ok=True)

# Setup detailed logging
log_file = './logs/background_processor.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def log_separator():
    """Print a visual separator"""
    separator = "=" * 80
    logger.info(separator)


def log_section(title):
    """Print a section header"""
    logger.info("")
    logger.info(f">>> {title}")
    logger.info("-" * 80)


class BackgroundEmailProcessor:
    """Process emails in background with clear logging"""
    
    def __init__(self):
        self.supabase = SupabaseDealsClient()
        self.max_emails_per_run = 10
        self.min_confidence = 30
        
        # Cutoff date - only process emails after this datetime
        # Set to Sep 28, 2025 6:00 AM UTC
        self.cutoff_date = datetime(2025, 9, 28, 6, 0, 0, tzinfo=timezone.utc)
        
        logger.info(f"Cutoff date set to: {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("Only emails received AFTER this time will be processed")
    
    def should_process_email(self, email_data):
        """
        Check if email should be processed
        Returns: (should_process, reason)
        """
        email_id = email_data.get('email_id')
        
        # Check 1: Is it after cutoff date?
        try:
            received_date_str = email_data.get('receivedDateTime')
            if not received_date_str:
                return False, "No received date"
            
            received_date = datetime.fromisoformat(received_date_str.replace('Z', '+00:00'))
            
            if received_date <= self.cutoff_date:
                return False, f"Before cutoff ({received_date.strftime('%Y-%m-%d %H:%M')})"
        except Exception as e:
            return False, f"Date parse error: {e}"
        
        # Check 2: Already processed? (Check Supabase)
        if self.supabase.deal_exists(email_id):
            return False, "Already processed (duplicate)"
        

        
        # All checks passed
        return True, f"OK - New email after cutoff"
    
    def run_comprehensive_analysis(self, email_data):
        """Run full financial analysis"""
        try:
            log_section("RUNNING COMPREHENSIVE ANALYSIS")
            
            analysis_data = {}
            
            logger.info("Step 1/15: Deal Appraisal")
            analysis_data['deal_appraisal'] = deal_appraisal(email_data)
            
            logger.info("Step 2/15: GDV Analysis")
            analysis_data['gdv'] = gross_development_value(email_data)
            
            logger.info("Step 3/15: Acquisition Costs")
            analysis_data['acquisition_costs'] = acquisition_costs(email_data)
            
            logger.info("Step 4/15: Build Costs")
            analysis_data['build_costs'] = build_costs(
                gdv_dict=analysis_data['gdv'], 
                acquisition_dict=analysis_data['acquisition_costs']
            )
            
            # Safely get timeline months
            property_details = email_data.get('property_details') or {}
            timeline = property_details.get('timeline') or {}
            timeline_months = timeline.get('total_development_duration_months') or 24
            
            logger.info("Step 5/15: Professional Fees")
            analysis_data['professional_fees'] = professional_fees(
                gdv_dict=analysis_data['gdv'],
                acquisition_dict=analysis_data['acquisition_costs'],
                build_cost_dict=analysis_data['build_costs'],
                timeline_months=timeline_months
            )
            
            logger.info("Step 6/15: Statutory Costs")
            analysis_data['statutory_costs'] = statutory_costs(gdv_dict=analysis_data['gdv'])
            
            logger.info("Step 7/15: Total Development Costs")
            analysis_data['total_development_costs'] = total_development_costs(
                build_cost_dict=analysis_data['build_costs'],
                prof_fees_dict=analysis_data['professional_fees'],
                statutory_dict=analysis_data['statutory_costs']
            )
            
            logger.info("Step 8/15: Profit Pre-Funding")
            analysis_data['profit_pre_funding'] = profit_pre_funding_costs(
                gdv_dict=analysis_data['gdv'],
                acquisition_dict=analysis_data['acquisition_costs'],
                dev_costs_dict=analysis_data['total_development_costs']
            )
            
            logger.info("Step 9/15: Finance Costs")
            analysis_data['finance_costs'] = finance_costs(
                acquisition_dict=analysis_data['acquisition_costs'],
                dev_costs_dict=analysis_data['total_development_costs'],
                timeline_months=timeline_months
            )
            
            logger.info("Step 10/15: Lenders Other Costs")
            # Use the timeline dict we already got
            analysis_data['lenders_other_costs'] = lenders_other_costs(timeline_months=timeline or {})
            
            logger.info("Step 11/15: Total Funding Costs")
            analysis_data['total_funding_costs'] = total_funding_costs(
                finance_dict=analysis_data['finance_costs'],
                lenders_dict=analysis_data['lenders_other_costs']
            )
            
            logger.info("Step 12/15: Selling Costs")
            analysis_data['selling_costs'] = selling_costs(gdv_dict=analysis_data['gdv'])
            
            logger.info("Step 13/15: Total Costs")
            analysis_data['total_costs'] = total_costs(
                acquisition_dict=analysis_data['acquisition_costs'],
                funding_costs_dict=analysis_data['total_funding_costs'],
                dev_costs_dict=analysis_data['total_development_costs'],
                selling_dict=analysis_data['selling_costs']
            )
            
            logger.info("Step 14/15: Net Profit Analysis")
            analysis_data['net_profit_analysis'] = net_profit_analysis(
                gdv_dict=analysis_data['gdv'],
                total_costs_dict=analysis_data['total_costs']
            )
            
            logger.info("Step 15/15: Calculating KPIs")
            analysis_data['lending_analysis'] = lending_analysis(
                total_costs_dict=analysis_data['total_costs'],
                gdv_dict=analysis_data['gdv'],
                own_funds_invested=1500
            )
            
            total_units = analysis_data['gdv'][-1]['no_of_units'] if analysis_data['gdv'] else 1
            analysis_data['post_development'] = post_development_analysis(
                gdv_dict=analysis_data['gdv'],
                total_units=total_units,
                rental_per_unit_per_month=3000
            )
            
            analysis_data['funding_workings'] = funding_workings(
                acquisition_dict=analysis_data['acquisition_costs'],
                dev_costs_dict=analysis_data['total_development_costs'],
                statutory_dict=analysis_data['statutory_costs'],
                funding_costs_dict=analysis_data['total_funding_costs'],
                selling_dict=analysis_data['selling_costs'],
                finance_dict=analysis_data['finance_costs']
            )
            
            analysis_data['kpis'] = calculate_kpis(
                email_dict=email_data,
                funding_workings_dict=analysis_data['funding_workings'],
                net_profit_dict=analysis_data['net_profit_analysis'],
                lending_dict=analysis_data['lenders_other_costs'],
                post_dev_dict=analysis_data['post_development'],
                timeline_months=timeline_months
            )
            
            logger.info("✓ Analysis completed successfully")
            
            # Log key metrics
            if 'net_profit_analysis' in analysis_data:
                net_profit = analysis_data['net_profit_analysis'].get('net_profit') or 0
                profit_margin = analysis_data['net_profit_analysis'].get('net_profit_on_gdv') or 0
                
                try:
                    logger.info(f"  Net Profit: £{float(net_profit):,.0f}")
                    logger.info(f"  Profit Margin: {float(profit_margin)*100:.1f}%")
                except (TypeError, ValueError):
                    logger.info(f"  Net Profit: Not calculated")
                    logger.info(f"  Profit Margin: Not calculated")
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"✗ Analysis failed: {e}", exc_info=True)
            return None
    
    def process_email(self, email_data, email_number, total_emails,processor):
        """Process a single email if it passes all checks"""
        try:
            
            result = {
                'email_id': email_data.get('id'),
                'subject': email_data.get('subject'),
                'sender': email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                'sender_name': email_data.get('from', {}).get('emailAddress', {}).get('name', 'Unknown'),
                'received_date': email_data.get('receivedDateTime'),
                'has_attachments': email_data.get('hasAttachments', False),

            }
                
            log_section(f"EMAIL {email_number}/{total_emails}")
            logger.info(f"Subject: {result['subject'][:60]}")
            logger.info(f"Email sender ID: {result['sender']}")
    
            
            # Check if should process
            should_process, reason = self.should_process_email(email_data)
            
            if not should_process:
                logger.warning(f"✗ SKIPPED: {reason}")
                return False
            
            logger.info(f"✓ {reason}")

            result_email_data = processor.process_single_email(email_data)
            
            # Run analysis
            analysis_data = self.run_comprehensive_analysis(result_email_data)
            
            if not analysis_data:
                logger.error("✗ FAILED: Analysis failed")
                return None
            
            # Save to Supabase
            log_section("SAVING TO SUPABASE")
            result = self.supabase.insert_deal(email_data, analysis_data)
            
            if result:
                deal_status = result.get('status', 'pending').upper()
                logger.info(f"✓ SUCCESS: Deal saved to Supabase")
                logger.info(f"  Deal ID: {result.get('id')}")
                logger.info(f"  Status: {deal_status}")
                return True
            else:
                logger.error("✗ FAILED: Could not save to Supabase")
                return None
            
        except Exception as e:
            logger.error(f"✗ ERROR: {e}", exc_info=True)
            return None
    
    def run(self):
        """Main processing loop"""
        log_separator()
        logger.info("")
        logger.info("  BACKGROUND EMAIL PROCESSOR STARTING")
        logger.info(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        log_separator()
        
        try:
            # Authentication
            log_section("AUTHENTICATION")
            logger.info("Authenticating with email service...")
            
            processor = get_authenticated_processor()
            
            if not processor:
                logger.error("✗ Authentication failed")
                log_separator()
                return
            
            logger.info("✓ Authentication successful")
            
            # Fetch emails
            log_section("FETCHING UNREAD EMAILS")
            logger.info(f"Fetching up to {self.max_emails_per_run} unread emails...")
            
            results = processor.process_all_unread_emails(limit=self.max_emails_per_run)
            
            if not results:
                logger.info("ℹ No unread emails found")
                log_separator()
                return
            
            logger.info(f"✓ Found {len(results)} unread emails")
            
            # Process each email ONE BY ONE
            log_section("PROCESSING EMAILS")
            logger.info(f"Processing rules:")
            logger.info(f"  ✓ Must be after {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  ✓ Must be unique (not already in Supabase)")
            logger.info(f"  ✓ Must have confidence >= {self.min_confidence}%")
            logger.info("")
            
            processed_count = 0
            skipped_count = 0
            failed_count = 0
            
            # Process one by one
            for i, email_data in enumerate(results, 1):
                result = self.process_email(email_data, i, len(results),processor)
                
                if result is True:
                    processed_count += 1
                elif result is False:
                    skipped_count += 1
                else:
                    failed_count += 1
                
                # Pause between emails
                import time
                time.sleep(0.5)
            
            # Summary
            log_separator()
            log_section("SUMMARY")
            logger.info(f"Total unread emails fetched: {len(results)}")
            logger.info(f"✓ Processed successfully: {processed_count}")
            logger.info(f"○ Skipped: {skipped_count}")
            if failed_count > 0:
                logger.info(f"✗ Failed: {failed_count}")
            
            logger.info("")
            logger.info("Skipped reasons: duplicates, before cutoff, or low confidence")
            
            # Database stats
            log_section("DATABASE STATISTICS")
            stats = self.supabase.get_stats()
            logger.info(f"Total deals in database: {stats['total']}")
            logger.info(f"  - Pending: {stats['pending']}")
            logger.info(f"  - Approved: {stats['approved']}")
            
            log_separator()
            logger.info(f"Run completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_separator()
            logger.info("")
            
        except Exception as e:
            logger.error(f"✗ FATAL ERROR: {e}", exc_info=True)
            log_separator()


def main():
    """Entry point"""
    try:
        processor = BackgroundEmailProcessor()
        processor.run()
    except Exception as e:
        logger.error(f"✗ FATAL ERROR IN MAIN: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()