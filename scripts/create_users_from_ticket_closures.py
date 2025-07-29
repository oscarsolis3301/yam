#!/usr/bin/env python3
"""
Create user accounts for team members found in Daily Ticket Closures database
This script creates user accounts for team members who exist in the Freshworks system
but don't have local user accounts yet.
"""

import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def create_users_from_ticket_closures():
    """Create user accounts for team members found in Daily Ticket Closures database"""
    try:
        # Import Flask app and models
        from app import create_app
        from app.models import User, FreshworksUserMapping
        from app.extensions import db
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            print("🔄 Creating user accounts from Daily Ticket Closures database...")
            
            # Get all unique Freshworks users from the mapping table
            mappings = FreshworksUserMapping.query.all()
            created_users = []
            skipped_users = []
            
            print(f"📊 Found {len(mappings)} Freshworks user mappings")
            
            for mapping in mappings:
                if mapping.freshworks_username:
                    # Check if user already exists by username
                    existing_user_by_username = User.query.filter_by(username=mapping.freshworks_username).first()
                    
                    # Create email from username
                    first_name = mapping.freshworks_username.split()[0].lower()
                    email = f"{first_name}@pdshealth.com"
                    
                    # Check if user already exists by email
                    existing_user_by_email = User.query.filter_by(email=email).first()
                    
                    if not existing_user_by_username and not existing_user_by_email:
                        # Create new user
                        user = User(
                            username=mapping.freshworks_username,
                            email=email,
                            role='user',
                            is_active=True,
                            profile_picture='default.png',
                            okta_verified=False,
                            teams_notifications=True,
                            requires_password_change=True
                        )
                        user.set_password('password')  # Set default password
                        db.session.add(user)
                        created_users.append(mapping.freshworks_username)
                        print(f"➕ Created user: {mapping.freshworks_username} ({email})")
                    else:
                        skipped_users.append(mapping.freshworks_username)
                        if existing_user_by_username:
                            print(f"⏭️ User already exists (username): {mapping.freshworks_username}")
                        elif existing_user_by_email:
                            print(f"⏭️ User already exists (email): {mapping.freshworks_username} (email: {email})")
            
            if created_users:
                db.session.commit()
                print(f"\n✅ Successfully created {len(created_users)} new user accounts")
                print(f"Created users: {', '.join(created_users)}")
            else:
                print(f"\n✅ No new users to create - all {len(skipped_users)} team members already have accounts")
            
            if skipped_users:
                print(f"Skipped (already exist): {', '.join(skipped_users)}")
            
            # Show summary
            total_team_members = len(mappings)
            total_users = User.query.count()
            print(f"\n📈 Summary:")
            print(f"   Total team members in Freshworks: {total_team_members}")
            print(f"   Total users in system: {total_users}")
            print(f"   New users created: {len(created_users)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating users from ticket closures: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def sync_freshworks_mappings():
    """Sync Freshworks user mappings from IDs.txt file"""
    try:
        from app import create_app
        from app.models import FreshworksUserMapping
        from app.extensions import db
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            print("🔄 Syncing Freshworks user mappings...")
            
            # Load team members from Freshworks IDs.txt
            ids_file_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'Freshworks', 'IDs.txt')
            
            if not os.path.exists(ids_file_path):
                print(f"❌ Freshworks IDs.txt not found at {ids_file_path}")
                return False
            
            mappings_created = 0
            mappings_updated = 0
            
            with open(ids_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ' - ' in line:
                        name, freshworks_id = line.split(' - ', 1)
                        clean_name = name.strip()
                        freshworks_id = freshworks_id.strip()
                        
                        # Check if mapping already exists
                        existing_mapping = FreshworksUserMapping.query.filter_by(
                            freshworks_user_id=freshworks_id
                        ).first()
                        
                        if existing_mapping:
                            # Update existing mapping
                            if existing_mapping.freshworks_username != clean_name:
                                existing_mapping.freshworks_username = clean_name
                                mappings_updated += 1
                                print(f"🔄 Updated mapping: {clean_name} (ID: {freshworks_id})")
                        else:
                            # Create new mapping
                            new_mapping = FreshworksUserMapping(
                                freshworks_user_id=freshworks_id,
                                freshworks_username=clean_name
                            )
                            db.session.add(new_mapping)
                            mappings_created += 1
                            print(f"➕ Created mapping: {clean_name} (ID: {freshworks_id})")
            
            if mappings_created > 0 or mappings_updated > 0:
                db.session.commit()
                print(f"\n✅ Synced Freshworks mappings:")
                print(f"   New mappings created: {mappings_created}")
                print(f"   Mappings updated: {mappings_updated}")
            else:
                print(f"\n✅ All Freshworks mappings are up to date")
            
            return True
            
    except Exception as e:
        print(f"❌ Error syncing Freshworks mappings: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function to run the user creation process"""
    print("=" * 60)
    print("TEAM MEMBER USER ACCOUNT CREATION")
    print("=" * 60)
    
    # Step 1: Sync Freshworks mappings
    print("\n1. Syncing Freshworks user mappings...")
    if sync_freshworks_mappings():
        print("✅ Freshworks mappings synced successfully")
    else:
        print("❌ Failed to sync Freshworks mappings")
        return
    
    # Step 2: Create users from ticket closures
    print("\n2. Creating user accounts from Daily Ticket Closures...")
    if create_users_from_ticket_closures():
        print("✅ User creation completed successfully")
    else:
        print("❌ Failed to create users")
        return
    
    print("\n" + "=" * 60)
    print("USER ACCOUNT CREATION COMPLETED")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Team members can now log in with their username and password 'password'")
    print("   2. They should change their password on first login")
    print("   3. Their ticket closure data will be automatically linked to their accounts")
    print("   4. They will appear in the YAM Dashboard Daily Ticket Closures chart")

if __name__ == '__main__':
    main() 