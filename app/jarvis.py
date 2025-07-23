#!/usr/bin/env python3
"""
Jarvis AI Training Script - Generate 1 Million Q&A Pairs
=======================================================

This script generates a comprehensive dataset of 1 million Q&A pairs for training
Jarvis AI to handle dental IT support queries. The dataset covers:

- Dental equipment troubleshooting
- Software support (Epic, Patterson, etc.)
- Network and connectivity issues
- User account management
- Office-specific information
- IT procedures and policies
- Emergency procedures
- Training and onboarding

Usage:
    python train_jarvis_million.py

The script will:
1. Check the current database state
2. Generate diverse Q&A pairs using templates and variations
3. Insert them into the chat_qa.db database
4. Provide progress updates and statistics
"""

import sqlite3
import os
import random
import time
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jarvis_training.log'),
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

# Database configuration
DB_PATH = "db/chat_qa.db"
BATCH_SIZE = 1000  # Insert in batches for better performance
TARGET_COUNT = 1_000_000

class JarvisTrainer:
    def __init__(self):
        self.db_path = DB_PATH
        self.current_count = 0
        self.generated_count = 0
        self.conn = None
        self.cursor = None
        
    def connect_db(self):
        """Connect to the SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def get_current_count(self) -> int:
        """Get the current number of Q&A pairs in the database"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM chat_qa")
            count = self.cursor.fetchone()[0]
            self.current_count = count
            logger.info(f"Current Q&A pairs in database: {count:,}")
            return count
        except Exception as e:
            logger.error(f"Failed to get current count: {e}")
            return 0
    
    def ensure_table_exists(self):
        """Ensure the chat_qa table exists with proper structure"""
        try:
            self.cursor.execute("""
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
            
            # Create index for better performance
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chatqa_question 
                ON chat_qa (lower(question))
            """)
            
            self.conn.commit()
            logger.info("Database table structure verified")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure table exists: {e}")
            return False
    
    def insert_qa_batch(self, qa_pairs: List[Tuple[str, str, str]]):
        """Insert a batch of Q&A pairs into the database"""
        try:
            # Prepare the insert statement
            insert_sql = """
                INSERT INTO chat_qa (user, question, answer, timestamp)
                VALUES (?, ?, ?, datetime('now'))
            """
            
            # Execute batch insert
            self.cursor.executemany(insert_sql, qa_pairs)
            self.conn.commit()
            
            self.generated_count += len(qa_pairs)
            logger.info(f"Inserted batch of {len(qa_pairs)} Q&A pairs. Total generated: {self.generated_count:,}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to insert batch: {e}")
            self.conn.rollback()
            return False
    
    def generate_qa_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate comprehensive Q&A templates for dental IT support"""
        
        templates = {
            "dental_equipment": [
                {
                    "questions": [
                        "How do I troubleshoot {equipment} issues?",
                        "What should I do if {equipment} is not working?",
                        "How to fix {equipment} problems?",
                        "Troubleshooting guide for {equipment}",
                        "Common {equipment} issues and solutions"
                    ],
                    "equipment": [
                        "Cerec machine", "X-ray machine", "intraoral scanner", 
                        "dental chair", "autoclave", "compressor", "vacuum system",
                        "dental handpiece", "curing light", "ultrasonic scaler"
                    ],
                    "answers": [
                        "For {equipment} issues, first check the power connection and ensure all cables are properly connected. Restart the device and check for any error messages on the display. If the problem persists, contact IT support at 1-800-IT-HELP or submit a ticket through the help desk portal.",
                        "When {equipment} is not working, verify that all connections are secure and the device is receiving power. Check the user manual for troubleshooting steps. If basic troubleshooting doesn't resolve the issue, escalate to the IT support team.",
                        "To fix {equipment} problems, start by identifying the specific error or issue. Check the device's status indicators and error codes. Follow the manufacturer's troubleshooting guide. If unable to resolve, contact technical support.",
                        "The troubleshooting guide for {equipment} includes checking power supply, connections, and error codes. Refer to the device manual for specific procedures. For complex issues, contact the IT department.",
                        "Common {equipment} issues include power problems, connection errors, and calibration issues. Most can be resolved by checking connections and restarting the device. For persistent issues, contact support."
                    ]
                }
            ],
            
            "software_support": [
                {
                    "questions": [
                        "How do I access {software}?",
                        "I can't log into {software}, what should I do?",
                        "How to reset {software} password?",
                        "Troubleshooting {software} login issues",
                        "How to navigate {software} interface?"
                    ],
                    "software": [
                        "Epic", "Patterson Eaglesoft", "Dentrix", "PracticeWorks",
                        "Open Dental", "Carestream", "Sirona Connect", "Cerec Connect",
                        "JAMF", "Active Directory", "Office 365", "VPN"
                    ],
                    "answers": [
                        "To access {software}, open your web browser and navigate to the login page. Use your assigned username and password. If you don't have credentials, contact your office manager or IT support.",
                        "If you can't log into {software}, first verify your username and password are correct. Check if Caps Lock is on. If the issue persists, try resetting your password or contact IT support.",
                        "To reset your {software} password, click the 'Forgot Password' link on the login page. Follow the prompts to verify your identity and create a new password. If you need assistance, contact IT support.",
                        "For {software} login issues, check your internet connection and ensure the service is available. Clear your browser cache and cookies. If problems continue, contact the IT help desk.",
                        "To navigate the {software} interface, start with the main dashboard. Use the menu bar to access different modules. Refer to the user manual or contact training support for detailed guidance."
                    ]
                }
            ],
            
            "network_issues": [
                {
                    "questions": [
                        "How to fix {network_issue}?",
                        "What causes {network_issue}?",
                        "Troubleshooting {network_issue}",
                        "How to resolve {network_issue}?",
                        "Steps to fix {network_issue}"
                    ],
                    "network_issue": [
                        "slow internet", "WiFi connection problems", "network connectivity issues",
                        "VPN connection errors", "printer network issues", "file sharing problems",
                        "email connectivity", "cloud service access", "remote desktop issues"
                    ],
                    "answers": [
                        "To fix {network_issue}, first restart your router and modem. Check all cable connections. If the problem persists, contact your internet service provider or IT support for assistance.",
                        "{network_issue} can be caused by hardware failures, configuration problems, or service outages. Check your equipment and contact IT support if needed.",
                        "When troubleshooting {network_issue}, start by checking your device's network settings. Verify connections and restart networking equipment. Contact IT support for advanced troubleshooting.",
                        "To resolve {network_issue}, identify the root cause by checking network status and equipment. Follow troubleshooting guides or contact technical support for assistance.",
                        "Steps to fix {network_issue} include checking connections, restarting equipment, and verifying settings. If basic steps don't work, escalate to IT support."
                    ]
                }
            ],
            
            "user_management": [
                {
                    "questions": [
                        "How to {user_action}?",
                        "What is the process for {user_action}?",
                        "Steps to {user_action}",
                        "How do I {user_action}?",
                        "Procedure for {user_action}"
                    ],
                    "user_action": [
                        "create a new user account", "reset a password", "disable a user account",
                        "change user permissions", "add user to group", "remove user from group",
                        "unlock a locked account", "update user information", "transfer user data"
                    ],
                    "answers": [
                        "To {user_action}, log into the admin portal with appropriate permissions. Navigate to the user management section and follow the step-by-step process. Contact IT support if you need assistance.",
                        "The process for {user_action} requires administrative access. Follow the documented procedures in the IT knowledge base. Ensure proper authorization before making changes.",
                        "Steps to {user_action} include accessing the admin interface, locating the user, and following the specific procedure. Always verify changes and document actions taken.",
                        "To {user_action}, you need appropriate permissions. Access the user management system and follow the guided process. Contact IT support for complex scenarios.",
                        "The procedure for {user_action} involves several steps including verification, authorization, and documentation. Follow the standard operating procedures and contact support if needed."
                    ]
                }
            ],
            
            "office_support": [
                {
                    "questions": [
                        "How to {office_task} at {office_location}?",
                        "What are the {office_location} office hours?",
                        "How to contact {office_location} IT support?",
                        "Equipment available at {office_location}",
                        "Network setup at {office_location}"
                    ],
                    "office_location": [
                        "Pacific Dental Services", "PDS office", "dental practice", "clinic",
                        "main office", "branch office", "satellite location", "remote office"
                    ],
                    "office_task": [
                        "set up new equipment", "configure network", "install software",
                        "access shared resources", "connect to printers", "use conference room tech",
                        "access patient records", "use backup systems"
                    ],
                    "answers": [
                        "To {office_task} at {office_location}, contact the local IT support team. They will guide you through the process and ensure proper setup and configuration.",
                        "The {office_location} office hours are typically 8 AM to 5 PM Monday through Friday. Emergency IT support is available 24/7 for critical issues.",
                        "To contact {office_location} IT support, call the help desk at 1-800-IT-HELP or submit a ticket through the online portal. Include your office location in the request.",
                        "Equipment available at {office_location} includes computers, printers, scanners, and specialized dental equipment. Contact IT support for a complete inventory or to request additional equipment.",
                        "The network setup at {office_location} includes secure WiFi, wired connections, and VPN access. Contact IT support for network configuration or troubleshooting assistance."
                    ]
                }
            ],
            
            "emergency_procedures": [
                {
                    "questions": [
                        "What to do during {emergency_type}?",
                        "Emergency procedure for {emergency_type}",
                        "How to handle {emergency_type}?",
                        "Steps during {emergency_type}",
                        "Emergency response for {emergency_type}"
                    ],
                    "emergency_type": [
                        "system outage", "data breach", "equipment failure", "network down",
                        "power outage", "security incident", "patient data loss", "backup failure"
                    ],
                    "answers": [
                        "During {emergency_type}, immediately contact IT support at the emergency hotline. Follow the emergency response procedures and document all actions taken. Ensure patient safety and data protection.",
                        "The emergency procedure for {emergency_type} involves immediate notification of IT support, assessment of impact, and implementation of contingency plans. Follow the documented emergency response protocol.",
                        "To handle {emergency_type}, stay calm and follow the emergency procedures. Contact the appropriate support team immediately and document all incidents for post-emergency review.",
                        "Steps during {emergency_type} include immediate assessment, notification of support teams, implementation of backup procedures, and communication with affected users.",
                        "Emergency response for {emergency_type} requires immediate action, proper communication, and following established protocols. Contact emergency IT support and follow their guidance."
                    ]
                }
            ],
            
            "training_and_onboarding": [
                {
                    "questions": [
                        "How to {training_action}?",
                        "Training resources for {training_topic}",
                        "How to learn {training_topic}?",
                        "Onboarding process for {training_topic}",
                        "Training schedule for {training_topic}"
                    ],
                    "training_action": [
                        "access training materials", "complete required training", "schedule training session",
                        "find training resources", "request additional training", "access online courses"
                    ],
                    "training_topic": [
                        "new software", "dental equipment", "IT procedures", "security protocols",
                        "patient management systems", "compliance requirements", "emergency procedures"
                    ],
                    "answers": [
                        "To {training_action}, log into the training portal and navigate to the appropriate section. Follow the instructions and complete all required modules. Contact training support if you need assistance.",
                        "Training resources for {training_topic} are available in the learning management system. Access includes video tutorials, documentation, and hands-on practice sessions.",
                        "To learn {training_topic}, start with the basic training modules and progress through advanced topics. Practice in the training environment and seek help from mentors or support teams.",
                        "The onboarding process for {training_topic} includes orientation, basic training, and hands-on practice. Follow the structured program and complete all required assessments.",
                        "Training schedule for {training_topic} is available in the training calendar. Sessions are offered regularly and can be scheduled based on your availability and role requirements."
                    ]
                }
            ]
        }
        
        return templates
    
    def generate_qa_variations(self, templates: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[str, str, str]]:
        """Generate Q&A variations from templates"""
        qa_pairs = []
        
        # Question variations to make them more natural
        question_variations = [
            "How do I {placeholder}?",
            "What's the best way to {placeholder}?",
            "Can you help me with {placeholder}?",
            "I need help with {placeholder}",
            "What should I do about {placeholder}?",
            "How to {placeholder}?",
            "Steps for {placeholder}",
            "Guide for {placeholder}",
            "Help with {placeholder}",
            "Troubleshooting {placeholder}"
        ]
        
        # Answer variations to make responses more helpful
        answer_prefixes = [
            "Here's how to handle this: ",
            "The solution is: ",
            "You can resolve this by: ",
            "Try these steps: ",
            "Here's what you need to do: ",
            "The process involves: ",
            "Follow this approach: ",
            "Here's the recommended solution: ",
            "You should: ",
            "The best approach is: "
        ]
        
        answer_suffixes = [
            " If you need further assistance, contact IT support.",
            " Don't hesitate to reach out to the help desk if you encounter issues.",
            " For additional help, submit a ticket through the support portal.",
            " Contact your IT team if you need more detailed guidance.",
            " Reach out to technical support for complex scenarios.",
            " The IT support team is available to help with any questions.",
            " For advanced troubleshooting, contact the help desk.",
            " IT support can provide additional assistance if needed.",
            " Don't hesitate to ask for help from the support team.",
            " The technical team is ready to assist with any issues."
        ]
        
        for category, category_templates in templates.items():
            for template in category_templates:
                questions = template.get("questions", [])
                answers = template.get("answers", [])
                
                # Get dynamic placeholders
                placeholders = {}
                for key, value in template.items():
                    if key not in ["questions", "answers"] and isinstance(value, list):
                        placeholders[key] = value
                
                # Generate combinations
                for question_template in questions:
                    for answer_template in answers:
                        # Generate variations for each placeholder
                        placeholder_combinations = self._generate_placeholder_combinations(placeholders)
                        
                        for combo in placeholder_combinations:
                            # Fill in the question template
                            question = question_template
                            for placeholder, value in combo.items():
                                question = question.replace(f"{{{placeholder}}}", value)
                            
                            # Fill in the answer template
                            answer = answer_template
                            for placeholder, value in combo.items():
                                answer = answer.replace(f"{{{placeholder}}}", value)
                            
                            # Add variations
                            for q_var in question_variations:
                                for a_prefix in answer_prefixes:
                                    for a_suffix in answer_suffixes:
                                        # Create variation of question
                                        var_question = q_var.replace("{placeholder}", question.lower())
                                        
                                        # Create variation of answer
                                        var_answer = a_prefix + answer + a_suffix
                                        
                                        qa_pairs.append(("jarvis_trainer", var_question, var_answer))
                                        
                                        # Limit to prevent excessive generation
                                        if len(qa_pairs) >= TARGET_COUNT:
                                            return qa_pairs
        
        return qa_pairs
    
    def _generate_placeholder_combinations(self, placeholders: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Generate combinations of placeholder values"""
        combinations = []
        
        # Get all placeholder keys
        keys = list(placeholders.keys())
        if not keys:
            return [{}]
        
        # Generate combinations
        def generate_combos(index, current_combo):
            if index >= len(keys):
                combinations.append(current_combo.copy())
                return
            
            key = keys[index]
            values = placeholders[key]
            
            for value in values:
                current_combo[key] = value
                generate_combos(index + 1, current_combo)
        
        generate_combos(0, {})
        return combinations
    
    def generate_additional_qa_pairs(self) -> List[Tuple[str, str, str]]:
        """Generate additional Q&A pairs to reach the target count"""
        additional_pairs = []
        
        # General IT support questions
        general_questions = [
            "How do I restart my computer?",
            "What is my IP address?",
            "How to check disk space?",
            "How to update software?",
            "How to backup files?",
            "How to install printer drivers?",
            "How to connect to WiFi?",
            "How to change password?",
            "How to access shared folders?",
            "How to check system status?"
        ]
        
        general_answers = [
            "To restart your computer, click the Start menu, select Power, and choose Restart. Alternatively, press Ctrl+Alt+Delete and select Restart from the options.",
            "To find your IP address, open Command Prompt and type 'ipconfig'. Look for the IPv4 address under your active network adapter.",
            "To check disk space, right-click on the drive in File Explorer and select Properties. The used and free space will be displayed.",
            "To update software, check for updates in the application's settings or help menu. For system updates, go to Settings > Update & Security.",
            "To backup files, use File History in Windows or copy important files to an external drive or cloud storage service.",
            "To install printer drivers, download the latest drivers from the manufacturer's website and run the installer. Follow the setup wizard.",
            "To connect to WiFi, click the network icon in the taskbar, select your network, and enter the password when prompted.",
            "To change your password, press Ctrl+Alt+Delete, select Change Password, and follow the prompts to create a new password.",
            "To access shared folders, open File Explorer and enter the network path in the address bar, or use the Network section to browse shared resources.",
            "To check system status, open Task Manager (Ctrl+Shift+Esc) to view CPU, memory, and disk usage. For network status, check the network icon in the taskbar."
        ]
        
        # Add general Q&A pairs
        for q, a in zip(general_questions, general_answers):
            additional_pairs.append(("jarvis_trainer", q, a))
        
        # Generate variations of existing pairs
        existing_pairs = self._get_existing_qa_pairs()
        for user, question, answer in existing_pairs:
            # Create variations
            variations = [
                (f"What about {question.lower()}", answer),
                (f"Can you help with {question.lower()}", answer),
                (f"I need help with {question.lower()}", answer),
                (f"How to solve {question.lower()}", answer),
                (f"Steps for {question.lower()}", answer)
            ]
            
            for var_q, var_a in variations:
                additional_pairs.append(("jarvis_trainer", var_q, var_a))
        
        return additional_pairs
    
    def _get_existing_qa_pairs(self) -> List[Tuple[str, str, str]]:
        """Get existing Q&A pairs from the database"""
        try:
            self.cursor.execute("SELECT user, question, answer FROM chat_qa LIMIT 1000")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get existing Q&A pairs: {e}")
            return []
    
    def run_training(self):
        """Main training process"""
        logger.info("Starting Jarvis AI training process...")
        
        # Connect to database
        if not self.connect_db():
            return False
        
        # Ensure table exists
        if not self.ensure_table_exists():
            return False
        
        # Get current count
        current_count = self.get_current_count()
        needed_count = TARGET_COUNT - current_count
        
        if needed_count <= 0:
            logger.info(f"Target count already reached! Current: {current_count:,}, Target: {TARGET_COUNT:,}")
            return True
        
        logger.info(f"Need to generate {needed_count:,} additional Q&A pairs")
        
        # Generate Q&A pairs
        start_time = time.time()
        
        # Generate from templates
        templates = self.generate_qa_templates()
        qa_pairs = self.generate_qa_variations(templates)
        
        # Add additional pairs if needed
        if len(qa_pairs) < needed_count:
            additional_pairs = self.generate_additional_qa_pairs()
            qa_pairs.extend(additional_pairs)
        
        # Remove duplicates
        unique_pairs = list(set(qa_pairs))
        logger.info(f"Generated {len(unique_pairs):,} unique Q&A pairs")
        
        # Insert in batches
        batch_count = 0
        for i in range(0, min(len(unique_pairs), needed_count), BATCH_SIZE):
            batch = unique_pairs[i:i + BATCH_SIZE]
            if self.insert_qa_batch(batch):
                batch_count += 1
                
                # Progress update
                progress = (i + len(batch)) / needed_count * 100
                elapsed = time.time() - start_time
                eta = (elapsed / (i + len(batch))) * (needed_count - i - len(batch)) if i + len(batch) > 0 else 0
                
                logger.info(f"Progress: {progress:.1f}% ({i + len(batch):,}/{needed_count:,}) - ETA: {format_time(eta)}")
            else:
                logger.error(f"Failed to insert batch {batch_count}")
                break
        
        # Final statistics
        final_count = self.get_current_count()
        total_time = time.time() - start_time
        
        logger.info(f"Training completed!")
        logger.info(f"Total Q&A pairs in database: {final_count:,}")
        logger.info(f"Total time: {format_time(total_time)}")
        logger.info(f"Average speed: {final_count/total_time:.0f} Q&A pairs per second")
        
        return True
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

def main():
    """Main function"""
    trainer = JarvisTrainer()
    
    try:
        success = trainer.run_training()
        if success:
            logger.info("Jarvis AI training completed successfully!")
        else:
            logger.error("Jarvis AI training failed!")
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error during training: {e}")
    finally:
        trainer.close()

if __name__ == "__main__":
    main() 