#!/usr/bin/env python3
"""
Assumptions Loader Module
Loads and manages deal assumptions from CSV file dynamically
"""

import pandas as pd
import json
import os
from typing import Dict, Optional, Any
import re

class AssumptionsLoader:
    def __init__(self, csv_path: str = "Assumptions.csv"):
        """Initialize assumptions loader with CSV file path"""
        self.csv_path = csv_path
        self.assumptions_data = None
        self.deal_types = []
        self.assumption_categories = []
        
        print(f"🔧 AssumptionsLoader initialized with: {csv_path}")
        
        # Load assumptions on initialization
        self.load_assumptions()
    
    def load_assumptions(self) -> bool:
        """Load assumptions from CSV file"""
        try:
            if not os.path.exists(self.csv_path):
                print(f"❌ Assumptions CSV not found at: {self.csv_path}")
                return False
            
            print(f"📊 Loading assumptions from: {self.csv_path}")
            
            # Read CSV file
            df = pd.read_csv(self.csv_path)
            
            # Store the dataframe
            self.assumptions_data = df
            
            # Extract deal types (all columns except first one)
            self.deal_types = [col for col in df.columns if col != 'Deal Type>>>']
            
            # Extract assumption categories (all rows)
            self.assumption_categories = df['Deal Type>>>'].tolist()
            
            print(f"✅ Loaded assumptions successfully!")
            print(f"   📈 Deal Types: {len(self.deal_types)}")
            print(f"   📋 Assumption Categories: {len(self.assumption_categories)}")
            
            # Show deal types
            print(f"\n🏠 Available Deal Types:")
            for i, deal_type in enumerate(self.deal_types, 1):
                print(f"   {i}. {deal_type}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading assumptions: {e}")
            return False
    
    def get_deal_types(self) -> list:
        """Get list of all available deal types"""
        return self.deal_types.copy()
    
    def get_assumption_categories(self) -> list:
        """Get list of all assumption categories"""
        return self.assumption_categories.copy()
    
    def get_assumption_value(self, deal_type: str, assumption_category: str) -> Optional[Any]:
        """
        Get specific assumption value for a deal type and category
        
        Args:
            deal_type: Name of the deal type (column name)
            assumption_category: Name of the assumption (row name)
            
        Returns:
            The assumption value or None if not found
        """
        if self.assumptions_data is None:
            print("❌ No assumptions data loaded")
            return None
        
        if deal_type not in self.deal_types:
            print(f"❌ Deal type not found: {deal_type}")
            return None
        
        if assumption_category not in self.assumption_categories:
            print(f"❌ Assumption category not found: {assumption_category}")
            return None
        
        try:
            # Find the row for this assumption category
            row_mask = self.assumptions_data['Deal Type>>>'] == assumption_category
            value = self.assumptions_data.loc[row_mask, deal_type].iloc[0]
            
            # Handle NaN values
            if pd.isna(value) or value == '':
                return None
            
            return value
            
        except Exception as e:
            print(f"❌ Error getting assumption value: {e}")
            return None
    
    def get_all_assumptions_for_deal_type(self, deal_type: str) -> Dict[str, Any]:
        """
        Get all assumptions for a specific deal type
        
        Args:
            deal_type: Name of the deal type
            
        Returns:
            Dictionary with assumption category as key and value as value
        """
        if self.assumptions_data is None:
            print("❌ No assumptions data loaded")
            return {}
        
        if deal_type not in self.deal_types:
            print(f"❌ Deal type not found: {deal_type}")
            return {}
        
        assumptions = {}
        
        for assumption_category in self.assumption_categories:
            value = self.get_assumption_value(deal_type, assumption_category)
            if value is not None:
                assumptions[assumption_category] = value
        
        return assumptions
    
    def parse_assumption_value(self, value: Any, assumption_category: str) -> Any:
        """
        Parse assumption values into appropriate data types
        
        Args:
            value: Raw value from CSV
            assumption_category: The assumption category for context
            
        Returns:
            Parsed value in appropriate data type
        """
        if pd.isna(value) or value == '':
            return None
        
        value_str = str(value).strip()
        
        # Handle percentage values
        if '%' in value_str:
            try:
                # Extract first number and convert to decimal
                numbers = re.findall(r'[\d.]+', value_str)
                if numbers:
                    return float(numbers[0]) / 100
                return value_str
            except:
                return value_str
        
        # Handle monetary values (£)
        if '£' in value_str:
            try:
                # Remove £ and commas, extract number
                clean_str = re.sub(r'[£,]', '', value_str)
                numbers = re.findall(r'[\d.]+', clean_str)
                if numbers:
                    return float(numbers[0])
                return value_str
            except:
                return value_str
        
        # Handle time periods (months, years)
        if 'month' in value_str.lower():
            try:
                numbers = re.findall(r'\d+', value_str)
                if numbers:
                    return int(numbers[0])
                return value_str
            except:
                return value_str
        
        # Handle decimal numbers
        try:
            if '.' in value_str and value_str.replace('.', '').replace('-', '').isdigit():
                return float(value_str)
        except:
            pass
        
        # Handle integers
        try:
            if value_str.replace('-', '').isdigit():
                return int(value_str)
        except:
            pass
        
        # Return as string if no parsing possible
        return value_str
    
    def get_parsed_assumptions_for_deal_type(self, deal_type: str) -> Dict[str, Any]:
        """
        Get all assumptions for a deal type with parsed values
        
        Args:
            deal_type: Name of the deal type
            
        Returns:
            Dictionary with parsed assumption values
        """
        raw_assumptions = self.get_all_assumptions_for_deal_type(deal_type)
        
        parsed_assumptions = {}
        for category, value in raw_assumptions.items():
            parsed_value = self.parse_assumption_value(value, category)
            if parsed_value is not None:
                parsed_assumptions[category] = parsed_value
        
        return parsed_assumptions
    
    def get_standardized_assumptions(self, deal_type: str) -> Dict[str, Any]:
        """
        Get assumptions with standardized field names for easier use in calculations
        
        Args:
            deal_type: Name of the deal type
            
        Returns:
            Dictionary with standardized field names
        """
        parsed_assumptions = self.get_parsed_assumptions_for_deal_type(deal_type)
        
        # Mapping from assumption categories to standardized field names
        field_mapping = {
            'Duration - Land ownership': 'duration_land_months',
            'Duration - Build phase': 'duration_build_months',
            'Duration - Selling period / Sign offs': 'duration_selling_months',
            'Sourcing fee': 'sourcing_fee_percent',
            'Building Insurance': 'building_insurance_percent',
            'Legal and other professional costs': 'legal_costs_percent',
            'Build costs': 'build_costs_per_sqft',
            'Build costs (outside London)': 'build_costs_outside_london',
            'Build contingency': 'build_contingency_percent',
            'Architect': 'architect_fee_percent',
            'Town Planner': 'town_planner_fee_percent',
            'Structural Engineer': 'structural_engineer_fee_percent',
            'Building Control': 'building_control_fee',
            'Project Management': 'project_management_fee',
            'Structural Warranty': 'structural_warranty_percent',
            'Developers\' Quantity Surveyor': 'quantity_surveyor_fee',
            'Finance costs on Land (LTV)': 'land_ltv_percent',
            'Finance costs on Land (Interest Rate)': 'land_interest_rate_percent',
            'Finance costs on Land (Entry)': 'land_entry_fee_percent',
            'Finance costs on Land (Exit)': 'land_exit_fee_percent',
            'Finance costs on Development (LTV)': 'development_ltv_percent',
            'Finance costs on Development (Interest Rate)': 'development_interest_rate_percent',
            'Finance costs on Development (Entry)': 'development_entry_fee_percent',
            'Finance costs on Development (Exit)': 'development_exit_fee_percent',
            'Lenders\' Valuation': 'lenders_valuation_fee',
            'Lenders\' Legal Costs': 'lenders_legal_costs',
            'Lenders\' Quantity Surveyor - Initial': 'lenders_qs_initial_fee',
            'Lenders\' Quantity Surveyor - Ongoing': 'lenders_qs_ongoing_fee',
            'Marketing Costs': 'marketing_costs',
            'Agent Fee': 'agent_fee_percent',
            'Legal Fees': 'legal_fees',
            'Lenders\' Criteria - Loan to Cost (LTC)': 'ltc_criteria_percent',
            'Lenders\' Criteria - Loan to GDV (LTGDV)': 'ltgdv_criteria_percent',
            'Post Development - Service Charges': 'service_charges_percent',
            'Post Development - Interest on term loan (LTV)': 'term_loan_ltv_percent',
            'Post Development - Interest on term loan (Interest rate)': 'term_loan_interest_rate_percent',
            'Margin / Yield': 'target_margin_yield',
            'Holding Period': 'holding_period',
            'Exit / Strategy': 'exit_strategy'
        }
        
        standardized = {}
        for category, value in parsed_assumptions.items():
            standard_field = field_mapping.get(category, category.lower().replace(' ', '_').replace('/', '_'))
            standardized[standard_field] = value
        
        return standardized
    
    def show_assumptions_summary(self, deal_type: str = None):
        """Show summary of assumptions for a deal type or all deal types"""
        if deal_type:
            if deal_type not in self.deal_types:
                print(f"❌ Deal type not found: {deal_type}")
                return
            
            print(f"\n📊 ASSUMPTIONS FOR: {deal_type}")
            print("=" * 80)
            
            assumptions = self.get_parsed_assumptions_for_deal_type(deal_type)
            
            for category, value in assumptions.items():
                print(f"📋 {category}: {value}")
        
        else:
            print(f"\n📊 ASSUMPTIONS SUMMARY")
            print("=" * 80)
            print(f"📁 CSV File: {self.csv_path}")
            print(f"🏠 Deal Types: {len(self.deal_types)}")
            print(f"📋 Assumption Categories: {len(self.assumption_categories)}")
            
            print(f"\n🏠 Available Deal Types:")
            for i, dt in enumerate(self.deal_types, 1):
                non_empty_assumptions = len(self.get_all_assumptions_for_deal_type(dt))
                print(f"   {i}. {dt} ({non_empty_assumptions} assumptions)")

