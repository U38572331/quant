
import os
import re
import sys
import typing

# Path to openbb package in site-packages
# I will derive it from sys.path or use hardcoded path based on previous tools
# Hardcoded path for this environment:
SITE_PACKAGES = r"C:\Users\user\AppData\Local\pypoetry\Cache\virtualenvs\openbb-GnnGhCRn-py3.13\Lib\site-packages"
OPENBB_PKG_DIR = os.path.join(SITE_PACKAGES, "openbb", "package")

print(f"Scanning {OPENBB_PKG_DIR}...")

def patch_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex to find 'from typing import (...)' blocks
    # This is a bit brittle but should work for the generated code style
    pattern = re.compile(r"from typing import \((.*?)\)", re.DOTALL)
    
    def replacer(match):
        block = match.group(0)
        inner = match.group(1)
        # Split by comma and strip
        names = [n.strip().replace(',', '') for n in inner.split() if n.strip() and n.strip() != ',']
        
        valid_imports = []
        invalid_imports = []
        
        for name in names:
            if hasattr(typing, name):
                valid_imports.append(name)
            else:
                invalid_imports.append(name)
        
        if not invalid_imports:
            return block
        
        # Reconstruct valid import
        new_block = ""
        if valid_imports:
            new_block += "from typing import (\n"
            for name in valid_imports:
                new_block += f"    {name},\n"
            new_block += ")\n"
        
        # Add fix for invalid imports
        new_block += "\n# Fixed invalid imports\n"
        if "Any" not in valid_imports and "Any" not in names: # Check if Any is available
             new_block += "from typing import Any\n"
             
        for name in invalid_imports:
            new_block += f"{name} = Any\n"
            print(f"  Fixed {name} in {os.path.basename(filepath)}")
            
        return new_block

    new_content = pattern.sub(replacer, content)

    # Also match single line: from typing import Foo, Bar (without parens)
    # Be careful not to match 'import typing' or other things
    # Regex: ^from typing import ([^(\n]+)$ (multiline)
    pattern_single = re.compile(r"^from typing import ([^(\n#]+)", re.MULTILINE)
    
    def replacer_single(match):
        raw_names = match.group(1)
        names = [n.strip().replace(',', '') for n in raw_names.split() if n.strip() and n.strip() != ',']
        
        valid_imports = []
        invalid_imports = []
        
        for name in names:
            if hasattr(typing, name):
                valid_imports.append(name)
            else:
                invalid_imports.append(name)
        
        if not invalid_imports:
            return match.group(0)
            
        new_block = ""
        if valid_imports:
             new_block += f"from typing import {', '.join(valid_imports)}\n"
        
        # Add fix for invalid imports
        if "Any" not in valid_imports and "Any" not in names:
             new_block += "from typing import Any\n"
             
        for name in invalid_imports:
            new_block += f"{name} = Any\n"
            print(f"  Fixed single-line {name} in {os.path.basename(filepath)}")
            
        return new_block.strip() # strip trailing newline from block reconstruction if needed

    new_content = pattern_single.sub(replacer_single, new_content)

    
    # Also handle single line imports? The generator seems to use parens for multiple, but maybe single line too?
    # e.g. from typing import List
    # But usually problematic ones are models which are multiple.
    
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False

count = 0
for root, dirs, files in os.walk(OPENBB_PKG_DIR):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            if patch_file(path):
                count += 1

print(f"Patched {count} files.")
