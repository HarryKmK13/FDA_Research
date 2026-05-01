#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, re, sys, os
from pathlib import Path
from datetime import datetime

import fitz               # PyMuPDF
import pandas as pd
from tqdm import tqdm
import requests

# Optional imports for enhanced PDF extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("[WARN] pdfplumber not installed. Install with: pip install pdfplumber")

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    print("[WARN] PyPDF2 not installed. Install with: pip install PyPDF2")

# OCR imports
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_OCR = True
    print("[INFO] OCR capabilities available (pytesseract + pdf2image)")
except ImportError:
    HAS_OCR = False
    print("[WARN] OCR not available. Install with: pip install pytesseract pdf2image pillow")
    print("[WARN] Also install tesseract-ocr system package")

# ----------------------------
# Enhanced Model wrapper
# ----------------------------
class LLMOllama:
    def __init__(self,
                 model="qwen2.5:7b-instruct-q4_K_M",
                 url="http://localhost:11434",
                 num_ctx=8192):
        self.model = model
        self.url = url.rstrip("/")
        self.num_ctx = num_ctx

    def infer(self, prompt, max_new_tokens=1200, temperature=0.1, timeout=400):
        """Enhanced inference with better parameters."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "num_predict": max_new_tokens,
                "temperature": temperature,
                "num_ctx": self.num_ctx,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "presence_penalty": 0.1
            }
        }
        try:
            r = requests.post(f"{self.url}/api/generate", json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ollama request failed: {e}")
            return ""
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return ""

# ----------------------------
# Columns / keys
# ----------------------------
petition_columns = [
    "File Name",
    "Date of Petition",
    "Date Comments",
    "Identity of Submitting Entity",
    "Representation Details",
    "Cited Statutes or Regulations",
    "FDA Action Commented On",
    "Requested Action",
    "Justification for Request",
]

response_columns = [
    "File Name",
    "Date of Response",
    "Date Comments",
    "Responding FDA Center",
    "Response to Petition",
    "Cited Statutes or Regulations",
    "Justification for Response",
]

petition_keys = [
    "Date of Petition",
    "Date Comments",
    "Identity of Submitting Entity",
    "Representation Details",
    "Cited Statutes or Regulations",
    "FDA Action Commented On",
    "Requested Action",
    "Justification for Request",
]

response_keys = [
    "Date of Response",
    "Date Comments",
    "Responding FDA Center",
    "Response to Petition",
    "Cited Statutes or Regulations",
    "Justification for Response",
]

# ----------------------------
# OCR Enhancement Functions
# ----------------------------
def preprocess_image_for_ocr(image):
    """Preprocess image to improve OCR accuracy."""
    try:
        # Convert to grayscale if not already
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        # Apply slight blur to reduce noise
        image = image.filter(ImageFilter.MedianFilter(size=1))

        return image
    except Exception as e:
        print(f"[DEBUG] Image preprocessing failed: {e}")
        return image

def extract_with_ocr(pdf_path, dpi=300, lang='eng'):
    """Extract text using OCR with image preprocessing."""
    if not HAS_OCR:
        return ""

    try:
        print(f"[DEBUG] Starting OCR extraction for {Path(pdf_path).name}")

        # Convert PDF to images
        try:
            images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=None)
        except Exception as e:
            print(f"[ERROR] PDF to image conversion failed: {e}")
            return ""

        if not images:
            print(f"[WARN] No images extracted from PDF")
            return ""

        print(f"[DEBUG] Converted {len(images)} pages to images")

        full_text = []
        successful_pages = 0

        # OCR configuration for better accuracy
        ocr_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,;:!?-()[]{}"/\'&@#$%^*+=<>|\\~`'

        for i, image in enumerate(images):
            try:
                # Preprocess image for better OCR
                processed_image = preprocess_image_for_ocr(image)

                # Extract text with multiple OCR attempts
                page_text = ""

                # Try standard PSM mode
                try:
                    page_text = pytesseract.image_to_string(processed_image, lang=lang, config=ocr_config)
                except Exception:
                    # Fallback to different PSM mode
                    try:
                        fallback_config = r'--oem 3 --psm 3'
                        page_text = pytesseract.image_to_string(processed_image, lang=lang, config=fallback_config)
                    except Exception:
                        # Last resort - minimal config
                        page_text = pytesseract.image_to_string(processed_image, lang=lang)

                if page_text and page_text.strip():
                    # Clean up OCR text
                    cleaned_text = clean_ocr_text(page_text)
                    if cleaned_text:
                        full_text.append(f"[OCR PAGE {i + 1}]\n{cleaned_text}")
                        successful_pages += 1
                        print(f"[DEBUG] Page {i + 1}: {len(cleaned_text)} chars extracted")
                    else:
                        print(f"[DEBUG] Page {i + 1}: No meaningful text after cleaning")
                else:
                    print(f"[DEBUG] Page {i + 1}: No text extracted")

            except Exception as e:
                print(f"[ERROR] OCR failed for page {i + 1}: {e}")
                continue

        if successful_pages == 0:
            print(f"[WARN] OCR failed to extract text from any page")
            return ""

        result_text = "\n\n".join(full_text)
        print(f"[SUCCESS] OCR extracted {len(result_text)} characters from {successful_pages}/{len(images)} pages")

        return result_text

    except Exception as e:
        print(f"[ERROR] OCR extraction completely failed: {e}")
        return ""

def clean_ocr_text(text):
    """Clean OCR text to remove common artifacts and improve quality."""
    if not text:
        return ""

    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Remove lines with too many special characters (likely OCR noise)
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip lines that are mostly special characters or very short
        if len(line) < 3:
            continue

        # Count alphanumeric vs special characters
        alphanum_count = sum(1 for c in line if c.isalnum())
        total_count = len(line)

        if total_count > 0 and alphanum_count / total_count >= 0.5:  # At least 50% alphanumeric
            cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)

    # Additional cleaning
    result = re.sub(r'[^\x00-\x7F]+', ' ', result)  # Remove non-ASCII
    result = re.sub(r'\s+', ' ', result)  # Normalize whitespace again
    result = result.strip()

    return result

# ----------------------------
# Enhanced PDF text extraction with OCR fallback
# ----------------------------
def extract_with_pymupdf(pdf_path):
    """PyMuPDF extraction with multiple methods."""
    try:
        with fitz.open(pdf_path) as doc:
            full_text = []

            for page_num, page in enumerate(doc):
                page_texts = []

                # Method 1: Standard text
                text = page.get_text("text")
                if text and len(text.strip()) > 20:
                    page_texts.append(("text", text))

                # Method 2: Dictionary method (better structure preservation)
                try:
                    text_dict = page.get_text("dict")
                    if text_dict and "blocks" in text_dict:
                        extracted_lines = []
                        for block in text_dict["blocks"]:
                            if "lines" in block:
                                for line in block["lines"]:
                                    if "spans" in line:
                                        line_text = "".join(span.get("text", "") for span in line["spans"])
                                        if line_text.strip():
                                            extracted_lines.append(line_text)

                        if extracted_lines:
                            dict_text = "\n".join(extracted_lines)
                            if len(dict_text.strip()) > len(text.strip()):  # Use if better
                                page_texts.append(("dict", dict_text))
                except Exception:
                    pass

                # Method 3: HTML method (preserves some formatting)
                try:
                    html_text = page.get_text("html")
                    if html_text and len(html_text.strip()) > len(text.strip()):
                        # Strip HTML tags for cleaner text
                        clean_html = re.sub(r'<[^>]+>', '', html_text)
                        clean_html = re.sub(r'\s+', ' ', clean_html).strip()
                        if clean_html:
                            page_texts.append(("html", clean_html))
                except Exception:
                    pass

                # Use the best extraction for this page
                if page_texts:
                    best_text = max(page_texts, key=lambda x: len(x[1].strip()))
                    full_text.append(f"[PAGE {page_num + 1}]\n{best_text[1]}")

            return "\n\n".join(full_text)

    except Exception as e:
        print(f"[ERROR] PyMuPDF extraction failed: {e}")
        return ""

def extract_with_pdfplumber(pdf_path):
    """pdfplumber extraction - often better for complex layouts."""
    if not HAS_PDFPLUMBER:
        return ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = []
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    full_text.append(f"[PAGE {page_num + 1}]\n{text}")
            return "\n\n".join(full_text)
    except Exception as e:
        print(f"[ERROR] pdfplumber extraction failed: {e}")
        return ""

def extract_with_pypdf2(pdf_path):
    """PyPDF2 extraction - different parsing approach."""
    if not HAS_PYPDF2:
        return ""

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = []
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    full_text.append(f"[PAGE {page_num + 1}]\n{text}")
            return "\n\n".join(full_text)
    except Exception as e:
        print(f"[ERROR] PyPDF2 extraction failed: {e}")
        return ""

def robust_pdf_extraction(pdf_path):
    """Try multiple extraction methods including OCR fallback."""
    print(f"[DEBUG] Attempting robust extraction for {Path(pdf_path).name}")

    # Standard extractors (fast)
    extractors = [
        ("pdfplumber", extract_with_pdfplumber),
        ("pymupdf_enhanced", extract_with_pymupdf),
        ("pypdf2", extract_with_pypdf2),
    ]

    results = {}

    # Try standard extraction methods first
    for name, extractor in extractors:
        try:
            text = extractor(pdf_path)
            if text and text.strip():
                # Quality metrics
                char_count = len(text)
                word_count = len(text.split())
                meaningful_words = len([w for w in text.split() if len(w) > 2 and w.isalpha()])

                results[name] = {
                    'text': text,
                    'char_count': char_count,
                    'word_count': word_count,
                    'meaningful_words': meaningful_words,
                    'quality_score': meaningful_words * 2 + word_count  # Simple quality metric
                }

                print(f"[DEBUG] {name}: {char_count} chars, {word_count} words, {meaningful_words} meaningful words")
            else:
                print(f"[DEBUG] {name}: No text extracted")

        except Exception as e:
            print(f"[DEBUG] {name}: Failed with error: {e}")

    # Check if we have good results from standard methods
    if results:
        best_method = max(results.keys(), key=lambda k: results[k]['quality_score'])
        best_result = results[best_method]

        # Use standard extraction if quality is reasonable
        if best_result['meaningful_words'] >= 50:  # At least 50 meaningful words
            print(f"[SUCCESS] Using {best_method} extraction ({best_result['char_count']} chars)")
            return best_result['text']
        else:
            print(f"[WARN] Best standard extraction ({best_method}) has low quality: {best_result['meaningful_words']} meaningful words")

    # Fall back to OCR if standard methods failed or produced poor results
    if HAS_OCR:
        print(f"[INFO] Falling back to OCR extraction...")
        ocr_text = extract_with_ocr(pdf_path)

        if ocr_text and ocr_text.strip():
            ocr_words = len([w for w in ocr_text.split() if len(w) > 2 and w.isalpha()])
            print(f"[SUCCESS] OCR extracted {len(ocr_text)} chars, {ocr_words} meaningful words")

            # Compare OCR with best standard method if available
            if results:
                best_standard = results[max(results.keys(), key=lambda k: results[k]['quality_score'])]
                if ocr_words > best_standard['meaningful_words']:
                    print(f"[INFO] OCR result better than standard extraction, using OCR")
                    return ocr_text
                else:
                    print(f"[INFO] Standard extraction better than OCR, using standard")
                    return best_standard['text']
            else:
                return ocr_text
        else:
            print(f"[ERROR] OCR also failed to extract meaningful text")
    else:
        print(f"[WARN] OCR not available, cannot attempt OCR fallback")

    # Last resort - return best standard result if any
    if results:
        best_method = max(results.keys(), key=lambda k: results[k]['quality_score'])
        print(f"[WARN] Using low-quality {best_method} result as last resort")
        return results[best_method]['text']

    print(f"[ERROR] All extraction methods failed for {pdf_path}")
    return ""

# ----------------------------
# Enhanced candidate extraction
# ----------------------------
MONTHS = "(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_PATTERNS = [
    rf"\b{MONTHS}\s+\d{{1,2}},\s*\d{{4}}\b",       # January 5, 2024
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",                # 1/5/2024 or 01/05/24
    r"\b\d{4}-\d{2}-\d{2}\b",                      # 2024-01-05
    rf"\b\d{{1,2}}\s+{MONTHS}\s+\d{{4}}\b",        # 5 January 2024
]

# Enhanced citation patterns - match both with and without section symbol
CFR_PATTERN = r"\b(\d+)\s*C\.?F\.?R\.?\s*(?:§|Section|Sec\.?)?\s*([\d\.\-\(\)a-zA-Z]+)"
USC_PATTERN = r"\b(\d+)\s*U\.?S\.?C\.?(?:A\.?)?\s*(?:§|Section|Sec\.?)?\s*([\d\.\-\(\)a-zA-Z]+)"
# Also catch variations like "section 505 of the FD&C Act"
FDCA_PATTERN = r"(?:section|§)\s*([\d\.\-\(\)a-zA-Z]+)\s+of\s+the\s+(?:FD&C|FDCA|Federal Food[,\s]+Drug[,\s]+and Cosmetic)\s+Act"

CFR_USC_RE = re.compile(f"(?:{CFR_PATTERN}|{USC_PATTERN}|{FDCA_PATTERN})", re.IGNORECASE)

FDA_CENTERS_FULL = {
    "CDER": ["Center for Drug Evaluation and Research", "CDER"],
    "CBER": ["Center for Biologics Evaluation and Research", "CBER"],
    "CDRH": ["Center for Devices and Radiological Health", "CDRH"],
    "CFSAN": ["Center for Food Safety and Applied Nutrition", "CFSAN"],
    "CVM": ["Center for Veterinary Medicine", "CVM"],
    "ORA": ["Office of Regulatory Affairs", "ORA"],
    "CTP": ["Center for Tobacco Products", "CTP"]
}

def extract_enhanced_candidates(text):
    """Extract candidates with better patterns and validation."""
    candidates = {
        "dates": set(),
        "citations": set(),
        "centers": set(),
        "response_indicators": set(),
        "entities": set(),
        "law_firms": set(),
        "represented_entities": set()
    }

    # Extract dates with validation
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                # Reconstruct full match
                full_match = " ".join(str(m) for m in match if m)
            else:
                full_match = match

            # Basic validation - must contain 4-digit year
            if re.search(r'\b20\d{2}\b', full_match):
                candidates["dates"].add(full_match)

    # Extract legal citations with improved handling
    # Find CFR citations
    cfr_matches = re.finditer(CFR_PATTERN, text, re.IGNORECASE)
    for match in cfr_matches:
        title = match.group(1)
        section = match.group(2)
        # Normalize format: "21 CFR 314.50"
        citation = f"{title} CFR {section}"
        candidates["citations"].add(citation)

    # Find USC citations
    usc_matches = re.finditer(USC_PATTERN, text, re.IGNORECASE)
    for match in usc_matches:
        title = match.group(1)
        section = match.group(2)
        # Normalize format: "21 U.S.C. § 355"
        citation = f"{title} U.S.C. § {section}"
        candidates["citations"].add(citation)

    # Find FD&C Act references
    fdca_matches = re.finditer(FDCA_PATTERN, text, re.IGNORECASE)
    for match in fdca_matches:
        section = match.group(1)
        citation = f"Section {section} of the FD&C Act"
        candidates["citations"].add(citation)

    # Also look for standalone section symbols with numbers (backup)
    section_symbol_pattern = r"(?:§|Section)\s*(\d+[\.\-\(\)a-zA-Z]*)"
    section_matches = re.finditer(section_symbol_pattern, text, re.IGNORECASE)
    for match in section_matches:
        section_ref = match.group(1)
        # Look for context around this to determine if it's CFR or USC
        context_start = max(0, match.start() - 30)
        context_end = min(len(text), match.end() + 30)
        context = text[context_start:context_end]

        if re.search(r'\bC\.?F\.?R\.?', context, re.IGNORECASE):
            # Try to find the title number
            title_match = re.search(r'\b(\d+)\s*C\.?F\.?R\.?', context, re.IGNORECASE)
            if title_match:
                citation = f"{title_match.group(1)} CFR {section_ref}"
                candidates["citations"].add(citation)
        elif re.search(r'\bU\.?S\.?C\.?', context, re.IGNORECASE):
            title_match = re.search(r'\b(\d+)\s*U\.?S\.?C\.?', context, re.IGNORECASE)
            if title_match:
                citation = f"{title_match.group(1)} U.S.C. § {section_ref}"
                candidates["citations"].add(citation)

    # Extract FDA centers
    for center_code, variations in FDA_CENTERS_FULL.items():
        for variation in variations:
            if re.search(rf"\b{re.escape(variation)}\b", text, re.IGNORECASE):
                candidates["centers"].add(center_code)

    # Extract response indicators
    response_patterns = [
        r"\bpetition\s+is\s+(approved?|denied?|granted?|rejected?)\b",
        r"\b(approving?|denying|granting|rejecting)\s+(?:the\s+)?petition\b",
        r"\b(?:we\s+are\s+)?(approving?|denying|granting|rejecting)\b",
        r"\bpartially\s+(approved?|granted?)\b"
    ]

    for pattern in response_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        candidates["response_indicators"].update(matches)

    # Extract LAW FIRMS (separate from represented entities)
    law_firm_patterns = [
        r"\b([A-Z][a-zA-Z]+(?:\s+(?:&|and)\s+[A-Z][a-zA-Z]+)+)\s+(?:LLP|PLLC|PC|P\.C\.)\b",
        r"\b([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:Law\s+(?:Firm|Offices?|Group)|Attorneys?|Legal)\b"
    ]

    for pattern in law_firm_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            candidates["law_firms"].add(match.strip())

    # Extract REPRESENTED ENTITIES (companies, organizations)
    # Look for "on behalf of [ENTITY]" patterns
    behalf_patterns = [
        r"(?:on\s+behalf\s+of|representing|for)\s+([A-Z][a-zA-Z\s]+(?:Inc\.?|LLC|Corp\.?|Company|Corporation|Pharmaceuticals?|Pharma|Laboratories?|Labs?|Associates?|Foundation|Institute|Association))",
        r"(?:filed\s+by|submitted\s+by)\s+([A-Z][a-zA-Z\s]+(?:Inc\.?|LLC|Corp\.?|Company|Corporation|Pharmaceuticals?|Pharma|Laboratories?|Labs?))"
    ]

    for pattern in behalf_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            entity = match.strip()
            # Filter out law firms from this list
            if not re.search(r'\b(?:LLP|PLLC|PC|P\.C.|Law|Legal|Attorneys?)\b', entity, re.IGNORECASE):
                candidates["represented_entities"].add(entity)

    # Extract general company/entity names (but prioritize those found in "on behalf of")
    entity_patterns = [
        r"\b([A-Z][a-z]+\s+(?:Inc\.?|LLC|Corp\.?|Company|Corporation))\b",
        r"\b([A-Z][a-zA-Z]+\s+Pharmaceuticals?|Pharma)\b",
        r"\b([A-Z][a-zA-Z]+\s+(?:Laboratories?|Labs?))\b"
    ]

    for pattern in entity_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            entity = match.strip()
            # Avoid adding law firms
            if not re.search(r'\b(?:LLP|PLLC|PC|P\.C.|Law|Legal|Attorneys?)\b', entity, re.IGNORECASE):
                candidates["entities"].add(entity)

    # Convert sets to sorted lists for JSON serialization
    return {k: sorted(list(v)) if isinstance(v, set) else v for k, v in candidates.items()}

# ----------------------------
# Enhanced prompts
# ----------------------------
def build_enhanced_petition_prompt(document_text, candidates):
    """Simplified petition prompt optimized for complex legal documents."""
    keys = petition_keys

    # More aggressive truncation for petitions
    if len(document_text) > 12000:
        # Keep first 8000 chars (header, intro) and last 4000 (signatures, dates)
        doc = (document_text[:8000] +
               "\n\n[... DOCUMENT TRUNCATED ...]\n\n" +
               document_text[-4000:])
    else:
        doc = document_text

    return f"""Extract key information from this FDA citizen petition. Return only valid JSON with these exact keys:

