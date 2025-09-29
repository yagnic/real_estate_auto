#!/usr/bin/env python3
"""
Enhanced deal type classification module using GPT-4 with Pydantic models and assumptions
"""

import json
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator
from openai import OpenAI
from config import OPENAI_API_KEY, DEAL_TYPES, GPT_MAX_CONTENT_LENGTH, GPT_MAX_TOKENS
from assumptions import AssumptionsLoader


class AccommodationType(BaseModel):
    """Model for accommodation type details"""
    type: str = Field(..., description="Type of accommodation (studio, 1-bed, 2-bed, etc.)")
    units: Optional[int] = Field(None, description="Number of units of this type")
    area_m2: Optional[float] = Field(None, description="Area per unit in square meters")
    area_sqft: Optional[float] = Field(None, description="Area per unit in square feet")
    price_per_unit: Optional[float] = Field(None, description="Sale price per unit")
    rental_value: Optional[float] = Field(None, description="Rental value per unit")
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    price_per_sqm: Optional[float] = Field(None, description="Price per square meter")
    affordable_housing: Optional[bool] = Field(None, description="Whether this is affordable housing")
    
    @validator('price_per_unit', 'rental_value', 'price_per_sqft', 'price_per_sqm', 'area_m2', 'area_sqft', pre=True)
    def clean_numeric_fields(cls, v):
        """Clean numeric fields by removing currency symbols and formatting"""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.replace('£', '').replace('$', '').replace('€', '')
            cleaned = cleaned.replace('GBP', '').replace('USD', '').replace('EUR', '')
            cleaned = cleaned.replace(',', '').strip()
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return float(v) if v is not None else None


class Floor(BaseModel):
    """Model for floor details"""
    floor_type: str = Field(..., description="Type of floor (ground, first, second, etc.)")
    accommodation_types: List[AccommodationType] = Field(default_factory=list, description="List of accommodation types on this floor")
    
    @validator('floor_type')
    def normalize_floor_type(cls, v):
        """Normalize floor type to standard format"""
        if v:
            return v.lower().strip()
        return v


class CostsAndRates(BaseModel):
    """Model for costs and rates"""
    construction_cost_per_sqm: Optional[float] = Field(None, description="Construction cost per square meter")
    construction_cost_per_sqft: Optional[float] = Field(None, description="Construction cost per square foot")
    total_construction_cost: Optional[float] = Field(None, description="Total construction cost")
    professional_fees_percentage: Optional[float] = Field(None, description="Professional fees as percentage")
    professional_fees_fixed: Optional[float] = Field(None, description="Fixed professional fees amount")
    s106_costs: Optional[float] = Field(None, description="Section 106 costs")
    cil_costs: Optional[float] = Field(None, description="Community Infrastructure Levy costs")
    planning_costs: Optional[float] = Field(None, description="Planning application costs")
    contingency_percentage: Optional[float] = Field(None, description="Contingency percentage")
    agent_fees_percentage: Optional[float] = Field(None, description="Agent fees percentage")
    legal_costs: Optional[float] = Field(None, description="Legal costs")
    marketing_costs: Optional[float] = Field(None, description="Marketing costs")
    
    @validator('*', pre=True)
    def clean_numeric_fields(cls, v):
        """Clean numeric fields"""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.replace('£', '').replace('$', '').replace('€', '')
            cleaned = cleaned.replace('GBP', '').replace('USD', '').replace('EUR', '')
            cleaned = cleaned.replace('%', '').replace(',', '').strip()
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return float(v) if v is not None else None


class Timeline(BaseModel):
    """Model for project timeline"""
    total_development_duration_months: Optional[int] = Field(None, description="Total development duration in months")
    construction_period_months: Optional[int] = Field(None, description="Construction period in months")
    planning_timeframe_months: Optional[int] = Field(None, description="Planning timeframe in months")
    sales_period_months: Optional[int] = Field(None, description="Sales/letting period in months")
    
    @validator('*', pre=True)
    def clean_numeric_fields(cls, v):
        """Clean numeric fields"""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.replace('months', '').replace('month', '').replace('mths', '').strip()
            try:
                return int(cleaned) if cleaned else None
            except ValueError:
                return None
        return int(v) if v is not None else None