def test_assumptions_loader():
    """Test function for the assumptions loader"""
    print("🧪 Testing Assumptions Loader")
    print("=" * 50)
    
    # Initialize loader
    loader = AssumptionsLoader()
    
    if not loader.assumptions_data is not None:
        print("❌ Failed to load assumptions")
        return
    
    # Show general summary
    loader.show_assumptions_summary()
    
    # Test specific deal type
    test_deal_type = "Residential – New Build"
    print(f"\n🧪 Testing assumptions for: {test_deal_type}")
    
    # Get raw assumptions
    raw_assumptions = loader.get_all_assumptions_for_deal_type(test_deal_type)
    print(f"📋 Raw assumptions count: {len(raw_assumptions)}")
    
    # Get parsed assumptions
    parsed_assumptions = loader.get_parsed_assumptions_for_deal_type(test_deal_type)
    print(f"🔧 Parsed assumptions count: {len(parsed_assumptions)}")
    
    # Get standardized assumptions
    standardized_assumptions = loader.get_standardized_assumptions(test_deal_type)
    print(f"⚙️ Standardized assumptions count: {len(standardized_assumptions)}")
    
    # Show sample values
    print(f"\n📋 Sample Assumptions:")
    sample_categories = ['Duration - Build phase', 'Build costs', 'Margin / Yield']
    
    for category in sample_categories:
        raw_value = loader.get_assumption_value(test_deal_type, category)
        parsed_value = loader.parse_assumption_value(raw_value, category)
        print(f"   {category}:")
        print(f"     Raw: {raw_value}")
        print(f"     Parsed: {parsed_value}")
    
    print(f"\n✅ Assumptions loader test completed!")

if __name__ == "__main__":
    test_assumptions_loader()