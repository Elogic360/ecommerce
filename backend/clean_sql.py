import re
import sys

def clean_sql(input_file, output_file):
    print(f"🧹 Cleaning SQL file: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    path_cleanup = [
        r'^\\.*$',                     # Lines starting with \ (psql meta-commands)
        r'^ALTER\s+.*\s+OWNER\s+TO\s+.*;', # ALTER ... OWNER TO ...;
        r'^COMMENT\s+ON\s+EXTENSION\s+.*;', # Extension comments often have owner issues
        r'^SELECT\s+pg_catalog\.set_config\(\'search_path\'.*$', # Search path locks
        r'^ALTER\s+DEFAULT\s+PRIVILEGES\s+.*;', # Render doesn't allow changing default privileges
        r'^GRANT\s+.*;', # Individual grants can fail if source role is missing
        r'^REVOKE\s+.*;', # Same for revokes
    ]

    cleaned_lines = []
    for line in lines:
        skip = False
        # Skip psql meta commands and owner changes
        for pattern in path_cleanup:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                skip = True
                break
        
        if not skip:
            # Replace old username with the new one
            line = line.replace('ecommerce_user', 'neatify_user')
            
            # Inline replacement for any remaining OWNER TO patterns that weren't caught by line start
            line = re.sub(r'OWNER\s+TO\s+[^;]+', '', line, flags=re.IGNORECASE)
            
            # Remove any trailing empty ALTER commands that might have been mangled
            if line.strip().upper() in ["ALTER SCHEMA PUBLIC ;", "ALTER SCHEMA PUBLIC"]:
                continue
            cleaned_lines.append(line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print(f"✅ Cleaned SQL saved to: {output_file}")

if __name__ == "__main__":
    clean_sql('database_schema02.sql', 'schema_production.sql')
