import os
import base64
import concurrent.futures
from openai import OpenAI
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
import pymupdf

class TyphoonOCRReader(BaseReader):
    """Custom LlamaIndex reader that uses OpenTyphoon's typhoon-ocr model
    to extract text from PDFs by rendering each page as an image.
    """
    def __init__(self, api_key: str = None, base_url: str = "https://api.opentyphoon.ai/v1", max_workers: int = 4):
        super().__init__()
        self.api_key = api_key or os.getenv("TYPHOON_API_KEY")
        self.base_url = base_url
        self.max_workers = max_workers
        
        if not self.api_key or self.api_key == "your_typhoon_api_key_here" or self.api_key == "mock_key_for_testing":
            raise ValueError("TYPHOON_API_KEY is not set or is using a placeholder. Please set it in your environment or .env file.")
            
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _ocr_page(self, page_idx: int, png_bytes: bytes, file_name: str) -> tuple[int, str]:
        """Submits a single page image to the typhoon-ocr API."""
        base64_image = base64.b64encode(png_bytes).decode('utf-8')
        
        # Simple retry logic for transient API issues (e.g. rate limits or server errors)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="typhoon-ocr",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all text and structure from this image. Output in clean Markdown format."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ]
                )
                text = response.choices[0].message.content
                print(f"[OCR] Successfully processed {file_name} - Page {page_idx + 1}")
                return page_idx, text
            except Exception as e:
                print(f"[Warning] Failed OCR request for {file_name} - Page {page_idx + 1} (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    # On final failure, return empty text but don't crash the pipeline
                    return page_idx, f"[OCR Error: Failed to extract text for page {page_idx + 1}]"
                import time
                time.sleep(2 ** attempt) # Exponential backoff

    def load_data(self, file_path: str, extra_info: dict = None) -> list[Document]:
        """Loads data from the PDF file, rendering pages and calling typhoon-ocr concurrently."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        print(f"[OCR] Opening PDF for visual extraction: {file_name}...")
        
        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        print(f"[OCR] PDF has {total_pages} page(s). Rendering pages and queueing OCR requests...")

        # 1. Render all pages to PNG bytes in memory
        pages_to_process = []
        for i in range(total_pages):
            page = doc[i]
            # Render page with 150 DPI resolution for clear text recognition
            pix = page.get_pixmap(dpi=150)
            png_bytes = pix.tobytes("png")
            pages_to_process.append((i, png_bytes))
            
        doc.close()

        # 2. Concurrently call Typhoon OCR API
        ocr_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_page = {
                executor.submit(self._ocr_page, page_idx, png_bytes, file_name): page_idx
                for page_idx, png_bytes in pages_to_process
            }
            for future in concurrent.futures.as_completed(future_to_page):
                page_idx, text = future.result()
                ocr_results[page_idx] = text

        # 3. Build ordered documents list
        documents = []
        for i in range(total_pages):
            text = ocr_results.get(i, "")
            
            # Construct standard metadata
            metadata = {
                "file_path": file_path,
                "file_name": file_name,
                "page_num": i + 1,
                "extraction_method": "typhoon_ocr"
            }
            if extra_info:
                metadata.update(extra_info)

            documents.append(Document(text=text, metadata=metadata))

        print(f"[OCR] Visual extraction completed for: {file_name}")
        return documents


class LocalPDFReader(BaseReader):
    """Custom LlamaIndex reader that extracts text locally.
    It first attempts direct text extraction via PyMuPDF.
    If the page is scanned (no text layer), it falls back to EasyOCR (if installed).
    """
    def __init__(self):
        super().__init__()
        self._easyocr_reader = None

    def _get_easyocr_reader(self):
        if self._easyocr_reader is None:
            try:
                import easyocr
                # Initialize reader for Thai and English
                print("[OCR] Loading local EasyOCR model (Thai + English)...")
                # EasyOCR downloads the model on the first load if not present
                self._easyocr_reader = easyocr.Reader(['th', 'en'])
            except ImportError:
                print("[Warning] 'easyocr' library not found. Local OCR fallback is disabled.")
                print("To enable local OCR for scanned PDFs, please run: pip install easyocr")
                self._easyocr_reader = False
        return self._easyocr_reader

    def load_data(self, file_path: str, extra_info: dict = None) -> list[Document]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        print(f"[Local Extract] Opening PDF for local extraction: {file_name}...")
        
        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        
        documents = []
        for i in range(total_pages):
            page = doc[i]
            # 1. Attempt direct text extraction
            text = page.get_text()
            
            method = "direct"
            # 2. Check if the page is empty/scanned
            if not text.strip():
                print(f"[Local Extract] Page {i + 1} has no text layer. Attempting local OCR...")
                # Render page to PNG bytes
                pix = page.get_pixmap(dpi=150)
                png_bytes = pix.tobytes("png")
                
                reader = self._get_easyocr_reader()
                if reader:
                    try:
                        results = reader.readtext(png_bytes, detail=0)
                        text = "\n".join(results)
                        method = "local_ocr"
                        print(f"[Local OCR] Successfully OCR-ed page {i + 1}")
                    except Exception as e:
                        print(f"[Error] Failed running EasyOCR on page {i + 1}: {e}")
                        text = f"[OCR Error: Failed to perform local OCR on page {i + 1}]"
                        method = "error"
                else:
                    text = f"[OCR Warning: easyocr is required to extract text from scanned page {i + 1}]"
                    method = "warning"
            else:
                print(f"[Local Extract] Successfully extracted text directly from page {i + 1}")

            metadata = {
                "file_path": file_path,
                "file_name": file_name,
                "page_num": i + 1,
                "extraction_method": method
            }
            if extra_info:
                metadata.update(extra_info)

            documents.append(Document(text=text, metadata=metadata))
            
        doc.close()
        print(f"[Local Extract] Extraction completed for: {file_name}")
        return documents


class HybridPDFReader(BaseReader):
    """Custom LlamaIndex reader that delegates to either LocalPDFReader or TyphoonOCRReader
    depending on the configured mode.
    """
    def __init__(self, mode: str = None, api_key: str = None, base_url: str = "https://api.opentyphoon.ai/v1", max_workers: int = 4):
        super().__init__()
        # Check environment variable first, then fallback to argument, default to 'local'
        env_mode = os.getenv("PDF_EXTRACT_MODE")
        self.mode = mode or env_mode or "local"
        self.mode = self.mode.lower().strip()
        
        if self.mode not in ["local", "typhoon"]:
            print(f"[Warning] Invalid extraction mode '{self.mode}'. Defaulting to 'local'.")
            self.mode = "local"
            
        self.api_key = api_key
        self.base_url = base_url
        self.max_workers = max_workers
        
    def load_data(self, file_path: str, extra_info: dict = None) -> list[Document]:
        print(f"[Hybrid Extract] Processing file using mode: {self.mode}")
        if self.mode == "typhoon":
            # Initialize TyphoonOCRReader dynamically only when needed to prevent premature key validation errors
            reader = TyphoonOCRReader(api_key=self.api_key, base_url=self.base_url, max_workers=self.max_workers)
            return reader.load_data(file_path, extra_info)
        else:
            reader = LocalPDFReader()
            return reader.load_data(file_path, extra_info)
