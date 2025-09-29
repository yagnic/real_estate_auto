#!/usr/bin/env python3
"""
Configuration module for email fetcher and classifier
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Authentication
CLIENT_ID = "650e7769-5178-4815-8f79-7d7a775d1251"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = [
    'Mail.Read',
    'Mail.Send'
]

# OCR API Configuration
RAPIDAPI_OCR_URL = "https://ocr43.p.rapidapi.com/v1/results"
RAPIDAPI_HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_OCR_KEY"),
    "x-rapidapi-host": "ocr43.p.rapidapi.com"
}

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Deal Type Categories
DEAL_TYPES = [
    "Residential – New Build",
    "Residential – Conversion / Change of Use", 
    "Residential – Extension / Airspace",
    "Mixed-Use Development",
    "Pure Residential Investment (BTL / PRS)",
    "HMO / Co-Living Investment",
    "Commercial Investment – Long Income",
    "Commercial Value-Add / Asset Mgmt",
    "Planning Gain / Land Promotion",
    "Forward Funding / Forward Purchase",
    "Specialist / Operational Assets"
]

# Target email configuration
TARGET_EMAIL = "deals.mdngroup@outlook.com"
DEFAULT_EMAIL_LIMIT = 10

# File processing configuration
PROCESSABLE_CONTENT_TYPES = ['pdf', 'image', 'text', 'doc']
PROCESSABLE_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.txt', '.doc', '.docx']

# Image-specific types for OCR
IMAGE_CONTENT_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp']
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']

# API limits
GPT_MAX_CONTENT_LENGTH = 4000
GPT_MAX_TOKENS = 500