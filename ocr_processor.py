#!/usr/bin/env python3
"""
OCR processing module for extracting text from attachments using OCR43 API
"""

import requests
import base64
import json
from typing import Dict
from config import RAPIDAPI_OCR_URL, RAPIDAPI_HEADERS


class OCRProcessor:
    @staticmethod
    def extract_text_from_attachment(attachment_data: Dict) -> str:
        """Extract text from attachment using OCR43 API from RapidAPI"""
        if not attachment_data.get('contentBytes'):
            return ""
        
        try:
            attachment_name = attachment_data.get('name', 'unknown')
            content_type = attachment_data.get('contentType', '')
            is_inline = attachment_data.get('isInline', False)
            
            print(f"Processing {'inline image' if is_inline else 'attachment'}: {attachment_name}")
            print(f"Content type: {content_type}")
            
            # Decode the base64 content
            try:
                file_content = base64.b64decode(attachment_data['contentBytes'])
                print(f"Decoded {len(file_content)} bytes for OCR processing")
            except Exception as e:
                print(f"Failed to decode base64 content: {e}")
                return ""
            
            # Check if we have valid headers
            if not RAPIDAPI_HEADERS.get("x-rapidapi-key"):
                print("Error: RAPID_OCR_KEY not found in environment variables")
                return ""
            
            # OCR43 API expects the image in a specific format
            # Try sending as base64 string first (common for OCR43)
            try:
                # Method 1: Send as base64 encoded string
                base64_string = base64.b64encode(file_content).decode('utf-8')
                
                data = {
                    'image': base64_string
                }
                
                print("Sending to OCR43 API (base64 format)...")
                print(f"API URL: {RAPIDAPI_OCR_URL}")
                
                response = requests.post(
                    RAPIDAPI_OCR_URL,
                    headers=RAPIDAPI_HEADERS,
                    data=data,
                    timeout=60
                )
                
                print(f"OCR API response status: {response.status_code}")
                
                # If base64 method fails, try file upload method
                if response.status_code == 422:
                    print("Base64 method failed, trying file upload...")
                    
                    # Method 2: File upload
                    files = {
                        'image': (
                            attachment_name,
                            file_content,
                            content_type or 'image/png'
                        )
                    }
                    
                    response = requests.post(
                        RAPIDAPI_OCR_URL,
                        headers=RAPIDAPI_HEADERS,
                        files=files,
                        timeout=60
                    )
                    
                    print(f"OCR API response status (file method): {response.status_code}")
                
                # If still failing, try URL-based approach (if supported)
                if response.status_code == 422:
                    print("File upload also failed, trying JSON format...")
                    
                    # Method 3: JSON with base64
                    json_data = {
                        'image': f"data:{content_type or 'image/png'};base64,{base64_string}"
                    }
                    
                    headers_json = RAPIDAPI_HEADERS.copy()
                    headers_json['Content-Type'] = 'application/json'
                    
                    response = requests.post(
                        RAPIDAPI_OCR_URL,
                        headers=headers_json,
                        json=json_data,
                        timeout=60
                    )
                    
                    print(f"OCR API response status (JSON method): {response.status_code}")
                
            except Exception as e:
                print(f"Error preparing OCR request: {e}")
                return ""
            
            print(f"OCR API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    ocr_result = response.json()
                    print(f"OCR result keys: {list(ocr_result.keys()) if isinstance(ocr_result, dict) else 'Not a dict'}")
                    
                    # Handle OCR43 API response format
                    extracted_text = ""
                    
                    if isinstance(ocr_result, dict):
                        # Try different possible response structures for OCR43
                        if 'results' in ocr_result:
                            results = ocr_result['results']
                            if isinstance(results, list) and results:
                                extracted_text = results[0].get('text', '')
                            elif isinstance(results, dict):
                                extracted_text = results.get('text', '')
                        elif 'text' in ocr_result:
                            extracted_text = ocr_result['text']
                        elif 'data' in ocr_result:
                            data = ocr_result['data']
                            if isinstance(data, dict):
                                extracted_text = data.get('text', '')
                            elif isinstance(data, str):
                                extracted_text = data
                        elif 'content' in ocr_result:
                            extracted_text = ocr_result['content']
                        else:
                            # If we can't find text in expected fields, try to find any text field
                            for key, value in ocr_result.items():
                                if isinstance(value, str) and len(value) > 10:  # Likely to be extracted text
                                    extracted_text = value
                                    break
                    
                    print(f"OCR extracted {len(extracted_text)} characters")
                    if extracted_text:
                        print(f"Preview: {extracted_text[:100]}...")
                        return extracted_text
                    else:
                        print("No text content found in OCR response")
                        print(f"Full response: {json.dumps(ocr_result, indent=2)}")
                        return ""
                    
                except json.JSONDecodeError as e:
                    print(f"Failed to parse OCR response as JSON: {e}")
                    print(f"Raw response: {response.text[:500]}")
                    return ""
            elif response.status_code == 401:
                print("OCR API Error: Unauthorized - Check your RAPID_OCR_KEY")
                return ""
            elif response.status_code == 403:
                print("OCR API Error: Forbidden - Check API permissions or quota")
                return ""
            elif response.status_code == 429:
                print("OCR API Error: Rate limit exceeded")
                return ""
            else:
                print(f"OCR failed with status {response.status_code}")
                print(f"Error response: {response.text[:500]}")
                return ""
                
        except requests.exceptions.Timeout:
            print("OCR request timed out")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"OCR request error: {e}")
            return ""
        except Exception as e:
            print(f"OCR processing error: {e}")
            return ""