{json.dumps(keys, indent=2)}

CRITICAL EXTRACTION RULES:

1. "Identity of Submitting Entity" - WHO is the petition about/for?
   - PRIORITY: The company, organization, or individual whose interests are being represented
   - Look for: "on behalf of [COMPANY]", "representing [COMPANY]", "[COMPANY] hereby petitions"
   - Examples: "Pfizer Inc.", "Generic Drug Association", "Dr. John Smith (individual petitioner)"
   - If ONLY a law firm is found with no client mentioned, use the law firm name
   - Common patterns: "[Entity] Inc.", "[Entity] LLC", "[Entity] Pharmaceuticals"

2. "Representation Details" - WHO filed it and for whom?
   - The full representation chain: attorney/law firm → client/entity
   - Format: "Filed by [LAW FIRM/ATTORNEY] on behalf of [CLIENT/ENTITY]"
   - Examples:
     * "Filed by Smith & Jones LLP on behalf of MedCorp Inc"
     * "Filed by John Doe, Attorney, representing Generic Pharma LLC"
     * "Self-filed by ABC Company" (if no separate representation)
   - If petition is self-filed: "Self-filed" or "Filed directly by [Entity]"

3. "Date of Petition" - The filing/submission date (format: YYYY-MM-DD)

4. "Cited Statutes or Regulations" - ALL legal citations as JSON array
   - Include BOTH CFR regulations AND USC statutes
   - Look for: "21 CFR", "U.S.C.", "§", "FD&C Act", "Federal Food, Drug, and Cosmetic Act"
   - Examples: ["21 CFR 314.50", "21 U.S.C. § 355", "Section 505 of the FD&C Act"]

