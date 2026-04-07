"""
One-time migration script to convert existing Excel files to Parquet
Run: python scripts/migrate_existing_files.py
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import UPLOAD_DIR, qdrant_client, collection_name


def convert_excel_to_parquet(excel_path):
    """Convert single Excel file to Parquet with data type handling"""
    try:
        print(f"   📖 Reading: {os.path.basename(excel_path)}")
        
        ext = os.path.splitext(excel_path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(excel_path)
        elif ext == '.csv':
            df = pd.read_csv(excel_path)
        else:
            print(f"   ⏭️  Skipping non-tabular file")
            return None
        
        # ✅ FIX: Convert all columns to string to avoid type conflicts
        # PyArrow Parquet has strict type requirements
        for col in df.columns:
            # Convert mixed-type columns to string
            try:
                # Try to keep numeric columns as numeric
                if df[col].dtype in ['int64', 'float64']:
                    pass  # Keep numeric
                else:
                    # Convert object columns to string (handles mixed types)
                    df[col] = df[col].astype(str)
            except:
                # If conversion fails, force to string
                df[col] = df[col].astype(str)
        
        # ✅ FIX: Ensure column names are strings
        df.columns = df.columns.astype(str)
        
        # Save as Parquet
        parquet_path = excel_path.rsplit('.', 1)[0] + '.parquet'
        
        # Use 'pyarrow' engine with string conversion for problematic columns
        df.to_parquet(
            parquet_path, 
            engine='pyarrow',
            compression='snappy',
            # Allow truncated timestamps and mixed types
            coerce_timestamps='ms',
            allow_truncated_timestamps=True
        )
        
        print(f"   ✅ Saved: {os.path.basename(parquet_path)}")
        print(f"   📊 Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        
        return {
            'parquet_path': parquet_path,
            'row_count': len(df),
            'columns': df.columns.tolist()
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print(f"   💡 Tip: File may have complex formatting - will use fallback at query time")
        return None


def update_qdrant_metadata():
    """Update Qdrant points with parquet_path metadata"""
    
    print("\n🔍 Fetching Qdrant points...")
    
    try:
        offset = None
        updated_count = 0
        total_count = 0
        processed_files = set()  # ✅ Track processed files
        
        while True:
            result, next_offset = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            if not result:
                break
            
            total_count += len(result)
            
            for point in result:
                payload = point.payload
                
                # Skip if already has parquet_path
                if 'parquet_path' in payload:
                    continue
                
                # Get file info
                source = payload.get('source') or payload.get('file_name')
                if not source:
                    continue
                
                # ✅ Skip if already processed (multiple chunks = same file)
                if source in processed_files:
                    continue
                
                processed_files.add(source)  # Mark as processed
                
                # Find original file path
                project_id = payload.get('project_id')
                project_name = payload.get('project_name', 'Unknown')
                
                folder_name = f"{project_id}_{project_name.replace(' ', '_')}"
                file_path = os.path.join(UPLOAD_DIR, folder_name, source)
                
                if not os.path.exists(file_path):
                    continue
                
                # Convert to Parquet
                print(f"\n📄 Processing: {source}")
                result = convert_excel_to_parquet(file_path)
                
                if result:
                    # ✅ Update ALL points for this file (not just one)
                    points_to_update = [
                        p.id for p in result 
                        if p.payload.get('source') == source or p.payload.get('file_name') == source
                    ]
                    
                    if points_to_update:
                        qdrant_client.set_payload(
                            collection_name=collection_name,
                            points=points_to_update,
                            payload={
                                'parquet_path': result['parquet_path'],
                                'row_count': result['row_count'],
                                'columns': result['columns']
                            }
                        )
                        updated_count += 1
                        print(f"   ✅ Updated {len(points_to_update)} Qdrant points for this file")
            
            if next_offset is None:
                break
            
            offset = next_offset
        
        print(f"\n✅ Migration complete!")
        print(f"   Total points: {total_count}")
        print(f"   Files updated: {updated_count}")
        
    except Exception as e:
        print(f"❌ Qdrant update failed: {e}")


def main():
    print("🚀 Starting migration of existing files...\n")
    
    if not os.path.exists(UPLOAD_DIR):
        print(f"❌ Upload directory not found: {UPLOAD_DIR}")
        return
    
    # Option 1: Convert all files in upload directory
    print("📁 Scanning upload directory...")
    converted = 0
    
    for root, dirs, files in os.walk(UPLOAD_DIR):
        for file in files:
            if file.endswith(('.xlsx', '.xls', '.csv')):
                file_path = os.path.join(root, file)
                parquet_path = file_path.rsplit('.', 1)[0] + '.parquet'
                
                # Skip if already exists
                if os.path.exists(parquet_path):
                    print(f"⏭️  Already exists: {file}")
                    continue
                
                print(f"\n📄 {file}")
                result = convert_excel_to_parquet(file_path)
                if result:
                    converted += 1
    
    print(f"\n✅ Converted {converted} files to Parquet")
    
    # Option 2: Update Qdrant metadata
    print("\n" + "="*50)
    update_qdrant_metadata()


if __name__ == "__main__":
    main()
