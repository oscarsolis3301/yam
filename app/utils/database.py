import sqlite3
from datetime import datetime
from sqlalchemy import text, Index
from app.extensions import db
from app.utils.logger import setup_logging
from app.config import Config
from sqlalchemy import inspect

logger = setup_logging()

def init_database(app):
    """Initialize database - call this once at startup"""
    if not app:
        raise ValueError("Flask app instance is required")
        
    # Create all tables
    db.create_all()
    
    # Add missing columns if needed
    add_missing_columns()
    
    # Create indexes for performance
    create_indexes()
    
    # Create default admin user
    create_admin_user()
    
    # Initialize cache table
    init_cache_table()
    
    # Initialize search table
    init_search_table()

    # Seed common questions / Jarvis user
    seed_common_qa()
    
    logger.info("Database initialized successfully")

def add_missing_columns():
    """Add any missing columns to existing tables"""
    try:
        conn = db.engine.connect()
        inspector = inspect(conn)
        
        # Check if ticket_closure table exists and add ticket_numbers column if missing
        if inspector.has_table('ticket_closure'):
            columns = [col['name'] for col in inspector.get_columns('ticket_closure')]
            if 'ticket_numbers' not in columns:
                conn.execute(text('ALTER TABLE ticket_closure ADD COLUMN ticket_numbers TEXT'))
                conn.commit()
                logger.info("Added ticket_numbers column to ticket_closure table")
        
        # Check search_history table
        if inspector.has_table('search_history'):
            columns = [col['name'] for col in inspector.get_columns('search_history')]
            if 'search_type' not in columns:
                conn.execute(text('ALTER TABLE search_history ADD COLUMN search_type VARCHAR(50) DEFAULT "General"'))
                conn.commit()
                logger.info("Added search_type column to search_history table")
        
        # Check outage table
        if inspector.has_table('outage'):
            columns = [col['name'] for col in inspector.get_columns('outage')]
            if 'affected_systems' not in columns:
                conn.execute(text('ALTER TABLE outage ADD COLUMN affected_systems VARCHAR(255)'))
                conn.commit()
                logger.info("Added affected_systems column to outage table")
        
        # Check user table
        if inspector.has_table('user'):
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'profile_picture' not in columns:
                conn.execute(text('ALTER TABLE user ADD COLUMN profile_picture VARCHAR(255) DEFAULT "default.png"'))
            if 'okta_verified' not in columns:
                conn.execute(text('ALTER TABLE user ADD COLUMN okta_verified BOOLEAN DEFAULT FALSE'))
            if 'teams_notifications' not in columns:
                conn.execute(text('ALTER TABLE user ADD COLUMN teams_notifications BOOLEAN DEFAULT TRUE'))
            
            conn.commit()
        
        # Create ticket closure tables if they don't exist
        if not inspector.has_table('ticket_closure'):
            conn.execute(text('''
                CREATE TABLE ticket_closure (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    freshworks_user_id INTEGER,
                    date DATE NOT NULL,
                    tickets_closed INTEGER NOT NULL DEFAULT 0,
                    ticket_numbers TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    UNIQUE (user_id, date)
                )
            '''))
            conn.commit()
            logger.info("Created ticket_closure table")
        
        if not inspector.has_table('freshworks_user_mapping'):
            conn.execute(text('''
                CREATE TABLE freshworks_user_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    freshworks_user_id INTEGER NOT NULL UNIQUE,
                    freshworks_username VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user (id)
                )
            '''))
            conn.commit()
            logger.info("Created freshworks_user_mapping table")
        
        if not inspector.has_table('ticket_sync_metadata'):
            conn.execute(text('''
                CREATE TABLE ticket_sync_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_date DATE NOT NULL UNIQUE,
                    last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_count INTEGER NOT NULL DEFAULT 0,
                    tickets_processed INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.commit()
            logger.info("Created ticket_sync_metadata table")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error adding missing columns: {e}")
        if 'conn' in locals():
            conn.close()

def create_indexes():
    """Create database indexes for better performance"""
    try:
        from app.models import KBArticle
        
        # Create indexes if they don't exist
        idx1 = Index('ix_kbarticle_file_path', KBArticle.file_path)
        idx2 = Index('ix_kbarticle_status', KBArticle.status)
        idx3 = Index('ix_kbarticle_is_public', KBArticle.is_public)
        
        idx1.create(bind=db.engine, checkfirst=True)
        idx2.create(bind=db.engine, checkfirst=True)
        idx3.create(bind=db.engine, checkfirst=True)
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")

def create_admin_user():
    """Create default admin user if it doesn't exist"""
    try:
        from app.models import User
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@pdshealth.com',
                role='admin',
                is_active=True,
                profile_picture='default.png',
                okta_verified=False,
                teams_notifications=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created successfully")
        else:
            # Update admin user
            admin.email = 'admin@pdshealth.com'
            admin.is_active = True
            admin.role = 'admin'
            db.session.commit()
            logger.info("Admin user updated successfully")
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating/updating admin user: {e}")

def init_cache_table():
    """Create api_cache if it doesn't exist yet."""
    try:
        conn = sqlite3.connect(Config.QUESTIONS_DB)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            query      TEXT PRIMARY KEY,
            raw_json   TEXT,
            summary    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()
        logger.info("Cache table initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing cache table: {e}")

def init_search_table():
    """Initialize search history table"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Search table initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing search table: {e}")

def seed_common_qa():
    """Insert a default "Jarvis" system user and a handful of common
    Q&A pairs so that the assistant can answer basic questions from day one.
    The function is *idempotent*: it checks for existing records to avoid
    duplicates every time the application restarts.
    """
    try:
        from app.models import User
        from app.utils.ai_helpers import store_qa

        # ------------------------------------------------------------------
        # 1) Ensure the special "Jarvis" system user exists
        # ------------------------------------------------------------------
        jarvis = User.query.filter_by(username='Jarvis').first()
        if not jarvis:
            jarvis = User(
                username='Jarvis',
                email='jarvis@pdshealth.com',
                role='system',
                is_active=True,
                profile_picture='jarvis.png',
                created_at=datetime.utcnow()
            )
            jarvis.set_password('changeMe')  # Random placeholder
            db.session.add(jarvis)
            db.session.commit()
            logger.info("Created default Jarvis system user")

        # ------------------------------------------------------------------
        # 2) Seed Q&A pairs – ensure the full canonical list is present
        # ------------------------------------------------------------------
        from app.models import ChatQA
        existing_questions = {row.question.strip().lower() for row in ChatQA.query.all()}

        # Comprehensive list of the ~50 most common Service-Desk / IT questions
        top_qas = [
            ("What is SPARK?", "SPARK is PDS Health's internal support and knowledge platform designed to streamline IT assistance and provide instant answers."),
            ("How do I reset my password?", "You can reset your password from the login screen by clicking 'Forgot Password' or by contacting the IT Service Desk."),
            ("Who do I contact for hardware issues?", "Please submit a ticket via SPARK or call the IT Service Desk at x1234 for any hardware-related problems."),
            ("What are the Service Desk hours?", "The Service Desk is staffed Monday–Friday from 6 AM to 6 PM (CST). After-hours support is available for critical outages."),
            ("How do I connect to the VPN?", "Open Cisco AnyConnect, enter 'vpn.pdshealth.com', then authenticate with your network credentials followed by your MFA token."),
            ("My computer is running slow. What should I do?", "Try rebooting first. Close unnecessary applications and ensure Windows Updates are completed. If the issue persists, open a ticket so we can run diagnostics."),
            ("I forgot my username. How can I retrieve it?", "Your username is normally the first letter of your first name plus your last name (e.g., jdoe). If you are unsure, call the Service Desk and we will verify your identity and provide it."),
            ("How do I set up my email on my mobile device?", "Install Microsoft Outlook from the app store, choose 'Work account', enter your email, and complete MFA. Detailed step-by-step guides are available in the KB under Email › Mobile."),
            ("Why can't I print? My printer shows offline.", "Ensure the printer is powered on and connected to the network. From Windows, go to Settings › Devices › Printers, right-click the printer and choose 'Use Printer Online'. If it remains offline, restart the printer and, if needed, contact IT."),
            ("How do I request new hardware or software?", "Submit a 'Hardware/Software Request' ticket in SPARK, providing business justification and manager approval. The procurement team will review and update you."),
            ("How do I map a network drive?", "Open File Explorer, right-click 'This PC' › 'Map network drive…', choose a drive letter, and enter the path (e.g., \\fileserver\\share). Use your network credentials if prompted."),
            ("I'm locked out of my account. What should I do?", "Wait 15 minutes for automatic unlock or call the Service Desk for immediate assistance after identity verification."),
            ("How do I set up Multi-Factor Authentication (MFA)?", "Install the Microsoft Authenticator app, sign in with your work account, and scan the QR code provided in the MFA setup portal at https://aka.ms/mfasetup."),
            ("Why am I unable to access a shared folder?", "You may lack permissions or be off-network. Verify VPN/Wi-Fi connectivity, then open a ticket requesting access including the folder path and business reason."),
            ("Outlook keeps asking for my password repeatedly.", "Close Outlook, open Windows Credentials Manager and remove saved credentials for Outlook/Office, then reopen Outlook and re-authenticate. If issue continues, run Office repair."),
            ("I accidentally deleted important files. Can I recover them?", "Check the Recycle Bin first. For network shares, right-click inside the folder and select 'Restore previous versions'. If the file is still missing, contact the Service Desk for backup restore."),
            ("How can I protect myself against phishing emails?", "Always verify sender address, hover over links before clicking, and never provide credentials via email. Report suspicious messages using the 'Report Phish' button in Outlook."),
            ("How do I update my operating system?", "Open Settings › Windows Update and click 'Check for updates'. Install all critical patches and reboot when prompted."),
            ("Why can't I join a Microsoft Teams meeting?", "Ensure Teams is up-to-date, clear cache (\%appdata\%\\Microsoft\\Teams), and try the web version if the desktop app fails. Confirm your audio/video devices are selected correctly."),
            ("How do I clear my browser cache?", "In Chrome/Edge press Ctrl+Shift+Delete, select 'Cached images and files' and 'Cookies', choose 'All time', then click 'Clear data'."),
            ("What should I do when my computer freezes?", "Press Ctrl+Alt+Delete and open Task Manager to end unresponsive tasks. If the system remains frozen, perform a hard reboot by holding the power button for 10 seconds."),
            ("How do I request admin rights on my workstation?", "Submit an 'Admin Rights' request in SPARK with justification. The request will be reviewed for least-privilege compliance."),
            ("How do I set an Out-of-Office reply in Outlook?", "In Outlook go to File › Automatic Replies, enable 'Send automatic replies', enter your message for inside and outside the organisation, and click OK."),
            ("How do I change my network password before it expires?", "Press Ctrl+Alt+Delete and select 'Change a password…', then follow the prompts. Ensure you update cached credentials on mobile devices to avoid lockouts."),
            ("How do I submit an IT ticket?", "Log in to SPARK, click 'New Ticket', select the appropriate category, provide a detailed description, and submit. You will receive email confirmation."),
            ("How long does it take to receive a response to my ticket?", "Initial acknowledgement is within 15 minutes during business hours. Resolution time depends on severity and complexity, but most requests are resolved within one business day."),
            ("How do I check my ticket status?", "Log in to SPARK, open the 'My Tickets' tab, and review the status column or comments."),
            ("My VPN connection drops frequently. What can I do?", "Ensure a stable internet connection, avoid Wi-Fi dead zones, and keep your VPN client up-to-date. If issues persist, collect the AnyConnect log and attach it to your ticket."),
            ("How do I encrypt a file or email?", "Right-click the file › Properties › Advanced › 'Encrypt contents'. For email, in Outlook choose 'Options' › 'Encrypt'. All recipients must be internal or have encryption capabilities."),
            ("How do I install approved software from Software Center?", "Open the Software Center app, browse the 'Applications' tab, select the software, and click 'Install'. A reboot may be required."),
            ("My Wi-Fi keeps disconnecting.", "Move closer to the access point, forget and reconnect to the corporate SSID, or try another device to rule out hardware faults. If still unstable, open a ticket including your location."),
            ("How do I connect to a projector or external monitor?", "Use the Windows shortcut Win+P to choose 'Duplicate' or 'Extend'. Ensure the HDMI/DisplayPort cable is firmly connected. Update graphics drivers if no signal."),
            ("My keyboard or mouse is not working.", "Replace batteries if wireless, check USB connections, and try a different port or PC. If still non-functional, request a replacement through SPARK."),
            ("How do I reset my voicemail PIN?", "Dial the voicemail access number, choose 'Reset PIN' from the menu, or request a reset through the telecom self-service portal."),
            ("Why is my internet so slow?", "Run a speed-test at https://speedtest.net and compare to expected bandwidth. Reboot your router if remote. Inside the office, check for network outages on the status page."),
            ("How do I unlock a user account in Active Directory?", "If you have delegated rights, open AD Users & Computers, locate the user, right-click and select 'Unlock Account'. Otherwise, request the Service Desk to unlock."),
            ("How do I run Windows updates manually?", "Open Settings › Windows Update and click 'Check for updates', then 'Install'. Reboot when prompted to complete installation."),
            ("How do I change my default printer?", "Settings › Devices › Printers & scanners, select the printer, click 'Manage', then 'Set as default'."),
            ("How do I recover a previous version of a file on a network share?", "Right-click the file or folder, choose 'Restore previous versions', select the required timestamp, and click 'Restore'."),
            ("How do I report spam email?", "In Outlook select the message and click 'Report Phish' on the ribbon. The email is sent to security for analysis."),
            ("My webcam is not working in Teams.", "Check Privacy settings under Windows Settings › Camera, ensure the app has permission. Update camera drivers and restart Teams."),
            ("How do I request remote assistance?", "Open Quick Assist on Windows, click 'Get assistance', share the 6-digit code with the Service Desk, or create a ticket requesting a remote session."),
            ("How do I find my computer name and IP address?", "Press Win+R, type 'cmd', then 'hostname' for the computer name and 'ipconfig' for IP details."),
            ("How do I access Citrix / Remote Apps?", "Install Citrix Workspace, navigate to https://remote.pdshealth.com, log in with network credentials, and launch the required app or desktop."),
            ("How do I sync OneDrive?", "Click the OneDrive cloud icon, sign in with your work account, and ensure 'Files On-Demand' is enabled. Use 'Sync' from SharePoint if a library is not yet added."),
            ("How do I set up a conference room display?", "Use the provided HDMI or wireless adapter (Teams Rooms). Select the correct input on the display panel. Call the Service Desk if the panel shows 'No Signal'."),
            ("How do I share a large file?", "Upload to OneDrive or SharePoint and share a link with appropriate permissions instead of emailing attachments larger than 25 MB."),
            ("How do I enable BitLocker disk encryption?", "Open Control Panel › BitLocker Drive Encryption and click 'Turn on BitLocker'. Save the recovery key to your OneDrive. IT can enable it remotely via Intune if required."),
            ("How do I factory-reset my work phone before returning it?", "Backup any personal data first, then go to Settings › General › Reset › Erase All Content and Settings (iOS) or Settings › System › Reset (Android). Remove the SIM card."),
            ("How do I extend my mailbox storage?", "Archive old mail to an Online Archive or PST, or open a ticket for a quota increase with business justification."),
            ("How do I troubleshoot blue screen (BSOD) errors?", "Note the stop-code, ensure drivers and Windows Updates are current, run hardware diagnostics, and open a ticket attaching the MEMORY.DMP located in C:\\Windows."),
            ("How do I change my password while off-network?", "Connect to VPN first, press Ctrl+Alt+Delete, choose 'Change a password…', then enter your old and new passwords."),
            ("How do I reset MFA when I change phones?", "Log in to https://aka.ms/mfasetup from a trusted device, remove the old authenticator and add a new one, or contact IT to reset if you no longer have access."),
        ]

        # Insert any Q&A pairs that are not yet present
        for q, a in top_qas:
            if q.strip().lower() not in existing_questions:
                store_qa('Jarvis', q, a)

        logger.info("Ensured Jarvis Q&A seed ({} entries) is present".format(len(top_qas)))

        # ------------------------------------------------------------------
        # 3) Ensure a placeholder profile picture exists so the UI doesn't
        #    break if a custom Jarvis avatar hasn't been uploaded yet.
        # ------------------------------------------------------------------
        try:
            import shutil, os
            base_dir = os.path.join('static', 'uploads', 'profile_pictures')
            os.makedirs(base_dir, exist_ok=True)
            jarvis_pic = os.path.join(base_dir, 'jarvis.png')
            default_pic = os.path.join(base_dir, 'boy.png')
            if not os.path.exists(jarvis_pic) and os.path.exists(default_pic):
                shutil.copy2(default_pic, jarvis_pic)
                logger.info("Copied default avatar to jarvis.png placeholder")
        except Exception as copy_err:
            logger.warning(f"Unable to create jarvis.png placeholder: {copy_err}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to seed common Q&A pairs: {e}") 