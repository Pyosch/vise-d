"""Script to fix indentation in networks_excel.py"""
import re

# Read the file
with open(r'f:\Streamlit_Project_new\vise-d\src\pages\networks_excel.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line where we need to start fixing indentation
# After "with tab1:" we need to reduce indentation by 4 spaces
fixed_lines = []
inside_fix_zone = False
tab_level = 0

for i, line in enumerate(lines):
    # Check if we're at the start of a tab block that needs fixing
    if '                with tab' in line and ':' in line:
        inside_fix_zone = True
        fixed_lines.append(line)
        continue
    
    # Check if we're exiting the problematic zone (going back to lower indentation)
    if inside_fix_zone:
        # If line starts with less than 20 spaces and is not empty/comment, we've exited
        if line.strip() and not line.startswith('                    '):
            inside_fix_zone = False
        elif line.startswith('                        '):  # 24 spaces
            # Remove 4 spaces
            line = line[4:]
    
    fixed_lines.append(line)

# Write back
with open(r'f:\Streamlit_Project_new\vise-d\src\pages\networks_excel.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Indentation fixed!")
