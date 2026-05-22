import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from src.calculator import AdvancedCalculator
    print("Import successful!")
    calc = AdvancedCalculator()
    print("Class instantiated.")
except Exception as e:
    print(f"Import failed: {e}")
