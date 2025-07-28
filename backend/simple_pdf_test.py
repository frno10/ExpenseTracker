#!/usr/bin/env python3
"""
Simple PDF text extraction test.
"""

import pdfplumber
from pathlib import Path

def extract_pdf_text(pdf_path: str) -> str:
    """Simple PDF text extraction."""
    
    print(f"📄 Extracting text from: {pdf_path}")
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return ""
    
    try:
        text_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📊 PDF has {len(pdf.pages)} pages")
            
            for page_num, page in enumerate(pdf.pages):
                print(f"📄 Processing page {page_num + 1}...")
                try:
                    text = page.extract_text()
                    if text:
                        text_content.append(f"--- Page {page_num + 1} ---\n{text}\n")
                        print(f"✅ Page {page_num + 1}: {len(text)} characters")
                    else:
                        print(f"⚠️  Page {page_num + 1}: No text found")
                except Exception as e:
                    print(f"❌ Error on page {page_num + 1}: {e}")
                    continue
        
        full_text = "\n".join(text_content)
        print(f"✅ Total extracted: {len(full_text)} characters")
        return full_text
        
    except Exception as e:
        print(f"❌ Error opening PDF: {e}")
        return ""

def main():
    """Main function."""
    
    print("🔍 Simple PDF Text Extraction Test")
    print("=" * 50)
    
    pdf_path = input("Enter PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        print("No file path provided.")
        return
    
    text = extract_pdf_text(pdf_path)
    
    if text:
        print("\n📖 First 1000 characters:")
        print("-" * 50)
        print(text[:1000])
        print("-" * 50)
        
        # Save to file
        save = input("\n💾 Save full text to file? (y/n): ").strip().lower()
        if save in ['y', 'yes']:
            output_file = Path("extracted_text.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"💾 Text saved to: {output_file.absolute()}")
    else:
        print("❌ No text extracted")

if __name__ == "__main__":
    main()