class FundingDetails(BaseModel):
    """Model for funding details"""
    ltc_ratio: Optional[float] = Field(None, description="Loan-to-cost ratio as percentage")
    ltgdv_ratio: Optional[float] = Field(None, description="Loan-to-GDV ratio as percentage")
    interest_rate: Optional[float] = Field(None, description="Interest rate as percentage")
    deposit_required: Optional[float] = Field(None, description="Deposit/equity required")
    total_loan_amount: Optional[float] = Field(None, description="Total loan amount")
    arrangement_fees: Optional[float] = Field(None, description="Arrangement fees")
    
    @validator('*', pre=True)
    def clean_numeric_fields(cls, v):
        """Clean numeric fields"""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.replace('£', '').replace('$', '').replace('€', '')
            cleaned = cleaned.replace('GBP', '').replace('USD', '').replace('EUR', '')
            cleaned = cleaned.replace('%', '').replace(',', '').strip()
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return float(v) if v is not None else None


class PropertyDetails(BaseModel):
    """Model for comprehensive property details"""
    # Basic property info
    site_address: Optional[str] = Field(None, description="Site address")
    asking_price: Optional[float] = Field(None, description="Asking price")
    reduction_to_achieve_target_profit_percentage_gdv: Optional[float] = Field(None, description = "Reduction to achieve target profit % on GDV")
    property_type: Optional[str] = Field(None, description="Property/development type")
    planning_status: Optional[str] = Field(None, description="Planning status")
    development_name: Optional[str] = Field(None, description="Development project name")
    
    # Building specifications
    floors: List[Floor] = Field(default_factory=list, description="List of floors in the property")
    total_units: Optional[int] = Field(None, description="Total number of units")
    total_area_m2: Optional[float] = Field(None, description="Total area in square meters")
    total_area_sqft: Optional[float] = Field(None, description="Total area in square feet")
    number_of_floors: Optional[int] = Field(None, description="Number of floors")
    construction_type: Optional[str] = Field(None, description="Construction type")
    
    # Market values
    gdv: Optional[float] = Field(None, description="Gross Development Value")
    average_price_per_sqft: Optional[float] = Field(None, description="Average price per square foot")
    average_price_per_sqm: Optional[float] = Field(None, description="Average price per square meter")
    market_comparables: Optional[str] = Field(None, description="Market comparables information")
    
    # Costs and financial details
    costs_and_rates: Optional[CostsAndRates] = Field(None, description="Costs and rates")
    timeline: Optional[Timeline] = Field(None, description="Project timeline")
    funding_details: Optional[FundingDetails] = Field(None, description="Funding details")
    
    # Additional considerations
    special_considerations: Optional[str] = Field(None, description="Special considerations or constraints")
    missing_information: Optional[List[str]] = Field(None, description="List of missing critical information")
    
    @validator('asking_price', 'reduction_to_achieve_target_profit_percentage_gdv', 'gdv', 'total_area_m2', 'total_area_sqft', 'average_price_per_sqft', 'average_price_per_sqm', pre=True)
    def clean_numeric_fields(cls, v):
        """Clean numeric fields"""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.replace('£', '').replace('$', '').replace('€', '')
            cleaned = cleaned.replace('GBP', '').replace('USD', '').replace('EUR', '')
            cleaned = cleaned.replace(',', '').strip()
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return float(v) if v is not None else None


class DealClassification(BaseModel):
    """Model for complete deal classification result"""
    deal_type: str = Field(..., description="Classified deal type")
    confidence: int = Field(..., ge=0, le=100, description="Confidence level from 0-100")
    reasoning: str = Field(..., description="Explanation of the classification")
    key_indicators: List[str] = Field(default_factory=list, description="Key words/phrases that led to classification")
    property_details: PropertyDetails = Field(default_factory=PropertyDetails, description="Comprehensive property information")
    applied_assumptions: Optional[Dict[str, Any]] = Field(None, description="Deal-type specific assumptions applied")
    
    @validator('deal_type')
    def validate_deal_type(cls, v):
        """Ensure deal type is from valid list or Unknown"""
        if v not in DEAL_TYPES and v != "Unknown":
            return "Unknown"
        return v


