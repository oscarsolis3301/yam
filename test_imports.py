#!/usr/bin/env python3
"""
Test script to verify imports work correctly
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    print("✅ Successfully imported create_app")
    
    from app.models.base import TicketClosure, FreshworksUserMapping, User, TicketSyncMetadata
    print("✅ Successfully imported models")
    
    from app.extensions import db
    print("✅ Successfully imported db")
    
    from app.utils.freshworks_service import freshworks_service
    print("✅ Successfully imported freshworks_service")
    
    print("\n🎉 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
except Exception as e:
    print(f"❌ Unexpected error: {e}") 