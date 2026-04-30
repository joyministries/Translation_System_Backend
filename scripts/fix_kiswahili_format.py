#!/usr/bin/env python3
"""Fix formatting for all Kiswahili translations in the database."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.translation_format_fixer import fix_all_translations_for_language

def main():
    """Fix all Kiswahili translations (language_id=1)."""
    db = SessionLocal()
    
    try:
        print("Fixing Kiswahili translations (language_id=1)...")
        result = fix_all_translations_for_language(db, language_id=1)
        
        print(f"\nResults:")
        print(f"  Total translations: {result['total']}")
        print(f"  Fixed: {result['fixed']}")
        print(f"  Errors: {result['errors']}")
        
        if result['details']:
            print(f"\nDetails:")
            for detail in result['details']:
                if 'error' in detail:
                    print(f"  - {detail['translation_id']}: ERROR - {detail['error']}")
                else:
                    print(f"  - {detail['translation_id']} ({detail['content_type']}): {detail['reduction_percent']}% reduction")
        
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