5. "Requested Action" - What specific action is FDA being asked to take?

6. All other fields as appropriate, or "Not Mentioned" if not found

EXAMPLES:

Example 1 (Law firm representing company):
{{
  "Date of Petition": "2024-04-05",
  "Date Comments": "Not Mentioned",
  "Identity of Submitting Entity": "MedCorp Pharmaceuticals Inc",
  "Representation Details": "Filed by Smith & Associates LLP on behalf of MedCorp Pharmaceuticals Inc",
  "Cited Statutes or Regulations": ["21 CFR 314.50", "21 U.S.C. § 355"],
  "FDA Action Commented On": "Generic drug approval process",
  "Requested Action": "Approve pending ANDA application",
  "Justification for Request": "Bioequivalence data supports approval"
}}

Example 2 (Company filing directly):
{{
  "Date of Petition": "2024-03-15",
  "Date Comments": "Not Mentioned",
  "Identity of Submitting Entity": "BioTech Labs LLC",
  "Representation Details": "Self-filed by BioTech Labs LLC through regulatory affairs department",
  "Cited Statutes or Regulations": ["21 CFR 10.30", "Section 505 of the FD&C Act"],
  "FDA Action Commented On": "Proposed rule on biosimilar labeling",
  "Requested Action": "Modify proposed labeling requirements",
  "Justification for Request": "Current proposal would create market confusion"
}}

