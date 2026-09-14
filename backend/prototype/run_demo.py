# run_demo.py - Quick test for the COBOL to OOP modernization mockup
from src.refactorer import OOPRefactorer

print("🚀 ML-Driven Legacy Code Modernization - Quick Demo\n")

refactorer = OOPRefactorer()

# Test on the main example
python_code = refactorer.refactor('data/simple_account.cbl')

print("=== GENERATED PYTHON OOP CODE ===\n")
print(python_code)

# Save with proper UTF-8 encoding
with open('output/output_refactored_account .py', 'w', encoding='utf-8') as f:
    f.write(python_code)

print("\n✅ Successfully saved to: output/output_refactored_account .py")
print("You can now open this file in any editor (VS Code recommended).")