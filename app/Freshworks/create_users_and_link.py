#!/usr/bin/env python3
"""
Create Local Users and Link to Freshworks Mappings

This script creates local user accounts for all Freshworks users in IDs.txt
and links them to the FreshworksUserMapping table so the Daily Ticket Closures
graph shows real data instead of dummy data.
"""

import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.models.base import User, FreshworksUserMapping
from app.extensions import db

def load_id_name_map(filepath):
    """Load ID to name mapping from IDs.txt file"""
    id_name_map = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Handle "Name - ID" format
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        id_str = parts[1].strip()
                        try:
                            id_int = int(id_str)
                            id_name_map[id_int] = name
                            print(f"✅ Mapped: {name} -> {id_int}")
                        except ValueError:
                            print(f"⚠️ Invalid ID format on line {line_num}: {id_str}")
                else:
                    print(f"⚠️ Invalid format on line {line_num}: {line}")
                    
    except FileNotFoundError:
        print(f"⚠️ ID file '{filepath}' not found.")
        return {}
    except Exception as e:
        print(f"❌ Error reading ID file: {e}")
        return {}
    
    print(f"📋 Loaded {len(id_name_map)} user mappings from {filepath}")
    return id_name_map

def create_username_from_name(name):
    """Create a username from a full name"""
    # Remove special characters and split into parts
    name_parts = name.replace('-', ' ').replace('.', ' ').split()
    
    if len(name_parts) >= 2:
        # Use first letter of first name + last name
        username = f"{name_parts[0][0].lower()}{name_parts[-1].lower()}"
    else:
        # Use the name as is, lowercase
        username = name.lower().replace(' ', '')
    
    # Remove any non-alphanumeric characters
    username = ''.join(c for c in username if c.isalnum())
    
    return username

def create_email_from_name(name):
    """Create an email from a full name"""
    username = create_username_from_name(name)
    return f"{username}@pdshealth.com"

def create_local_users_and_link():
    """Create local users for all Freshworks mappings and link them"""
    print("🚀 Creating local users and linking to Freshworks mappings...")
    print("=" * 60)
    
    # Load Freshworks user mappings
    script_dir = os.path.dirname(os.path.abspath(__file__))
    id_file_path = os.path.join(script_dir, 'IDs.txt')
    id_name_map = load_id_name_map(id_file_path)
    
    if not id_name_map:
        print("❌ No user mappings found. Cannot proceed.")
        return False
    
    users_created = 0
    users_linked = 0
    
    for freshworks_id, freshworks_name in id_name_map.items():
        print(f"\n🔍 Processing: {freshworks_name} (ID: {freshworks_id})")
        
        # Check if mapping exists
        mapping = FreshworksUserMapping.query.filter_by(
            freshworks_user_id=freshworks_id
        ).first()
        
        if not mapping:
            print(f"   ⚠️ No mapping found for {freshworks_name}, creating...")
            mapping = FreshworksUserMapping(
                freshworks_user_id=freshworks_id,
                freshworks_username=freshworks_name
            )
            db.session.add(mapping)
            db.session.commit()
        
        # Check if already linked
        if mapping.user_id:
            print(f"   ✅ Already linked to user ID: {mapping.user_id}")
            continue
        
        # Create username and email
        username = create_username_from_name(freshworks_name)
        email = create_email_from_name(freshworks_name)
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | 
            (User.email == email) |
            (User.username == freshworks_name)
        ).first()
        
        if existing_user:
            print(f"   🔗 Found existing user: {existing_user.username}")
            # Link the mapping to existing user
            mapping.user_id = existing_user.id
            users_linked += 1
        else:
            print(f"   ➕ Creating new user: {username} ({email})")
            # Create new user
            new_user = User(
                username=username,
                email=email,
                role='user',
                is_active=True,
                profile_picture='default.png',
                okta_verified=False,
                teams_notifications=True
            )
            new_user.set_password('password')  # Default password
            db.session.add(new_user)
            db.session.commit()
            
            # Link the mapping to new user
            mapping.user_id = new_user.id
            users_created += 1
            print(f"   ✅ Created and linked user: {username}")
        
        # Update mapping
        mapping.updated_at = datetime.utcnow()
        db.session.commit()
    
    print(f"\n🎉 Summary:")
    print(f"   📊 Total Freshworks users: {len(id_name_map)}")
    print(f"   ➕ New users created: {users_created}")
    print(f"   🔗 Existing users linked: {users_linked}")
    print(f"   ✅ Total linked: {users_created + users_linked}")
    
    return True

def verify_linkages():
    """Verify that all mappings are properly linked"""
    print("\n🔍 Verifying linkages...")
    print("=" * 40)
    
    mappings = FreshworksUserMapping.query.all()
    linked_count = 0
    unlinked_count = 0
    
    for mapping in mappings:
        if mapping.user_id:
            user = User.query.get(mapping.user_id)
            if user:
                print(f"✅ {mapping.freshworks_username} -> {user.username}")
                linked_count += 1
            else:
                print(f"❌ {mapping.freshworks_username} -> User ID {mapping.user_id} not found")
                unlinked_count += 1
        else:
            print(f"⚠️ {mapping.freshworks_username} -> Not linked")
            unlinked_count += 1
    
    print(f"\n📊 Linkage Summary:")
    print(f"   ✅ Linked: {linked_count}")
    print(f"   ⚠️ Unlinked: {unlinked_count}")
    print(f"   📊 Total: {len(mappings)}")
    
    return linked_count, unlinked_count

def main():
    """Main function"""
    try:
        # Create Flask app context
        app = create_app()
        with app.app_context():
            print("🚀 Starting user creation and linking process...")
            
            # Create users and link mappings
            success = create_local_users_and_link()
            
            if success:
                # Verify linkages
                linked, unlinked = verify_linkages()
                
                if unlinked == 0:
                    print("\n🎉 All Freshworks users are now properly linked!")
                    print("📊 The Daily Ticket Closures graph will now show real data.")
                else:
                    print(f"\n⚠️ {unlinked} users still need to be linked manually.")
            else:
                print("\n❌ Failed to create users and link mappings.")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main() 