Example 3 (Law firm only, no client identified):
{{
  "Date of Petition": "2024-02-20",
  "Date Comments": "Not Mentioned",
  "Identity of Submitting Entity": "Johnson & Williams PLLC",
  "Representation Details": "Filed by Johnson & Williams PLLC; client not disclosed in document",
  "Cited Statutes or Regulations": ["21 U.S.C. § 355"],
  "FDA Action Commented On": "Drug approval timeline",
  "Requested Action": "Expedite review process",
  "Justification for Request": "Public health urgency"
}}

EXTRACTED CANDIDATES (reference if helpful):
{json.dumps(candidates, indent=2)}

DOCUMENT:
{doc}

Return ONLY valid JSON:"""

def build_enhanced_response_prompt(document_text, candidates):
    """Enhanced response prompt with concrete examples."""
    keys = response_keys

    # Smart truncation
    if len(document_text) > 16000:
        mid_point = len(document_text) // 2
        doc = (document_text[:8000] +
               "\n\n[... MIDDLE SECTION TRUNCATED FOR LENGTH ...]\n\n" +
               document_text[mid_point + 8000:])
    else:
        doc = document_text

    return f"""You are an expert legal document analyst extracting structured data from an FDA response letter to a citizen petition.

TASK: Extract information and return a JSON object with exactly these keys:
{json.dumps(keys, indent=2)}

