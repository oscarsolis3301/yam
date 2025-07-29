#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Jarvis AI Training Script - Generate Diverse Q&A Pairs
==============================================================

This enhanced script generates comprehensive Q&A pairs for training Jarvis AI
to handle dental IT support queries. The script is designed to:

1. Separate different question types into different files for better organization
2. Avoid duplicates by checking existing database entries AND AI.html content
3. Generate more diverse and intelligent responses
4. Handle large-scale training without timeouts
5. Provide progress tracking and statistics

Usage:
    python jarvis_enhanced.py [category] [--target-count N] [--batch-size N]

Categories:
    - dental_equipment: Dental equipment troubleshooting
    - software_support: Software support (Epic, Patterson, etc.)
    - network_issues: Network and connectivity issues
    - user_management: User account management
    - office_support: Office-specific information
    - emergency_procedures: Emergency procedures
    - training_onboarding: Training and onboarding
    - security_compliance: Security and compliance
    - hardware_support: Hardware troubleshooting
    - general_it: General IT support
    - all: Generate all categories (default)

Examples:
    python jarvis_enhanced.py dental_equipment --target-count 50000
    python jarvis_enhanced.py all --target-count 1000000 --batch-size 2000
"""

import os
import random
import time
import json
import argparse
import hashlib
import re
from datetime import datetime
from typing import List, Tuple, Dict, Any, Set
import logging
from pathlib import Path

# Import training data modules
try:
    from app.training_data.dental_equipment_qa import get_dental_equipment_qa_pairs
    from app.training_data.software_support_qa import get_software_support_qa_pairs
    from app.training_data.network_issues_qa import get_network_issues_qa_pairs
except ImportError:
    # Fallback if modules not found
    def get_dental_equipment_qa_pairs():
        return []
    def get_software_support_qa_pairs():
        return []
    def get_network_issues_qa_pairs():
        return []

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jarvis_enhanced_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def format_time(seconds):
    """Convert seconds to minutes and seconds format."""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    else:
        return f"{remaining_seconds}s"

# Default configuration
DEFAULT_BATCH_SIZE = 1000
DEFAULT_TARGET_COUNT = 100_000

class EnhancedJarvisTrainer:
    def __init__(self):
        self.current_count = 0
        self.generated_count = 0
        self.duplicate_count = 0
        self.existing_hashes: Set[str] = set()
        self.ai_html_hashes: Set[str] = set()
        
        # Import Flask app and database
        try:
            import sys
            sys.path.append('..')  # Add parent directory to path
            from app.YAM_refactored import app
            from app.extensions import db
            from sqlalchemy import text
            self.app = app
            self.db = db
            self.text = text
            logger.info("Flask app and database imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import Flask app: {e}")
            raise
    
    def get_current_count(self) -> int:
        """Get the current number of Q&A pairs in the database"""
        try:
            with self.app.app_context():
                result = self.db.session.execute(
                    self.text("SELECT COUNT(*) FROM chat_qa")
                ).fetchone()
                count = result[0] if result else 0
                self.current_count = count
                logger.info(f"Current Q&A pairs in database: {count:,}")
                return count
        except Exception as e:
            logger.error(f"Failed to get current count: {e}")
            return 0
    
    def load_existing_hashes(self):
        """Load existing Q&A hashes from database to avoid duplicates"""
        try:
            with self.app.app_context():
                result = self.db.session.execute(
                    self.text("SELECT question, answer FROM chat_qa")
                ).fetchall()
                
                for question, answer in result:
                    # Create hash of normalized question and answer
                    normalized_q = self._normalize_text(question)
                    normalized_a = self._normalize_text(answer)
                    hash_value = hashlib.md5(f"{normalized_q}|{normalized_a}".encode()).hexdigest()
                    self.existing_hashes.add(hash_value)
                
                logger.info(f"Loaded {len(self.existing_hashes):,} existing Q&A hashes from database")
                return True
        except Exception as e:
            logger.error(f"Failed to load existing hashes from database: {e}")
            return False
    
    def load_ai_html_hashes(self):
        """Load existing Q&A hashes from AI.html file to avoid duplicates"""
        try:
            ai_html_path = "app/templates/AI.html"
            if not os.path.exists(ai_html_path):
                logger.warning(f"AI.html file not found at {ai_html_path}")
                return True
            
            with open(ai_html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract Q&A pairs from AI.html
            # Look for common patterns in the HTML
            qa_patterns = [
                r'"([^"]*How do I[^"]*)"',  # Questions starting with "How do I"
                r'"([^"]*How to[^"]*)"',    # Questions starting with "How to"
                r'"([^"]*What should I[^"]*)"',  # Questions starting with "What should I"
                r'"([^"]*Troubleshooting[^"]*)"',  # Questions with "Troubleshooting"
                r'"([^"]*Steps to[^"]*)"',  # Questions with "Steps to"
                r'"([^"]*Guide for[^"]*)"',  # Questions with "Guide for"
            ]
            
            extracted_questions = set()
            for pattern in qa_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                extracted_questions.update(matches)
            
            # Also look for common answer patterns
            answer_patterns = [
                r'To ([^"]*), first check',  # Answers starting with "To"
                r'If you ([^"]*), first verify',  # Answers starting with "If you"
                r'When ([^"]*), start by',  # Answers starting with "When"
                r'For ([^"]*), first check',  # Answers starting with "For"
            ]
            
            extracted_answers = set()
            for pattern in answer_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                extracted_answers.update(matches)
            
            # Create hashes for extracted Q&A pairs
            for question in extracted_questions:
                if len(question) > 10:  # Only consider substantial questions
                    normalized_q = self._normalize_text(question)
                    # Create a hash for the question alone
                    hash_value = hashlib.md5(f"{normalized_q}|".encode()).hexdigest()
                    self.ai_html_hashes.add(hash_value)
            
            for answer in extracted_answers:
                if len(answer) > 20:  # Only consider substantial answers
                    normalized_a = self._normalize_text(answer)
                    # Create a hash for the answer alone
                    hash_value = hashlib.md5(f"|{normalized_a}".encode()).hexdigest()
                    self.ai_html_hashes.add(hash_value)
            
            logger.info(f"Loaded {len(self.ai_html_hashes):,} Q&A hashes from AI.html")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load AI.html hashes: {e}")
            return False
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for duplicate detection"""
        return text.lower().strip()
    
    def is_duplicate(self, question: str, answer: str) -> bool:
        """Check if Q&A pair already exists in database or AI.html"""
        normalized_q = self._normalize_text(question)
        normalized_a = self._normalize_text(answer)
        
        # Check database hashes
        hash_value = hashlib.md5(f"{normalized_q}|{normalized_a}".encode()).hexdigest()
        if hash_value in self.existing_hashes:
            return True
        
        # Check AI.html hashes (partial matches)
        question_hash = hashlib.md5(f"{normalized_q}|".encode()).hexdigest()
        answer_hash = hashlib.md5(f"|{normalized_a}".encode()).hexdigest()
        
        if question_hash in self.ai_html_hashes or answer_hash in self.ai_html_hashes:
            return True
        
        # Additional similarity check for AI.html content
        for ai_hash in self.ai_html_hashes:
            # Simple similarity check - if question or answer contains similar content
            if normalized_q in ai_hash or normalized_a in ai_hash:
                return True
        
        return False
    
    def ensure_table_exists(self):
        """Ensure the chat_qa table exists with proper structure"""
        try:
            with self.app.app_context():
                # Create table if it doesn't exist
                self.db.session.execute(
                    self.text("""
                        CREATE TABLE IF NOT EXISTS chat_qa (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user TEXT NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            question TEXT NOT NULL,
                            answer TEXT NOT NULL,
                            image_path TEXT,
                            image_caption TEXT,
                            embedding BLOB
                        )
                    """)
                )
                
                # Create indexes for better performance
                self.db.session.execute(
                    self.text("""
                        CREATE INDEX IF NOT EXISTS idx_chatqa_question 
                        ON chat_qa (lower(question))
                    """)
                )
                
                self.db.session.execute(
                    self.text("""
                        CREATE INDEX IF NOT EXISTS idx_chatqa_user 
                        ON chat_qa (user)
                    """)
                )
                
                self.db.session.commit()
                logger.info("Database table structure verified")
                return True
        except Exception as e:
            logger.error(f"Failed to ensure table exists: {e}")
            return False
    
    def insert_qa_batch(self, qa_pairs: List[Tuple[str, str, str]]) -> int:
        """Insert a batch of Q&A pairs into the database, return number inserted"""
        if not qa_pairs:
            return 0
            
        try:
            with self.app.app_context():
                # Filter out duplicates
                unique_pairs = []
                for user, question, answer in qa_pairs:
                    if not self.is_duplicate(question, answer):
                        unique_pairs.append((user, question, answer))
                    else:
                        self.duplicate_count += 1
                
                if not unique_pairs:
                    logger.info("All Q&A pairs in batch were duplicates")
                    return 0
                
                # Prepare the insert statement
                insert_sql = """
                    INSERT INTO chat_qa (user, question, answer, timestamp)
                    VALUES (:user, :question, :answer, datetime('now'))
                """
                
                # Execute batch insert
                for user, question, answer in unique_pairs:
                    self.db.session.execute(
                        self.text(insert_sql),
                        {
                            'user': user,
                            'question': question,
                            'answer': answer
                        }
                    )
                
                self.db.session.commit()
                
                # Add new hashes to existing set
                for user, question, answer in unique_pairs:
                    normalized_q = self._normalize_text(question)
                    normalized_a = self._normalize_text(answer)
                    hash_value = hashlib.md5(f"{normalized_q}|{normalized_a}".encode()).hexdigest()
                    self.existing_hashes.add(hash_value)
                
                self.generated_count += len(unique_pairs)
                logger.info(f"Inserted {len(unique_pairs)} unique Q&A pairs (skipped {len(qa_pairs) - len(unique_pairs)} duplicates). Total generated: {self.generated_count:,}")
                
                return len(unique_pairs)
        except Exception as e:
            logger.error(f"Failed to insert batch: {e}")
            with self.app.app_context():
                self.db.session.rollback()
            return 0

