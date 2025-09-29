#!/usr/bin/env python3
"""
Content processing module for combining email content and attachments with BeautifulSoup
Enhanced with link processing for images and PDFs
"""

import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from email_fetcher import EmailFetcher
from ocr_processor import OCRProcessor
from config import PROCESSABLE_CONTENT_TYPES, PROCESSABLE_EXTENSIONS


class ContentProcessor:
    def __init__(self, email_fetcher: EmailFetcher):
        self.email_fetcher = email_fetcher
        self.ocr_processor = OCRProcessor()
        
        # Create directory for saving HTML files
        self.html_output_dir = "email_html_files"
        os.makedirs(self.html_output_dir, exist_ok=True)
        
        # Image and PDF extensions to look for in links
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        self.pdf_extensions = {'.pdf'}
        self.processable_link_extensions = self.image_extensions | self.pdf_extensions
        
        # Content types that indicate processable resources
        self.processable_content_types = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
            'image/bmp', 'image/tiff', 'image/webp',
            'application/pdf'
        }
    
    def concatenate_email_content(self, email: Dict) -> str:
        """Concatenate all email content (subject, body, attachment data, and linked resources)"""
        email_id = email.get('id', 'unknown')
        subject = email.get('subject', 'No Subject')
        
        print(f"Processing content for: {subject[:50]}...")
        
        content_parts = []
        
        # Add subject
        if subject:
            content_parts.append(f"SUBJECT: {subject}")
            print(f"Added subject: {len(subject)} characters")
        
        # Add body preview
        body_preview = email.get('bodyPreview', '')
        if body_preview:
            content_parts.append(f"BODY PREVIEW: {body_preview}")
            print(f"Added body preview: {len(body_preview)} characters")
        
        # Process email body with HTML extraction and link processing
        body_text, extracted_links = self._process_email_body(email, email_id)
        if body_text:
            content_parts.append(f"FULL BODY: {body_text}")
            print(f"Added processed body: {len(body_text)} characters")
        
        # Process links found in the body
        if extracted_links:
            print(f"Found {len(extracted_links)} processable links in email body")
            for i, link_data in enumerate(extracted_links):
                link_url = link_data['url']
                link_text = link_data.get('text', '')
                print(f"Processing link {i+1}: {link_url}")
                
                extracted_text = self._process_link_content(link_url)
                if extracted_text and extracted_text.strip():
                    link_type = self._get_link_type(link_url)
                    content_parts.append(f"LINKED_{link_type.upper()} ({link_text or link_url}): {extracted_text}")
                    print(f"  Extracted {len(extracted_text)} characters from link")
                else:
                    print(f"  No text extracted from link: {link_url}")
        
        # Debug: Show what we have so far
        print(f"Content parts so far: {len(content_parts)}")
        
        # Check for attachments using multiple methods
        has_attachments_flag = email.get('hasAttachments', False)
        print(f"Email hasAttachments flag: {has_attachments_flag}")
        
        # Method 1: Check if email has attachments flag
        if has_attachments_flag:
            print("Method 1: Using hasAttachments flag")
            attachments = self.email_fetcher.get_email_attachments(email_id)
            print(f"Found {len(attachments)} attachments via API call")
            
            for i, attachment in enumerate(attachments):
                attachment_name = attachment.get('name', f'attachment_{i}')
                content_type = attachment.get('contentType', 'unknown')
                is_inline = attachment.get('isInline', False)
                size = attachment.get('size', 0)
                
                print(f"Attachment {i+1}: {attachment_name}")
                print(f"  Content Type: {content_type}")
                print(f"  Is Inline: {is_inline}")
                print(f"  Size: {size} bytes")
                
                # Process all images and documents
                if self._should_process_attachment(attachment):
                    print(f"  Processing attachment: {attachment_name}")
                    extracted_text = self._process_attachment(email_id, attachment)
                    if extracted_text and extracted_text.strip():
                        attachment_type = "INLINE_IMAGE" if is_inline else "ATTACHMENT"
                        content_parts.append(f"{attachment_type} ({attachment_name}): {extracted_text}")
                        print(f"  Extracted {len(extracted_text)} characters")
                    else:
                        print(f"  No text extracted from {attachment_name}")
                else:
                    print(f"  Skipping {attachment_name} (not processable)")
        
        # Method 2: Also try the detailed attachment check
        print("Method 2: Using detailed attachment check")
        attachment_info = self.email_fetcher.check_all_attachments(email_id)
        print(f"Detailed check found: {attachment_info.get('attachment_count', 0)} attachments")
        
        # Combine all content
        combined_content = "\n\n".join(content_parts)
        print(f"Final combined content: {len(combined_content)} characters")
        
        return combined_content
    
    def _process_email_body(self, email: Dict, email_id: str) -> tuple[str, List[Dict]]:
        """Process email body with HTML saving, BeautifulSoup extraction, and link discovery"""
        body = email.get('body', {})
        if not isinstance(body, dict):
            if body:  # String body
                links = self._extract_links_from_text(str(body))
                return str(body), links
            return "", []
        
        body_content = body.get('content', '')
        body_type = body.get('contentType', 'text').lower()
        
        if not body_content:
            print("No body content found")
            return "", []
        
        # Save HTML to file for debugging/inspection
        if 'html' in body_type:
            html_filename = self._save_html_to_file(body_content, email_id, email.get('subject', 'No Subject'))
            print(f"HTML saved to: {html_filename}")
            
            # Extract text and links using BeautifulSoup
            extracted_text, links = self._extract_text_and_links_with_beautifulsoup(body_content)
            print(f"BeautifulSoup extraction: {len(body_content)} chars -> {len(extracted_text)} chars")
            print(f"Found {len(links)} processable links in HTML body")
            return extracted_text, links
        else:
            # Plain text body - look for URLs
            print(f"Plain text body: {len(body_content)} characters")
            links = self._extract_links_from_text(body_content)
            print(f"Found {len(links)} processable links in plain text body")
            return body_content, links
    
    def _extract_links_from_text(self, text: str) -> List[Dict]:
        """Extract processable links from plain text using regex"""
        # Regex pattern to find URLs
        url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+|[^\s<>"\']+\.[a-z]{2,}(?:/[^\s<>"\']*)??'
        
        links = []
        for match in re.finditer(url_pattern, text, re.IGNORECASE):
            url = match.group()
            
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    # Skip if it doesn't look like a complete URL
                    continue
            
            if self._is_processable_link(url):
                links.append({
                    'url': url,
                    'text': ''  # No link text available in plain text
                })
        
        return links
    
    def _extract_text_and_links_with_beautifulsoup(self, html_content: str) -> tuple[str, List[Dict]]:
        """Extract text and processable links from HTML using BeautifulSoup"""
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract processable links before cleaning
            links = self._extract_links_from_soup(soup)
            
            # Remove script and style elements
            for script in soup(["script", "style", "head", "title", "meta"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # If we got very little text, try more aggressive extraction
            if len(text) < 100:
                print("Basic extraction yielded little text, trying advanced methods...")
                
                # Try extracting from specific elements that might contain content
                content_selectors = [
                    'div[class*="content"]',
                    'div[class*="body"]',
                    'div[class*="message"]',
                    'div[class*="text"]',
                    'p',
                    'div',
                    'span',
                    'td'
                ]
                
                extracted_parts = []
                for selector in content_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        element_text = element.get_text(strip=True)
                        if element_text and len(element_text) > 10:  # Only meaningful text
                            extracted_parts.append(element_text)
                
                if extracted_parts:
                    text = ' '.join(extracted_parts)
                    print(f"Advanced extraction found: {len(text)} characters")
            
            # Final cleanup
            text = re.sub(r'\s+', ' ', text).strip()
            
            print(f"Final extracted text length: {len(text)} characters")
            if text:
                print(f"Text preview: {text[:200]}...")
            
            return text, links
            
        except Exception as e:
            print(f"BeautifulSoup extraction failed: {e}")
            # Fallback to simple regex
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            links = self._extract_links_from_text(html_content)
            return text, links
    
    def _extract_links_from_soup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract processable links from BeautifulSoup object"""
        links = []
        processed_urls = set()  # Avoid duplicates
        
        # Find all anchor tags with href attributes
        for link_tag in soup.find_all('a', href=True):
            url = link_tag.get('href')
            link_text = link_tag.get_text(strip=True)
            
            # Skip if URL is empty or already processed
            if not url or url in processed_urls:
                continue
            
            # Handle relative URLs (this is basic - you might need more sophisticated handling)
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/') or not url.startswith(('http://', 'https://')):
                # Skip relative URLs for now unless you have a base URL
                continue
            
            if self._is_processable_link(url):
                links.append({
                    'url': url,
                    'text': link_text
                })
                processed_urls.add(url)
        
        # Also look for img tags with src pointing to external images
        for img_tag in soup.find_all('img', src=True):
            url = img_tag.get('src')
            alt_text = img_tag.get('alt', '')
            
            if not url or url in processed_urls:
                continue
            
            # Handle relative URLs
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/') or not url.startswith(('http://', 'https://')):
                continue
            
            if self._is_processable_link(url):
                links.append({
                    'url': url,
                    'text': f"Image: {alt_text}" if alt_text else "Image"
                })
                processed_urls.add(url)
        
        return links
    
    def _is_processable_link(self, url: str) -> bool:
        """Check if a URL points to a processable resource (image or PDF)"""
        try:
            parsed = urlparse(url.lower())
            path = parsed.path
            
            # First check file extension (fast path)
            for ext in self.processable_link_extensions:
                if path.endswith(ext):
                    print(f"Link identified by extension: {url}")
                    return True
            
            # If no clear extension, make a HEAD request to check content type
            print(f"No file extension found, checking content type for: {url}")
            return self._check_link_content_type(url)
            
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            return False
    
    def _check_link_content_type(self, url: str) -> bool:
        """Make a HEAD request to check if URL serves processable content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Make HEAD request (faster than GET since we only need headers)
            print(f"Making HEAD request to check content type: {url}")
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            
            # Get content type from response headers
            content_type = response.headers.get('content-type', '').lower()
            print(f"Content type from HEAD request: {content_type}")
            
            # Check if content type indicates processable resource
            is_processable = any(ct in content_type for ct in self.processable_content_types)
            
            if is_processable:
                print(f"✓ Link serves processable content: {url} ({content_type})")
            else:
                print(f"✗ Link does not serve processable content: {url} ({content_type})")
            
            return is_processable
            
        except requests.RequestException as e:
            print(f"HEAD request failed for {url}: {e}")
            # If HEAD request fails, we could try a more permissive approach
            # or fall back to checking if URL looks like it might serve files
            return self._fallback_link_check(url)
        except Exception as e:
            print(f"Error checking content type for {url}: {e}")
            return False
    
    def _fallback_link_check(self, url: str) -> bool:
        """Fallback method to guess if a URL might serve processable content"""
        url_lower = url.lower()
        
        # Look for common patterns that suggest file serving
        file_serving_patterns = [
            '/download',
            '/file',
            '/attachment',
            '/document',
            '/pdf',
            '/image',
            '/media',
            'download=',
            'attachment=',
            'file=',
            'document=',
            '.do',  # Common in enterprise systems
            '/api/',  # API endpoints often serve files
        ]
        
        # Check if URL contains file-serving patterns
        has_pattern = any(pattern in url_lower for pattern in file_serving_patterns)
        
        if has_pattern:
            print(f"URL matches file-serving pattern, will attempt processing: {url}")
            return True
        
        print(f"URL doesn't match known patterns, skipping: {url}")
        return False
    
    def _get_link_type(self, url: str) -> str:
        """Determine the type of linked resource"""
        url_lower = url.lower()
        if any(url_lower.endswith(ext) for ext in self.image_extensions):
            return "image"
        elif any(url_lower.endswith(ext) for ext in self.pdf_extensions):
            return "pdf"
        else:
            return "document"
    
    def _process_link_content(self, url: str) -> str:
        """Download and extract text from a linked resource"""
        try:
            print(f"Downloading content from: {url}")
            
            # Set headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Download the content with GET request
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type from actual response
            content_type = response.headers.get('content-type', '').lower()
            print(f"Actual content type from GET request: {content_type}")
            
            # Double-check that it's actually processable content
            if not any(ct in content_type for ct in self.processable_content_types):
                print(f"Content type {content_type} is not processable, skipping")
                return ""
            
            # Get file size for logging
            content_length = response.headers.get('content-length')
            if content_length:
                print(f"Content size: {int(content_length):,} bytes")
            
            # Read the content
            content_bytes = response.content
            print(f"Downloaded {len(content_bytes):,} bytes")
            
            # Validate the downloaded content
            if not content_bytes:
                print("Downloaded content is empty")
                return ""
            
            # Check if it's actually a PDF by looking at magic bytes
            if content_type and 'pdf' in content_type:
                if not content_bytes.startswith(b'%PDF'):
                    print("WARNING: Content-Type says PDF but file doesn't start with PDF magic bytes")
                    print(f"First 20 bytes: {content_bytes[:20]}")
                else:
                    print("✓ Valid PDF file detected (starts with %PDF)")
            
            # Determine filename from URL or content-disposition header
            filename = self._get_filename_from_response(url, response)
            
            # Create a temporary attachment-like object for OCR processing
            fake_attachment = {
                'name': filename,
                'contentType': content_type,
                'contentBytes': content_bytes,
                'size': len(content_bytes)
            }
            
            print(f"Processing downloaded content as: {filename} ({content_type})")
            print(f"Calling OCR processor with {len(content_bytes)} bytes of data...")
            
            # Use existing OCR processor with enhanced error handling
            try:
                extracted_text = self.ocr_processor.extract_text_from_attachment(fake_attachment)
                
                if extracted_text and extracted_text.strip():
                    print(f"✓ OCR SUCCESS: Extracted {len(extracted_text)} characters")
                    print(f"Text preview: {extracted_text[:200]}...")
                    return extracted_text
                else:
                    print("✗ OCR returned empty text")
                    
                    # Try alternative PDF processing if it's a PDF
                    if 'pdf' in content_type.lower():
                        print("Attempting alternative PDF text extraction...")
                        return self._alternative_pdf_extraction(content_bytes, filename)
                    
                    return ""
                    
            except Exception as ocr_error:
                print(f"OCR processor failed: {ocr_error}")
                
                # Try alternative PDF processing if it's a PDF
                if 'pdf' in content_type.lower():
                    print("OCR failed, attempting alternative PDF text extraction...")
                    return self._alternative_pdf_extraction(content_bytes, filename)
                
                return ""
            
        except requests.RequestException as e:
            print(f"Failed to download {url}: {e}")
            return ""
        except Exception as e:
            print(f"Error processing link content {url}: {e}")
            return ""
    
    def _process_link_content(self, url: str) -> str:
        """Download and extract text from a linked resource"""
        try:
            print(f"Downloading content from: {url}")
            
            # Set headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Download the content with GET request
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type from actual response
            content_type = response.headers.get('content-type', '').lower()
            print(f"Actual content type from GET request: {content_type}")
            
            # Double-check that it's actually processable content
            if not any(ct in content_type for ct in self.processable_content_types):
                print(f"Content type {content_type} is not processable, skipping")
                return ""
            
            # Get file size for logging
            content_length = response.headers.get('content-length')
            if content_length:
                print(f"Content size: {int(content_length):,} bytes")
            
            # Read the content
            content_bytes = response.content
            print(f"Downloaded {len(content_bytes):,} bytes")
            
            # Validate the downloaded content
            if not content_bytes:
                print("Downloaded content is empty")
                return ""
            
            # Check if it's actually a PDF by looking at magic bytes
            if content_type and 'pdf' in content_type:
                if not content_bytes.startswith(b'%PDF'):
                    print("WARNING: Content-Type says PDF but file doesn't start with PDF magic bytes")
                    print(f"First 20 bytes: {content_bytes[:20]}")
                    # Still try to process it
                else:
                    print("✓ Valid PDF file detected (starts with %PDF)")
                
                # For PDFs, try text-based extraction FIRST (faster and more reliable)
                print("Attempting text-based PDF extraction before OCR...")
                text_from_pdf = self._extract_text_from_pdf(content_bytes)
                if text_from_pdf and len(text_from_pdf.strip()) > 50:  # Got meaningful text
                    print(f"✓ PDF TEXT EXTRACTION SUCCESS: {len(text_from_pdf)} characters")
                    print(f"Text preview: {text_from_pdf[:200]}...")
                    return text_from_pdf
                else:
                    print("PDF text extraction yielded little/no text, will try OCR...")
            
            # Determine filename from URL or content-disposition header
            filename = self._get_filename_from_response(url, response)
            
            # Create a temporary attachment-like object for OCR processing
            fake_attachment = {
                'name': filename,
                'contentType': content_type,
                'contentBytes': content_bytes,
                'size': len(content_bytes)
            }
            
            print(f"Processing downloaded content as: {filename} ({content_type})")
            print(f"Calling OCR processor with {len(content_bytes)} bytes of data...")
            
            # Use existing OCR processor with enhanced error handling
            try:
                extracted_text = self.ocr_processor.extract_text_from_attachment(fake_attachment)
                
                if extracted_text and extracted_text.strip():
                    print(f"✓ OCR SUCCESS: Extracted {len(extracted_text)} characters")
                    print(f"Text preview: {extracted_text[:200]}...")
                    return extracted_text
                else:
                    print("✗ OCR returned empty text")
                    
                    # For PDFs, this is a fallback (we already tried text extraction above)
                    if 'pdf' in content_type.lower():
                        print("OCR failed for PDF - saving for manual inspection")
                        self._save_problematic_pdf(content_bytes, filename)
                    
                    return ""
                    
            except Exception as ocr_error:
                print(f"OCR processor failed with error: {ocr_error}")
                
                # For PDFs, save for inspection
                if 'pdf' in content_type.lower():
                    print("OCR error for PDF - saving for manual inspection")
                    self._save_problematic_pdf(content_bytes, filename)
                
                return ""
            
        except requests.RequestException as e:
            print(f"Failed to download {url}: {e}")
            return ""
        except Exception as e:
            print(f"Error processing link content {url}: {e}")
            return ""
    
    def _extract_text_from_pdf(self, content_bytes: bytes) -> str:
        """Extract text from PDF using multiple methods"""
        extracted_text = ""
        
        # Try PyPDF2 first (fastest for text-based PDFs)
        try:
            import PyPDF2
            import io
            
            print("Trying PyPDF2 for PDF text extraction...")
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                print("PDF is encrypted/password protected - cannot extract text")
                return ""
            
            text_parts = []
            total_pages = len(pdf_reader.pages)
            print(f"PDF has {total_pages} pages")
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(page_text.strip())
                        print(f"  Page {page_num + 1}: {len(page_text)} characters")
                    else:
                        print(f"  Page {page_num + 1}: No text found")
                except Exception as e:
                    print(f"  Failed to extract from page {page_num + 1}: {e}")
            
            if text_parts:
                extracted_text = '\n\n'.join(text_parts)
                print(f"✓ PyPDF2 extracted {len(extracted_text)} characters from {len(text_parts)} pages")
                return extracted_text
            else:
                print("PyPDF2 found no extractable text (likely scanned PDF)")
                
        except ImportError:
            print("PyPDF2 not available - install with: pip install PyPDF2")
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
        
        # Try pdfplumber as fallback (better for complex layouts)
        try:
            import pdfplumber
            import io
            
            print("Trying pdfplumber for PDF text extraction...")
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                text_parts = []
                total_pages = len(pdf.pages)
                print(f"pdfplumber: PDF has {total_pages} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_parts.append(page_text.strip())
                            print(f"  Page {page_num + 1}: {len(page_text)} characters")
                        else:
                            print(f"  Page {page_num + 1}: No text found")
                    except Exception as e:
                        print(f"  Failed to extract from page {page_num + 1}: {e}")
                
                if text_parts:
                    extracted_text = '\n\n'.join(text_parts)
                    print(f"✓ pdfplumber extracted {len(extracted_text)} characters from {len(text_parts)} pages")
                    return extracted_text
                else:
                    print("pdfplumber found no extractable text (likely scanned PDF)")
                    
        except ImportError:
            print("pdfplumber not available - install with: pip install pdfplumber")
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
        
        # If we get here, no text could be extracted
        print("No text-based extraction possible - PDF likely contains only images/scans")
        return ""
    
    def _save_problematic_pdf(self, content_bytes: bytes, filename: str) -> None:
        """Save PDFs that failed text extraction for manual inspection"""
        try:
            # Create directory for problematic PDFs
            problem_dir = "problematic_pdfs"
            os.makedirs(problem_dir, exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
            save_filename = f"{timestamp}_{safe_filename}"
            save_path = os.path.join(problem_dir, save_filename)
            
            with open(save_path, 'wb') as f:
                f.write(content_bytes)
            
            print(f"📄 Saved problematic PDF: {save_path}")
            print(f"   Size: {len(content_bytes):,} bytes")
            print(f"   You can manually open this PDF to see if it contains text or just images")
            
            # Try to get basic PDF info
            try:
                import PyPDF2
                import io
                reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                print(f"   Pages: {len(reader.pages)}")
                print(f"   Encrypted: {reader.is_encrypted}")
                if reader.metadata:
                    title = reader.metadata.get('/Title', 'Unknown')
                    print(f"   Title: {title}")
            except:
                print("   Could not read PDF metadata")
            
        except Exception as e:
            print(f"Failed to save problematic PDF: {e}")
    
    def _get_filename_from_response(self, url: str, response) -> str:
        """Extract filename from URL or response headers"""
        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get('content-disposition', '')
        if content_disposition:
            # Parse filename from content-disposition header
            import re
            filename_match = re.search(r'filename[*]?=["\']?([^"\';\s]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1)
                print(f"Filename from Content-Disposition: {filename}")
                return filename
        
        # Fallback to URL path
        parsed = urlparse(url)
        path = parsed.path
        if path and '/' in path:
            filename = path.split('/')[-1]
            if filename and '.' in filename:
                print(f"Filename from URL path: {filename}")
                return filename
        
        # Last resort: generate filename based on content type
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' in content_type:
            return 'linked_document.pdf'
        elif 'image' in content_type:
            if 'jpeg' in content_type or 'jpg' in content_type:
                return 'linked_image.jpg'
            elif 'png' in content_type:
                return 'linked_image.png'
            else:
                return 'linked_image.img'
        else:
            return 'linked_resource'
    
    def _save_html_to_file(self, html_content: str, email_id: str, subject: str) -> str:
        """Save HTML content to file for inspection"""
        # Create safe filename
        safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{email_id[:8]}_{safe_subject}.html"
        filepath = os.path.join(self.html_output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return filepath
        except Exception as e:
            print(f"Failed to save HTML file: {e}")
            return ""
    
    def _should_process_attachment(self, attachment: Dict) -> bool:
        """Determine if attachment should be processed for text extraction"""
        content_type = attachment.get('contentType', '').lower()
        filename = attachment.get('name', '').lower()
        
        # Process all images (inline or not)
        if 'image' in content_type:
            return True
        
        # Process PDFs and documents
        if any(file_type in content_type for file_type in PROCESSABLE_CONTENT_TYPES):
            return True
        
        # Check file extension
        if any(filename.endswith(ext) for ext in PROCESSABLE_EXTENSIONS):
            return True
        
        return False
    
    def _process_attachment(self, email_id: str, attachment: Dict) -> str:
        """Download and extract text from attachment"""
        full_attachment = self.email_fetcher.download_attachment(email_id, attachment['id'])
        
        if full_attachment and full_attachment.get('contentBytes'):
            return self.ocr_processor.extract_text_from_attachment(full_attachment)
        
        return ""