CRITICAL EXTRACTION RULES:

1. "Date of Response": The PRIMARY official FDA response date
   - Look for: FDA letterhead dates, signature dates, "Date:" labels
   - Format as YYYY-MM-DD (e.g., "April 5, 2024" → "2024-04-05")
   - This is the MAIN response date

2. "Date Comments": Additional date information ONLY
   - Use for: docket posting dates, received dates, processing dates
   - If only ONE date exists, put it in "Date of Response", not here
   - If no additional dates: "Not Mentioned"

3. "Responding FDA Center": Which FDA center/office responded
   - Common values: "CDER", "CBER", "CDRH", "CFSAN", "CVM", "ORA", "CTP"
   - Look for full names: "Center for Drug Evaluation and Research" → "CDER"

4. "Response to Petition": FDA's decision (use exactly one):
   - "approved" - petition granted/approved
   - "denied" - petition rejected/denied
   - "partially approved" - some parts approved, some denied
   - "other: [brief description]" - for interim responses, withdrawn, etc.

5. "Cited Statutes or Regulations": All legal references found
   - Format as JSON array: ["21 CFR 314.93", "21 U.S.C. § 355", "Section 505 of the FD&C Act"]
   - Include BOTH CFR regulations AND USC statutes
   - Look for section symbol (§) which often precedes statute numbers
   - Common patterns: "21 CFR", "21 U.S.C.", "USC", "§", "FD&C Act"

