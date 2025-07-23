#!/usr/bin/env python3
"""
Run Training Test
================

This script runs a small test of the enhanced training system to verify
it works correctly with the database.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run a small training test"""
    print("Enhanced Jarvis Training Test")
    print("=" * 40)
    
    try:
        # Import the enhanced trainer
        from jarvis_enhanced import main as run_training
        
        # Set up command line arguments for a small test
        sys.argv = [
            'jarvis_enhanced.py',
            'dental_equipment',  # Test with dental equipment category
            '--target-count', '1000',  # Small number for testing
            '--batch-size', '100'  # Small batch size for testing
        ]
        
        print("Running training test with:")
        print(f"Category: dental_equipment")
        print(f"Target count: 1,000")
        print(f"Batch size: 100")
        print()
        
        # Run the training
        success = run_training()
        
        if success:
            print("\n✅ Training test completed successfully!")
            print("The enhanced training system is working correctly.")
        else:
            print("\n❌ Training test failed!")
            print("Check the logs for error details.")
            
    except Exception as e:
        print(f"\n❌ Error during training test: {e}")
        print("Check the configuration and database setup.")

if __name__ == "__main__":
    main() 