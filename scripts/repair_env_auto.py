
import os
import re

def repair():
    env_path = '.env'
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Extract password again
    # Current format might be the one we just wrote: postgresql://postgres.fiejpifwokyteprirvqp:[PASSWORD]@aws-0...
    # Or original: postgresql://postgres:[PASSWORD]@...
    
    # Generic regex for password: between '://' and '@' -> split by ':'
    # postgresql://USER:PASSWORD@HOST...
    
    match = re.search(r'postgresql://[^:]+:([^@]+)@', content)
    if match:
        password = match.group(1)
        print(f"Found password (length: {len(password)})")
        
        project_ref = "fiejpifwokyteprirvqp"
        
        # New URL: direct host, port 6543, user with project ref
        # Note: If password has special chars, they should be urlencoded, but we preserve what was there.
        new_url = f"postgresql://postgres.{project_ref}:{password}@db.{project_ref}.supabase.co:6543/postgres"
        
        new_content = re.sub(
            r'DATABASE_URL=.*',
            f'DATABASE_URL={new_url}',
            content
        )
        
        with open(env_path, 'w') as f:
            f.write(new_content)
            
        print("SUCCESS: .env updated to Direct Host + Port 6543")
        print(f"New URL: ...@db.{project_ref}.supabase.co:6543/postgres")
        
    else:
        print("Error: Could not extract password from current file")

if __name__ == "__main__":
    repair()
