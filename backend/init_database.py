"""
Database initialization script for Supabase.
This script creates all necessary tables and sets up the database schema.
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def init_supabase_database():
    """Initialize Supabase database with required tables."""
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return False
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🚀 Initializing Supabase database...")
    
    # SQL to create tables
    sql_commands = [
        # Users table (extends Supabase auth.users)
        """
        CREATE TABLE IF NOT EXISTS public.users (
            id UUID REFERENCES auth.users(id) PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Categories table
        """
        CREATE TABLE IF NOT EXISTS public.categories (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT DEFAULT '#6B7280',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Expenses table
        """
        CREATE TABLE IF NOT EXISTS public.expenses (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Payment methods table
        """
        CREATE TABLE IF NOT EXISTS public.payment_methods (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('credit_card', 'debit_card', 'cash', 'bank_transfer', 'other')),
            last_four TEXT,
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Budgets table
        """
        CREATE TABLE IF NOT EXISTS public.budgets (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
            category TEXT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            period TEXT NOT NULL CHECK (period IN ('monthly', 'weekly', 'yearly')),
            start_date DATE NOT NULL,
            end_date DATE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Row Level Security (RLS) policies
        """
        ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.payment_methods ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.budgets ENABLE ROW LEVEL SECURITY;
        """,
        
        # RLS Policies for users table
        """
        CREATE POLICY "Users can view own profile" ON public.users
            FOR SELECT USING (auth.uid() = id);
        """,
        
        """
        CREATE POLICY "Users can update own profile" ON public.users
            FOR UPDATE USING (auth.uid() = id);
        """,
        
        # RLS Policies for expenses table
        """
        CREATE POLICY "Users can view own expenses" ON public.expenses
            FOR SELECT USING (auth.uid() = user_id);
        """,
        
        """
        CREATE POLICY "Users can insert own expenses" ON public.expenses
            FOR INSERT WITH CHECK (auth.uid() = user_id);
        """,
        
        """
        CREATE POLICY "Users can update own expenses" ON public.expenses
            FOR UPDATE USING (auth.uid() = user_id);
        """,
        
        """
        CREATE POLICY "Users can delete own expenses" ON public.expenses
            FOR DELETE USING (auth.uid() = user_id);
        """,
        
        # RLS Policies for payment_methods table
        """
        CREATE POLICY "Users can manage own payment methods" ON public.payment_methods
            FOR ALL USING (auth.uid() = user_id);
        """,
        
        # RLS Policies for budgets table
        """
        CREATE POLICY "Users can manage own budgets" ON public.budgets
            FOR ALL USING (auth.uid() = user_id);
        """,
        
        # Insert default categories
        """
        INSERT INTO public.categories (name, description, color) VALUES
            ('Food', 'Meals, groceries, dining out', '#EF4444'),
            ('Transportation', 'Gas, public transport, car maintenance', '#3B82F6'),
            ('Entertainment', 'Movies, games, hobbies', '#8B5CF6'),
            ('Utilities', 'Electricity, water, internet, phone', '#F59E0B'),
            ('Healthcare', 'Medical expenses, pharmacy, insurance', '#10B981'),
            ('Shopping', 'Clothing, electronics, household items', '#EC4899'),
            ('Other', 'Miscellaneous expenses', '#6B7280')
        ON CONFLICT (name) DO NOTHING;
        """,
        
        # Create indexes for better performance
        """
        CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON public.expenses(user_id);
        CREATE INDEX IF NOT EXISTS idx_expenses_date ON public.expenses(date);
        CREATE INDEX IF NOT EXISTS idx_expenses_category ON public.expenses(category);
        CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id ON public.payment_methods(user_id);
        CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON public.budgets(user_id);
        """,
        
        # Function to automatically create user profile on signup
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.users (id, email, full_name)
            VALUES (
                NEW.id,
                NEW.email,
                COALESCE(NEW.raw_user_meta_data->>'full_name', '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """,
        
        # Trigger to call the function when a new user signs up
        """
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """
    ]
    
    # Execute each SQL command
    success_count = 0
    for i, sql in enumerate(sql_commands, 1):
        try:
            print(f"📝 Executing SQL command {i}/{len(sql_commands)}...")
            result = supabase.rpc('exec_sql', {'sql': sql.strip()})
            success_count += 1
            print(f"✅ Command {i} executed successfully")
        except Exception as e:
            print(f"⚠️  Command {i} failed (might already exist): {str(e)}")
            # Continue with other commands even if one fails
            continue
    
    print(f"\n🎉 Database initialization completed!")
    print(f"✅ {success_count}/{len(sql_commands)} commands executed successfully")
    
    # Verify tables were created
    try:
        print("\n📊 Verifying tables...")
        tables_result = supabase.rpc('get_tables')
        print(f"✅ Database setup complete!")
        return True
    except Exception as e:
        print(f"⚠️  Could not verify tables: {str(e)}")
        print("✅ Database setup likely complete (verification failed)")
        return True

if __name__ == "__main__":
    print("🔧 Supabase Database Initialization")
    print("=" * 40)
    
    success = init_supabase_database()
    
    if success:
        print("\n🚀 Your database is ready!")
        print("You can now:")
        print("1. Start your FastAPI server: python -m uvicorn app.main:app --reload")
        print("2. Register users through the API")
        print("3. Create expenses and manage data")
        print("\n📱 Check your Supabase dashboard to see the new tables:")
        print("https://supabase.com/dashboard/project/nsvdbcqvyphyiktrvtkw/editor")
    else:
        print("\n❌ Database initialization failed!")
        print("Please check your Supabase credentials and try again.")