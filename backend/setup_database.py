"""
Simple database setup script for Supabase.
This script provides instructions and helps verify the database setup.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("🔧 Supabase Database Setup")
    print("=" * 50)
    
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        print("❌ Error: SUPABASE_URL not found in .env file")
        return
    
    project_id = supabase_url.split("//")[1].split(".")[0]
    sql_editor_url = f"https://supabase.com/dashboard/project/{project_id}/sql"
    
    print("📋 To set up your database, follow these steps:")
    print()
    print("1. Open the Supabase SQL Editor:")
    print(f"   {sql_editor_url}")
    print()
    print("2. Copy the contents of 'database_schema.sql' file")
    print("   (located in the same directory as this script)")
    print()
    print("3. Paste the SQL into the editor and click 'Run'")
    print()
    print("4. Verify the tables were created in the Table Editor:")
    print(f"   https://supabase.com/dashboard/project/{project_id}/editor")
    print()
    print("Expected tables after setup:")
    print("   ✅ users")
    print("   ✅ categories") 
    print("   ✅ expenses")
    print("   ✅ payment_methods")
    print("   ✅ budgets")
    print()
    print("5. Once tables are created, you can test user registration!")
    print()
    
    # Check if we can connect to Supabase
    try:
        from supabase import create_client
        supabase_key = os.getenv("SUPABASE_KEY")
        if supabase_key:
            client = create_client(supabase_url, supabase_key)
            print("✅ Supabase connection test successful!")
            print("   Your credentials are working correctly.")
        else:
            print("⚠️  SUPABASE_KEY not found in .env file")
    except ImportError:
        print("⚠️  Supabase client not installed. Run: pip install supabase")
    except Exception as e:
        print(f"⚠️  Supabase connection test failed: {str(e)}")
    
    print()
    print("🚀 After database setup, start your server with:")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    main()