class DealClassifier:
    def __init__(self, assumptions_csv_path: str = "Assumptions.csv"):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.assumptions_loader = AssumptionsLoader(assumptions_csv_path)
    
    def get_assumptions_for_deal_type(self, deal_type: str) -> Dict[str, Any]:
        """Get standardized assumptions for a specific deal type"""
        try:
            assumptions = self.assumptions_loader.get_standardized_assumptions(deal_type)
            return assumptions
        except Exception as e:
            print(f"Error loading assumptions for {deal_type}: {e}")
            return {}
    
    def format_assumptions_for_prompt(self, deal_type: str) -> str:
        """Format assumptions for inclusion in GPT prompt"""
        assumptions = self.get_assumptions_for_deal_type(deal_type)
        
        if not assumptions:
            return "No specific assumptions available for this deal type."
        
        formatted = f"**ASSUMPTIONS FOR {deal_type.upper()}:**\n"
        
        # Group assumptions by category
        categories = {
            "Duration": ["duration_land_months", "duration_build_months", "duration_selling_months"],
            "Fees & Costs": ["sourcing_fee_percent", "building_insurance_percent", "legal_costs_percent", 
                           "architect_fee_percent", "town_planner_fee_percent", "structural_engineer_fee_percent"],
            "Construction": ["build_costs_per_sqft", "build_contingency_percent"],
            "Finance": ["land_ltv_percent", "land_interest_rate_percent", "development_ltv_percent", 
                       "development_interest_rate_percent", "ltc_criteria_percent", "ltgdv_criteria_percent"],
            "Marketing & Sales": ["marketing_costs", "agent_fee_percent"],
            "Target Returns": ["target_margin_yield", "exit_strategy"]
        }
        
        for category, fields in categories.items():
            category_assumptions = {k: v for k, v in assumptions.items() if k in fields}
            if category_assumptions:
                formatted += f"\n{category}:\n"
                for field, value in category_assumptions.items():
                    # Convert field name to readable format
                    readable_name = field.replace('_', ' ').title()
                    formatted += f"- {readable_name}: {value}\n"
        
        # Add any remaining assumptions
        used_fields = [field for fields in categories.values() for field in fields]
        remaining = {k: v for k, v in assumptions.items() if k not in used_fields}
        if remaining:
            formatted += f"\nOther Assumptions:\n"
            for field, value in remaining.items():
                readable_name = field.replace('_', ' ').title()
                formatted += f"- {readable_name}: {value}\n"
        
        return formatted
    
    def classify_deal_type(self, content: str) -> DealClassification:
        """Classify deal type and extract comprehensive property information using GPT-4"""
        print("Classifying deal type and extracting comprehensive property details with GPT-4...")
        
        try:
            deal_types_list = "\n".join([f"- {dt}" for dt in DEAL_TYPES])
            
            # First, do a preliminary classification to get the deal type
            preliminary_prompt = f"""
            Analyze this real estate content and classify it into one of these exact deal types:
            {deal_types_list}
            
            Return ONLY the deal type name (or "Unknown" if unclear).
            
            Content: {content[:1000]}
            """
            
            prelim_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a real estate expert. Return only the deal type classification."},
                    {"role": "user", "content": preliminary_prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            preliminary_deal_type = prelim_response.choices[0].message.content.strip()
            print(f"Preliminary classification: {preliminary_deal_type}")
            
            # Get assumptions for this deal type
            assumptions_text = self.format_assumptions_for_prompt(preliminary_deal_type)
            applied_assumptions = self.get_assumptions_for_deal_type(preliminary_deal_type)
            
            # Comprehensive example JSON structure
            example_json = """{
    "deal_type": "New Build Development",
    "confidence": 95,
    "reasoning": "Property involves construction of new residential units with detailed specifications",
    "key_indicators": ["new build", "studio flat", "1 bed flat", "2 bed flat", "construction"],
    "property_details": {
        "site_address": "Hambleden House, Waterloo Court, Andover, SP10 1LQ",
        "asking_price": 3370034,
        "reduction_to_achieve_target_profit_percentage_gdv" : 300000
        "property_type": "Residential Development",
        "planning_status": "Planning Approved",
        "development_name": "Hambleden House Development",
        "floors": [
            {
                "floor_type": "ground",
                "accommodation_types": [
                    {
                        "type": "studio",
                        "units": 12,
                        "area_sqft": 400,
                        "price_per_unit": 145000,
                        "price_per_sqft": 362.5,
                        "affordable_housing": false
                    },
                    {
                        "type": "1-bed",
                        "units": 62,
                        "area_sqft": 402,
                        "price_per_unit": 150000,
                        "price_per_sqft": 373.1,
                        "affordable_housing": false
                    }
                ]
            },
            {
                "floor_type": "first",
                "accommodation_types": [
                    {
                        "type": "2-bed",
                        "units": 10,
                        "area_m2": 52.0,
                        "price_per_unit": 170000,
                        "affordable_housing": true
                    }
                ]
            }
        ],
        "total_units": 84,
        "number_of_floors": 2,
        "construction_type": "New Build",
        "gdv": 3370034,
        "costs_and_rates": {
            "construction_cost_per_sqm": 1200,
            "professional_fees_percentage": 2.1,
            "contingency_percentage": 10.0,
            "agent_fees_percentage": 2.4,
            "legal_costs": 33700,
            "marketing_costs": 5000
        },
        "timeline": {
            "total_development_duration_months": 18,
            "construction_period_months": 12,
            "planning_timeframe_months": 6
        },
        "funding_details": {
            "ltc_ratio": 85.0,
            "ltgdv_ratio": 70.0,
            "interest_rate": 9.95
        },
        "missing_information": ["Rental values", "Detailed S106 costs"]
    }
}"""

            comprehensive_prompt = f"""
            Analyze the following real estate email/text and extract ALL relevant property development data.

            DEAL TYPE CLASSIFICATION:
            Classify into one of these exact deal types: {deal_types_list}

            {assumptions_text}

            Use these assumptions as defaults when specific information is not provided in the email content. 
            If the email contains different values, use those instead of the assumptions.

            EXTRACTION REQUIREMENTS:
            Extract and organize ALL information into these categories:

            **PROPERTY BASICS:** Site address, asking price, property type, planning status
            **DEVELOPMENT SPECIFICATION:** Total units, unit mix, floor areas, building specs, affordable housing
            **MARKET VALUES:** Sale prices per unit, rental values, comparables, price per sqft/sqm
            **COSTS & RATES:** Construction costs, professional fees, statutory costs, contingencies
            **TIMELINE:** Development duration, construction period, planning timeframes
            **FUNDING DETAILS:** LTC/LTGDV ratios, interest rates, deposit requirements
            **OTHER KEY DATA:** Agent fees, legal costs, marketing costs, special considerations

            EXAMPLE OUTPUT:
            {example_json}

            CRITICAL INSTRUCTIONS:
            - Extract EVERY piece of data mentioned in the email
            - Apply deal-type assumptions for missing values
            - Include all floors, unit types, areas, and prices
            - Extract percentages, rates, costs, and timelines
            - Note missing critical information in the missing_information array
            - Use null only for data not mentioned and not covered by assumptions
            - Prioritize email content over assumptions when both are available

            Email/Text Content:
            {content[:GPT_MAX_CONTENT_LENGTH]}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert real estate development analyst. Extract ALL financial, technical, and development data from the provided content using deal-type specific assumptions as defaults. Return ONLY valid JSON with comprehensive property development information."
                    },
                    {"role": "user", "content": comprehensive_prompt}
                ],
                temperature=0.1,
                max_tokens=GPT_MAX_TOKENS * 3
            )
            
            raw_response = response.choices[0].message.content
            print(f"Debug: GPT raw response length: {len(raw_response) if raw_response else 0}")
            
            if not raw_response or not raw_response.strip():
                print("Error: Empty response from GPT")
                return self._get_error_response("Empty GPT response")
            
            # Clean the response
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response.replace('```', '').strip()
            
            print(f"Debug: Cleaned response preview: {cleaned_response[:300]}...")
            
            classification_data = json.loads(cleaned_response)
            
            # Add the applied assumptions to the result
            classification_data['applied_assumptions'] = applied_assumptions
            
            classification = DealClassification(**classification_data)
            
            print(f"Classification: {classification.deal_type} (confidence: {classification.confidence}%)")
            if classification.property_details.total_units:
                print(f"Property details: {classification.property_details.total_units} total units extracted")
            if classification.applied_assumptions:
                print(f"Applied {len(classification.applied_assumptions)} deal-type assumptions")
            
            return classification
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse GPT JSON response: {e}")
            print(f"Raw response was: {raw_response[:500] if 'raw_response' in locals() else 'No response'}")
            return self._get_error_response("JSON parsing failed")
        except Exception as e:
            print(f"GPT classification error: {e}")
            print(f"Raw response was: {raw_response[:500] if 'raw_response' in locals() else 'No response'}")
            return self._get_error_response(f"Error: {e}")
    
    def _get_error_response(self, error_msg: str) -> DealClassification:
        """Return standardized error response using Pydantic model"""
        return DealClassification(
            deal_type="Unknown",
            confidence=0,
            reasoning=error_msg,
            key_indicators=[],
            property_details=PropertyDetails(),
            applied_assumptions={}
        )