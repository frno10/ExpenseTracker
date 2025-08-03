import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Debug Supabase configuration
console.log('🗄️ Supabase Configuration:')
console.log('VITE_SUPABASE_URL from env:', import.meta.env.VITE_SUPABASE_URL)
console.log('VITE_SUPABASE_ANON_KEY from env:', import.meta.env.VITE_SUPABASE_ANON_KEY ? '✅ Present' : '❌ Missing')
console.log('supabaseUrl being used:', supabaseUrl)
console.log('supabaseAnonKey being used:', supabaseAnonKey ? '✅ Present' : '❌ Missing')
console.log('Is using fallback URL?', !import.meta.env.VITE_SUPABASE_URL)
console.log('Is using fallback key?', !import.meta.env.VITE_SUPABASE_ANON_KEY)

export const supabase = createClient(supabaseUrl, supabaseAnonKey)