def get_qa_pairs_for_category(category: str, target_count: int) -> List[Tuple[str, str, str]]:
    """Get Q&A pairs for a specific category"""
    
    if category == "dental_equipment":
        qa_pairs = get_dental_equipment_qa_pairs()
    elif category == "software_support":
        qa_pairs = get_software_support_qa_pairs()
    elif category == "network_issues":
        qa_pairs = get_network_issues_qa_pairs()
    elif category == "all":
        # Combine all categories
        qa_pairs = []
        qa_pairs.extend(get_dental_equipment_qa_pairs())
        qa_pairs.extend(get_software_support_qa_pairs())
        qa_pairs.extend(get_network_issues_qa_pairs())
    else:
        # Default to dental equipment
        qa_pairs = get_dental_equipment_qa_pairs()
    
    # Limit to target count
    if len(qa_pairs) > target_count:
        qa_pairs = qa_pairs[:target_count]
    
    return qa_pairs

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Enhanced Jarvis AI Training Script")
    parser.add_argument("category", nargs="?", default="all", 
                       choices=["dental_equipment", "software_support", "network_issues", 
                               "user_management", "office_support", "emergency_procedures", 
                               "training_onboarding", "security_compliance", "hardware_support", 
                               "general_it", "all"],
                       help="Category of Q&A pairs to generate")
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT,
                       help=f"Target number of Q&A pairs to generate (default: {DEFAULT_TARGET_COUNT:,})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                       help=f"Batch size for database inserts (default: {DEFAULT_BATCH_SIZE})")
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = EnhancedJarvisTrainer()
    
    try:
        # Ensure table exists
        if not trainer.ensure_table_exists():
            return False
        
        # Load existing hashes from database
        if not trainer.load_existing_hashes():
            return False
        
        # Load existing hashes from AI.html
        if not trainer.load_ai_html_hashes():
            return False
        
        # Get current count
        current_count = trainer.get_current_count()
        needed_count = args.target_count
        
        logger.info(f"Starting training for category: {args.category}")
        logger.info(f"Target count: {needed_count:,}")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Existing database entries: {current_count:,}")
        logger.info(f"AI.html hashes loaded: {len(trainer.ai_html_hashes):,}")
        
        # Generate Q&A pairs
        start_time = time.time()
        
        qa_pairs = get_qa_pairs_for_category(args.category, needed_count)
        logger.info(f"Generated {len(qa_pairs):,} Q&A pairs")
        
        # Insert in batches
        batch_count = 0
        total_inserted = 0
        
        for i in range(0, len(qa_pairs), args.batch_size):
            batch = qa_pairs[i:i + args.batch_size]
            inserted = trainer.insert_qa_batch(batch)
            total_inserted += inserted
            batch_count += 1
            
            # Progress update
            progress = (i + len(batch)) / len(qa_pairs) * 100
            elapsed = time.time() - start_time
            eta = (elapsed / (i + len(batch))) * (len(qa_pairs) - i - len(batch)) if i + len(batch) > 0 else 0
            
            logger.info(f"Progress: {progress:.1f}% ({i + len(batch):,}/{len(qa_pairs):,}) - Inserted: {total_inserted:,} - ETA: {format_time(eta)}")
            
            if inserted == 0 and len(batch) > 0:
                logger.warning(f"Batch {batch_count} had no new unique entries")
        
        # Final statistics
        final_count = trainer.get_current_count()
        total_time = time.time() - start_time
        
        logger.info(f"Training completed!")
        logger.info(f"Category: {args.category}")
        logger.info(f"Total Q&A pairs in database: {final_count:,}")
        logger.info(f"New Q&A pairs inserted: {total_inserted:,}")
        logger.info(f"Duplicates skipped: {trainer.duplicate_count:,}")
        logger.info(f"Total time: {format_time(total_time)}")
        logger.info(f"Average speed: {total_inserted/total_time:.0f} Q&A pairs per second")
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error during training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 