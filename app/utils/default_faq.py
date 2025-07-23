"""Default IT Service Desk FAQ entries.

This module holds the *minimal* knowledge base that should be present in every
installation so that technicians receive consistent answers even on a fresh
setup.  The loader can be invoked at start-up to populate the ``chat_qa`` table
**only if** the question is not already present.
"""
from typing import List, Tuple

from flask import current_app
from sqlalchemy import text

from extensions import db
from app.utils.ai_helpers import store_qa, ensure_chat_qa_table, _normalize

# ---------------------------------------------------------------------------
# Top 50 questions – keep them short so fuzzy matching remains effective.  All
# answers are intentionally concise and focus on actionable next steps.
# ---------------------------------------------------------------------------
FAQ_ENTRIES: List[Tuple[str, str]] = [
    ("How do I reset my Windows password?", "Press Ctrl+Alt+Delete and choose 'Change a password'. If you have forgotten it, browse to https://passwordreset.company.com to reset it using multifactor authentication."),
    ("My account is locked out. What should I do?", "Wait 15 minutes for it to unlock automatically or call the Service Desk at x1234 to have it unlocked immediately."),
    ("I can't print. How do I reconnect to the printer?", "Open Settings > Devices > Printers & scanners, remove the printer, then click 'Add printer' and select it again. If the issue persists reboot the printer and your PC."),
    ("How do I map a network drive?", "Right-click This PC > Map network drive, choose a letter and enter \\fileserver\sharename. Tick 'Reconnect at sign-in' then finish."),
    ("How do I access email on my phone?", "Install the Microsoft Outlook app, sign in with your company email, and approve the sign-in with Authenticator."),
    ("How do I set up multi-factor authentication (MFA)?", "Visit https://aka.ms/mfasetup while on the corporate network and follow the prompts to register the Microsoft Authenticator app."),
    ("How do I request new hardware?", "Submit a hardware request ticket through SPARK under the 'Procurement' category."),
    ("My laptop is running slow. Any tips?", "Reboot the laptop, close unused applications and ensure Windows Updates have finished installing. If the problem continues, open a ticket so we can run diagnostics."),
    ("How do I install approved software?", "Open Company Portal from the Start menu, locate the application and click 'Install'."),
    ("I need admin rights to install software.", "Please open a ticket with justification. Temporary admin access can be granted for up to 1 hour after approval."),
    ("How do I connect to VPN?", "Launch Cisco AnyConnect, enter vpn.company.com, click Connect and sign in with your network credentials and MFA."),
    ("VPN disconnects frequently.", "Check your Internet connection, restart your modem/router and ensure you are on a stable wired or 5 GHz Wi-Fi network."),
    ("Teams is not ringing on incoming calls.", "Verify Do Not Disturb is off, quit and reopen Teams, and ensure Windows Focus Assist is disabled."),
    ("My camera isn't detected in Teams.", "Close any application using the camera, then in Teams go to Settings > Devices and pick the correct camera."),
    ("Outlook keeps asking for my password.", "Remove stored credentials in Windows Credential Manager and restart Outlook."),
    ("Email is stuck in Outbox.", "Switch to Online Mode (Send/Receive > Work Offline), then click Send/Receive All."),
    ("How do I create a meeting in Outlook?", "In Calendar view click 'New Meeting', add attendees, set date/time and click Send."),
    ("How do I synchronize OneDrive?", "Click the blue OneDrive icon, then 'Help & Settings' > 'Resume syncing'."),
    ("OneDrive shows red X on files.", "Right-click the file and choose 'Free up space', then let OneDrive sync again."),
    ("I deleted a file by mistake.", "Check Recycle Bin or OneDrive's 'Recycle bin' online to restore it within 30 days."),
    ("How do I forward my desk phone to mobile?", "On the phone press Forward > All Calls and enter your mobile number starting with 9."),
    ("Wireless mouse is not working.", "Replace the batteries, re-pair Bluetooth or plug the USB receiver into a different port."),
    ("Dual monitor not detected.", "Make sure cables are connected, press Windows+P and choose 'Extend'. Update graphics drivers if needed."),
    ("How do I connect to a meeting room display?", "Use the HDMI cable on the table and press the 'Laptop' input on the Crestron panel."),
    ("Zoom audio echo.", "Mute all microphones except the active speaker and reduce speaker volume."),
    ("How do I request software license?", "Create a SPARK ticket under 'Software > Licensing' with the software name and justification."),
    ("Computer won't turn on.", "Verify the power cable is seated, press and hold the power button for 10 seconds, then press again."),
    ("Blue screen error.", "Take note of the error code, reboot, and open a ticket with the code and steps you were doing."),
    ("How do I clear browser cache?", "Press Ctrl+Shift+Delete in the browser, select cached data and cookies, and click Clear."),
    ("Can't access a website but others can.", "Clear DNS cache with 'ipconfig /flushdns' and try in a different browser."),
    ("How do I set an Out of Office reply?", "In Outlook select File > Automatic Replies, choose dates and type your message."),
    ("Email delivery delayed message.", "The recipient's server is throttling messages. Wait or resend later; large attachments may cause delay."),
    ("Printer shows offline.", "Right-click the printer > See what's printing > Printer > Untick 'Use Printer Offline'."),
    ("Can't connect to Wi-Fi.", "Toggle Wi-Fi off/on, forget and reconnect to the SSID, or reboot the access point if authorised."),
    ("Wi-Fi is slow.", "Move closer to the access point or connect to wired if possible. Check other devices for interference."),
    ("How do I encrypt an email?", "In Outlook compose window click Options > Encrypt and send as usual."),
    ("Forgot BitLocker recovery key.", "Contact the Service Desk with the key ID shown on the recovery screen."),
    ("Laptop battery drains quickly.", "Lower screen brightness, close unused apps, and run Battery Report to identify culprits."),
    ("Where can I find the asset tag?", "The silver barcode sticker labelled 'Asset Tag' is usually on the bottom of laptops or back of desktops."),
    ("How do I log a security incident?", "Email security@company.com and open a priority ticket marked 'Security'."),
    ("Phishing email suspected.", "Do not click links. Use 'Report Phishing' button in Outlook or forward to phishing@company.com."),
    ("How do I request a shared mailbox?", "Submit a ticket with desired mailbox name, owners and justification."),
    ("Shared mailbox not showing in Outlook.", "Restart Outlook. If still missing, remove and re-add the account under Account Settings."),
    ("Network drive disconnected after reboot.", "Ensure the 'Reconnect at sign-in' option is ticked when mapping the drive."),
    ("How do I change my voicemail greeting?", "Dial *98 on your desk phone, enter your PIN, then choose option 3 for greetings."),
    ("How do I update Java?", "Open Company Portal and install the latest approved Java package."),
    ("Software Center stuck on downloading.", "Restart the SCCM service: 'net stop ccmexec' then 'net start ccmexec' as admin."),
    ("Windows updates failing.", "Run 'sfc /scannow', then retry updates. If failures persist, contact IT with the error code."),
    ("Can I work from home on personal PC?", "Use the HTML5 Citrix workspace at https://remote.company.com from any up-to-date browser."),
    ("How do I open a ServiceNow ticket?", "Visit https://spark.company.com and click 'New Ticket', choose the relevant category and provide details."),
    ("How do I clear the printer queue using CMD?", "Open Command Prompt as administrator and run 'net stop spooler', then delete all files inside %SystemRoot%\\System32\\spool\\PRINTERS and run 'net start spooler' to restart the print service."),
    ("What's an Oralyzer?", "An Oralyzer is a specialised dental device used to measure oral bacteria levels and saliva pH. It helps clinicians assess oral health quickly chair-side. You can open the full user guide (PDF) <a href='/static/docs/Oralyzer_Docs.pdf' target='_blank'>here</a>.") ,
    ("What is an oralyzer machine?", "The Oralyzer machine analyses saliva samples to provide rapid diagnostics on oral bacteria counts and pH balance. For detailed operating instructions refer to the <a href='/static/docs/Oralyzer_Docs.pdf' target='_blank'>Oralyzer User Guide</a>.") ,
    ("Oralyzer", "The Oralyzer is a diagnostic device that evaluates oral health indicators from saliva. View the full documentation <a href='/static/docs/Oralyzer_Docs.pdf' target='_blank'>here (PDF)</a>.") ,
]


def load_default_faq():
    """Insert FAQ_ENTRIES into chat_qa table if they are missing."""
    ensure_chat_qa_table()
    with current_app.app_context():
        for question, answer in FAQ_ENTRIES:
            exists = db.session.execute(
                text('SELECT 1 FROM chat_qa WHERE lower(question) = :q LIMIT 1'),
                {'q': _normalize(question)},
            ).fetchone()
            if not exists:
                store_qa('Jarvis', question, answer) 