#!/usr/bin/env python3
"""Quick test to verify the Flask app is set up correctly"""
import os
os.environ['FLASK_SKIP_DOTENV'] = '1'

from app import app

print("✅ Flask app imported successfully")
print(f"✅ App has {len(app.url_map._rules)} routes registered")
print("\nAvailable routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")

print("\n" + "="*60)
print("To start the server, run:")
print("  python3 app.py")
print("="*60)