6. "Justification for Response": FDA's main reasoning (brief summary)
   - Why they approved/denied
   - Key points from their analysis

EXAMPLES:
Input: "April 5, 2024 ... CDER ... petition is denied ... 21 CFR 314.93 ... safety studies required ..."
Output: {{
  "Date of Response": "2024-04-05",
  "Date Comments": "Not Mentioned",
  "Responding FDA Center": "CDER",
  "Response to Petition": "denied",
  "Cited Statutes or Regulations": ["21 CFR 314.93"],
  "Justification for Response": "Additional safety studies required before approval can be considered"
}}

EXTRACTED CANDIDATES (use if accurate, ignore if incorrect):
{json.dumps(candidates, indent=2)}

DOCUMENT TEXT:
{doc}

Return JSON only:"""

# ----------------------------
# Helper functions
# ----------------------------
PLACEHOLDER = "Not Mentioned"

def robust_json_parse(raw_response):
    """Robust JSON parsing with multiple fallback strategies."""
    if not raw_response or not raw_response.strip():
        return {}

    # Clean the response
    cleaned = raw_response.strip()

    # Strategy 1: Direct parse (with Unicode support)
    try:
        # Use ensure_ascii=False to properly handle Unicode characters
        parsed = json.loads(cleaned)
        return parsed
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find JSON blocks with better patterns
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(?:^|\n)\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*(?:\n|$)',
        r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})',
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, cleaned, re.DOTALL | re.MULTILINE)

        for match in reversed(matches):  # Try last match first
            try:
                # Clean common JSON issues
                json_text = match.strip()

                # Fix common formatting issues
                json_text = re.sub(r',\s*}', '}', json_text)
                json_text = re.sub(r',\s*]', ']', json_text)
                # Remove control characters but keep Unicode characters like §
                json_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_text)

                # Try to fix unescaped quotes in values
                json_text = re.sub(r'(?<!\\)"(?=[^"]*":)', '\\"', json_text)

                parsed = json.loads(json_text)
                if isinstance(parsed, dict) and len(parsed) > 0:
                    return parsed

            except json.JSONDecodeError:
                continue

    # Strategy 3: Manual key-value extraction
    try:
        manual_dict = {}
        # Look for "key": "value" patterns
        kv_pattern = r'"([^"]+)"\s*:\s*"([^"]*(?:\\.[^"]*)*)"'
        matches = re.findall(kv_pattern, cleaned)

        if matches:
            for key, value in matches:
                # Unescape quotes
                value = value.replace('\\"', '"')
                manual_dict[key] = value

            if len(manual_dict) > 2:  # At least some fields found
                return manual_dict
    except Exception:
        pass

    print(f"[ERROR] All JSON parsing strategies failed")
    print(f"[DEBUG] Response preview: {cleaned[:500]}...")
    return {}

def ensure_keys(d, required_keys):
    """Ensure all keys exist with proper handling."""
    out = {}
    for k in required_keys:
        v = d.get(k, PLACEHOLDER)

        # Handle nested structures
        if isinstance(v, dict) and "value" in v:
            v = v.get("value", PLACEHOLDER)
        elif isinstance(v, list) and len(v) == 1 and isinstance(v[0], dict) and "value" in v[0]:
            v = v[0].get("value", PLACEHOLDER)

        # Convert to string and clean
        if v is None or v == "":
            out[k] = PLACEHOLDER
        elif isinstance(v, list):
            # Handle arrays (like citations)
            if all(isinstance(item, str) for item in v):
                out[k] = v if v else PLACEHOLDER
            else:
                out[k] = [str(item) for item in v] if v else PLACEHOLDER
        else:
            out[k] = str(v).strip() if str(v).strip() else PLACEHOLDER

    return out

def normalize_date(value):
    """Enhanced date normalization."""
    if not isinstance(value, str) or not value.strip() or value.strip().lower() == PLACEHOLDER.lower():
        return PLACEHOLDER

    s = value.strip()

    # Try pandas first (most flexible)
    try:
        dt = pd.to_datetime(s, errors="coerce", dayfirst=False)
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # Try specific formats
    formats = [
        "%B %d, %Y",      # January 5, 2024
        "%b %d, %Y",      # Jan 5, 2024
        "%m/%d/%Y",       # 1/5/2024
        "%m/%d/%y",       # 1/5/24
        "%Y-%m-%d",       # 2024-01-05
        "%d %B %Y",       # 5 January 2024
        "%d %b %Y",       # 5 Jan 2024
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If all else fails, try to extract year and see if it looks reasonable
    year_match = re.search(r'\b(20\d{2})\b', s)
    if year_match:
        year = int(year_match.group(1))
        if 2020 <= year <= 2030:  # Reasonable range for FDA documents
            return s  # Keep original if it contains a reasonable year

    return PLACEHOLDER

def extract_with_enhanced_pipeline(pdf_path, llm, doc_type):
    """Enhanced extraction pipeline with better error handling."""
    print(f"Processing: {Path(pdf_path).name}")

    # Enhanced PDF extraction
    text = robust_pdf_extraction(pdf_path)

    if not text or len(text.strip()) < 100:
        print(f"[WARN] Insufficient text extracted from {pdf_path}")
        return create_error_row(pdf_path, "Insufficient extractable text", doc_type)

    # Extract candidates
    candidates = extract_enhanced_candidates(text)
    print(f"[DEBUG] Candidates: {len(candidates['dates'])} dates, {len(candidates['centers'])} centers, {len(candidates['citations'])} citations")

    # Build appropriate prompt
    if doc_type == "petition":
        prompt = build_enhanced_petition_prompt(text, candidates)
        expected_keys = petition_keys
    else:
        prompt = build_enhanced_response_prompt(text, candidates)
        expected_keys = response_keys

    # Try extraction with retry logic
    for attempt in range(2):
        try:
            print(f"[DEBUG] Attempt {attempt + 1}")

            # Vary temperature slightly on retry
            temp = 0.1 + (attempt * 0.05)
            raw_response = llm.infer(prompt, max_new_tokens=1200, temperature=temp)

            if not raw_response:
                print(f"[WARN] Empty LLM response on attempt {attempt + 1}")
                continue

            # Parse JSON
            data = robust_json_parse(raw_response)

            if not data:
                print(f"[WARN] JSON parsing failed on attempt {attempt + 1}")
                if attempt == 0:  # Save debug info
                    debug_file = f"debug_{Path(pdf_path).stem}_attempt{attempt + 1}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"PDF: {pdf_path}\n")
                        f.write(f"Attempt: {attempt + 1}\n")
                        f.write("="*50 + "\n")
                        f.write("RAW RESPONSE:\n")
                        f.write("="*50 + "\n")
                        f.write(raw_response)
                continue

            # Ensure all required keys exist
            values = ensure_keys(data, expected_keys)

            # Normalize dates
            if doc_type == "petition":
                values["Date of Petition"] = normalize_date(values["Date of Petition"])
            else:
                values["Date of Response"] = normalize_date(values["Date of Response"])

            # Clean up date comments
            if values.get("Date Comments") != PLACEHOLDER:
                values["Date Comments"] = re.sub(r'\s+', ' ', values["Date Comments"]).strip()

            # Check extraction quality
            not_mentioned_count = sum(1 for v in values.values() if str(v).strip().lower() == PLACEHOLDER.lower())
            quality_ratio = 1 - (not_mentioned_count / len(expected_keys))

            print(f"[DEBUG] Extraction quality: {quality_ratio:.2%} ({len(expected_keys) - not_mentioned_count}/{len(expected_keys)} fields)")

            if quality_ratio >= 0.5 or attempt == 1:  # Accept if >50% or last attempt
                return build_final_row(pdf_path, values, expected_keys, doc_type)

        except Exception as e:
            print(f"[ERROR] Extraction attempt {attempt + 1} failed: {e}")
            continue

    # If we reach here, all attempts failed
    return create_error_row(pdf_path, "All extraction attempts failed", doc_type)

def create_error_row(pdf_path, reason, doc_type):
    """Create error row with proper structure."""
    if doc_type == "petition":
        columns = petition_columns
    else:
        columns = response_columns

    row = {col: PLACEHOLDER for col in columns}
    row["File Name"] = Path(pdf_path).name
    row["Date Comments"] = reason
    return row

def build_final_row(pdf_path, values, expected_keys, doc_type):
    """Build final row with validation."""
    if doc_type == "petition":
        columns = petition_columns
    else:
        columns = response_columns

    row = {"File Name": Path(pdf_path).name}

    for key in expected_keys:
        value = values.get(key, PLACEHOLDER)
        if isinstance(value, list):
            # Convert lists to JSON string for Excel with proper Unicode handling
            row[key] = json.dumps(value, ensure_ascii=False) if value != PLACEHOLDER else PLACEHOLDER
        else:
            row[key] = str(value).strip() if value and str(value).strip() else PLACEHOLDER

    return row

def find_pdfs(root_dir):
    """Find all PDF files in directory tree."""
    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"[ERROR] Directory does not exist: {root_dir}")
        return []
    pdfs = list(root_path.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDF files in {root_dir}")
    return sorted(str(p) for p in pdfs)

# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Enhanced FDA petition/response PDF extractor with OCR fallback")
    parser.add_argument("--input", required=True, help="Input directory containing PDFs")
    parser.add_argument("--output", required=True, help="Output Excel file path")
    parser.add_argument("--doc-type", choices=["petition", "response"], default="petition", help="Type of documents to process")
    parser.add_argument("--model", default="qwen2.5:7b-instruct-q4_K_M", help="Ollama model name")
    parser.add_argument("--url", default="http://localhost:11434", help="Ollama server URL")
    parser.add_argument("--context", type=int, default=8192, help="Context window size")
    parser.add_argument("--batch-size", type=int, default=10, help="Save every N documents")
    parser.add_argument("--ocr-dpi", type=int, default=300, help="OCR DPI resolution (higher = better quality, slower)")
    parser.add_argument("--disable-ocr", action="store_true", help="Disable OCR fallback")

    args = parser.parse_args()

    # Check dependencies
    missing_deps = []
    if not HAS_PDFPLUMBER:
        missing_deps.append("pdfplumber")
    if not HAS_PYPDF2:
        missing_deps.append("PyPDF2")

    if missing_deps:
        print(f"[WARN] Missing optional dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install " + " ".join(missing_deps))
        print("Continuing with available extractors...")

    if not HAS_OCR and not args.disable_ocr:
        print(f"[WARN] OCR dependencies not available. Install with:")
        print("pip install pytesseract pdf2image pillow")
        print("Also install system package: apt-get install tesseract-ocr")
        print("Continuing without OCR fallback...")

    # Initialize LLM
    llm = LLMOllama(model=args.model, url=args.url, num_ctx=args.context)

    # Find PDFs
    pdf_files = find_pdfs(args.input)
    if not pdf_files:
        print("[ERROR] No PDF files found!")
        return

    # Process documents
    results = []
    columns = petition_columns if args.doc_type == "petition" else response_columns

    print(f"\n[INFO] Starting extraction of {len(pdf_files)} {args.doc_type} documents")
    print(f"[INFO] Using model: {args.model}")
    print(f"[INFO] Available extractors: PyMuPDF" +
          (", pdfplumber" if HAS_PDFPLUMBER else "") +
          (", PyPDF2" if HAS_PYPDF2 else "") +
          (", OCR" if HAS_OCR and not args.disable_ocr else ""))

    for i, pdf_path in enumerate(tqdm(pdf_files, desc=f"Processing {args.doc_type}s")):
        try:
            row = extract_with_enhanced_pipeline(pdf_path, llm, args.doc_type)
            results.append(row)

            # Save periodically
            if (i + 1) % args.batch_size == 0:
                df = pd.DataFrame(results, columns=columns)
                df.to_excel(args.output, index=False)
                print(f"\n[INFO] Saved {len(results)} results to {args.output}")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user")
            break
        except Exception as e:
            print(f"[ERROR] Failed to process {pdf_path}: {e}")
            error_row = create_error_row(pdf_path, f"Processing error: {str(e)[:100]}", args.doc_type)
            results.append(error_row)

    # Save final results
    if results:
        df = pd.DataFrame(results, columns=columns)
        df.to_excel(args.output, index=False)
        print(f"\n[SUCCESS] Extraction complete!")
        print(f"[INFO] Total documents processed: {len(results)}")
        print(f"[INFO] Output saved to: {Path(args.output).resolve()}")

        # Detailed statistics
        error_indicators = ["error", "failed", "insufficient"]
        error_count = sum(1 for row in results
                         if any(indicator in str(row.get("Date Comments", "")).lower()
                               for indicator in error_indicators))
        success_count = len(results) - error_count

        print(f"[INFO] Successful extractions: {success_count}")
        print(f"[INFO] Failed extractions: {error_count}")

        if success_count > 0:
            # Quality metrics
            if args.doc_type == "petition":
                key_fields = ["Date of Petition", "Identity of Submitting Entity", "Requested Action"]
            else:
                key_fields = ["Date of Response", "Responding FDA Center", "Response to Petition"]

            high_quality = 0
            ocr_used = 0
            for row in results:
                filled_key_fields = sum(1 for field in key_fields
                                      if str(row.get(field, "")).strip().lower() != PLACEHOLDER.lower())
                if filled_key_fields >= len(key_fields) * 0.67:  # 2/3 key fields filled
                    high_quality += 1

                # Check if OCR was used (look for OCR PAGE markers in debug info)
                if "OCR PAGE" in str(row.get("Date Comments", "")):
                    ocr_used += 1

            print(f"[INFO] High quality extractions: {high_quality} ({high_quality/success_count*100:.1f}%)")
            if HAS_OCR and not args.disable_ocr:
                print(f"[INFO] Documents requiring OCR: {ocr_used}")
    else:
        print("[ERROR] No results to save!")

if __name__ == "__main__":
    main()
