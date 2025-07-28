// User Profile Module
// Handles user profile modals and user data management

class UserProfileModule {
    constructor(coreModule, apiModule) {
        this.coreModule = coreModule;
        this.apiModule = apiModule;
    }
    
    handleClockIdLookup(clockId, userData = null) {
        console.log('User Profile Module: handleClockIdLookup called with:', { clockId, userData });
        // Hide suggestions dropdown when opening user profile modal
        this.coreModule.hideSuggestions();
        this.coreModule.hideResults();
        
        // Use the existing sidebar user modal
        if (window.showSidebarUserModal) {
            window.showSidebarUserModal(clockId, userData);
        } else {
            // Fallback to creating a new modal if sidebar modal is not available
            this.showUserProfileModal(clockId, userData);
        }
    }
    
    showUserProfileModal(clockId, userData = null) {
        console.log('User Profile Module: showUserProfileModal called with:', { clockId, userData });
        
        // Add CSS styles if not already present
        this.addUserProfileStyles();
        
        // Create modal HTML with improved design
        const modalHTML = `
            <div id="userProfileModal" class="user-profile-modal-overlay">
                <div class="user-profile-modal">
                    <div class="user-profile-modal-header">
                        <h3><i class="bi bi-person-circle"></i> User Profile</h3>
                        <button class="user-profile-modal-close" onclick="window.closeUserProfileModal()">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                    <div class="user-profile-modal-content">
                        <div class="user-profile-loading">
                            <div class="loading-spinner"></div>
                            <p>Loading user information...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        console.log('User Profile Module: Adding modal to page...');
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        console.log('User Profile Module: User profile modal added to page');
        
        // Add click outside to close functionality
        const modalOverlay = document.getElementById('userProfileModal');
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                this.closeUserProfileModal();
            }
        });
        
        // Add escape key to close functionality
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                this.closeUserProfileModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        // Add global close function
        window.closeUserProfileModal = () => {
            this.closeUserProfileModal();
        };
        
        // Load user data immediately
        this.loadUserProfileData(clockId, userData);
    }
    
    async loadUserProfileData(clockId, userData = null) {
        const modalContent = document.querySelector('.user-profile-modal-content');
        
        try {
            const userInfo = await this.apiModule.loadUserProfileData(clockId, userData);
            
            // Generate initials for avatar with fallback
            const fullName = userInfo.full_name || `User ${clockId}`;
            const initials = fullName.split(' ').map(name => name.charAt(0)).join('').toUpperCase().slice(0, 2) || 'U';
            
            // Determine user status and badges
            const status = userInfo.status || 'Active';
            const isLocked = status.toLowerCase().includes('locked') || status.toLowerCase().includes('lockout');
            const isDisabled = status.toLowerCase().includes('disabled') || status.toLowerCase().includes('inactive');
            const isAdmin = userInfo.role === 'admin' || userInfo.department === 'IT' || userInfo.is_admin;
            const isVip = userInfo.is_vip || userInfo.priority === 'high';
            
            // Generate badges
            const badges = [];
            if (status.toLowerCase().includes('active') && !isLocked && !isDisabled) {
                badges.push('<span class="user-profile-badge badge-active"><i class="bi bi-check-circle"></i> Active</span>');
            }
            if (isLocked) {
                badges.push('<span class="user-profile-badge badge-locked"><i class="bi bi-lock"></i> Locked</span>');
            }
            if (isDisabled) {
                badges.push('<span class="user-profile-badge badge-disabled"><i class="bi bi-x-circle"></i> Disabled</span>');
            }
            if (isAdmin) {
                badges.push('<span class="user-profile-badge badge-admin"><i class="bi bi-shield-check"></i> Admin</span>');
            }
            if (isVip) {
                badges.push('<span class="user-profile-badge badge-vip"><i class="bi bi-star"></i> VIP</span>');
            }
            
            // Render user profile content
            modalContent.innerHTML = this.generateUserProfileHTML(clockId, userInfo, initials, badges, isLocked, isDisabled);
            
            // Add service desk action handlers
            this.addServiceDeskHandlers(clockId, userInfo);
            
        } catch (error) {
            console.error('Error loading user profile:', error);
            // Show a user-friendly error with the ability to still view basic info
            modalContent.innerHTML = this.generateErrorProfileHTML(clockId);
        }
    }
    
    generateUserProfileHTML(clockId, userInfo, initials, badges, isLocked, isDisabled) {
        const fullName = userInfo.full_name || `User ${clockId}`;
        const status = userInfo.status || 'Active';
        
        return `
            <div class="user-profile-header">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <div class="user-profile-avatar">
                        <span class="user-profile-avatar-text">${initials}</span>
                    </div>
                    <div class="user-profile-info-header">
                        <div class="user-profile-name-row">
                            <div class="user-profile-name">${fullName}</div>
                            ${badges.join('')}
                        </div>
                        <div class="user-profile-title">${userInfo.title || userInfo.job_title || 'Employee'}</div>
                    </div>
                </div>
                <div class="user-profile-actions-header">
                    <div class="tooltip">
                        <button class="action-icon-btn-header" onclick="window.createTicket('${clockId}')" title="Create Ticket">
                            <i class="bi bi-ticket"></i>
                        </button>
                        <span class="tooltiptext">Create Ticket</span>
                    </div>
                    <div class="tooltip">
                        <button class="action-icon-btn-header" onclick="window.resetPassword('${clockId}')" title="Reset Password">
                            <i class="bi bi-key"></i>
                        </button>
                        <span class="tooltiptext">Reset Password</span>
                    </div>
                    <div class="tooltip">
                        <button class="action-icon-btn-header" onclick="window.viewHistory('${clockId}')" title="View History">
                            <i class="bi bi-clock-history"></i>
                        </button>
                        <span class="tooltiptext">View History</span>
                    </div>
                    ${isLocked ? `<div class="tooltip">
                        <button class="action-icon-btn-header" onclick="window.unlockAccount('${clockId}')" title="Unlock Account">
                            <i class="bi bi-unlock"></i>
                        </button>
                        <span class="tooltiptext">Unlock Account</span>
                    </div>` : ''}
                    ${isDisabled ? `<div class="tooltip">
                        <button class="action-icon-btn-header" onclick="window.enableAccount('${clockId}')" title="Enable Account">
                            <i class="bi bi-check-circle"></i>
                        </button>
                        <span class="tooltiptext">Enable Account</span>
                    </div>` : ''}
                    ${!isDisabled ? `<div class="tooltip">
                        <button class="action-icon-btn-header" onclick="window.disableAccount('${clockId}')" title="Disable Account">
                            <i class="bi bi-x-circle"></i>
                        </button>
                        <span class="tooltiptext">Disable Account</span>
                    </div>` : ''}
                    <div class="tooltip">
                        <a href="/tickets?user=${encodeURIComponent(clockId)}" class="action-icon-btn-header" title="View Tickets">
                            <i class="bi bi-ticket-detailed"></i>
                        </a>
                        <span class="tooltiptext">View Tickets</span>
                    </div>
                    <div class="tooltip">
                        <a href="/admin/users/${clockId}" class="action-icon-btn-header" title="Admin View">
                            <i class="bi bi-gear"></i>
                        </a>
                        <span class="tooltiptext">Admin View</span>
                    </div>
                </div>
            </div>
            
            <div class="user-profile-info">
                <div class="user-profile-section">
                    <h4><i class="bi bi-person"></i> Basic Info</h4>
                    <div class="user-profile-fields">
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Clock ID</span>
                            <span class="user-profile-field-value">${userInfo.clock_id || clockId}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Status</span>
                            <span class="user-profile-field-value">
                                <span class="user-profile-status ${isLocked ? 'status-locked' : isDisabled ? 'status-disabled' : 'status-active'}">
                                    <i class="bi bi-${isLocked ? 'lock' : isDisabled ? 'x-circle' : 'check-circle'}"></i>
                                    ${status}
                                </span>
                            </span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Department</span>
                            <span class="user-profile-field-value">${userInfo.department || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Location</span>
                            <span class="user-profile-field-value">${userInfo.location || userInfo.office || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Manager</span>
                            <span class="user-profile-field-value">${userInfo.manager || userInfo.supervisor || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Start Date</span>
                            <span class="user-profile-field-value">${userInfo.start_date || userInfo.hire_date || 'N/A'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="user-profile-section">
                    <h4><i class="bi bi-envelope"></i> Contact</h4>
                    <div class="user-profile-fields">
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Email</span>
                            <span class="user-profile-field-value">${userInfo.email || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Phone</span>
                            <span class="user-profile-field-value">${userInfo.phone || userInfo.phone_number || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Extension</span>
                            <span class="user-profile-field-value">${userInfo.extension || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Mobile</span>
                            <span class="user-profile-field-value">${userInfo.mobile || userInfo.cell_phone || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Emergency</span>
                            <span class="user-profile-field-value">${userInfo.emergency_contact || 'N/A'}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Address</span>
                            <span class="user-profile-field-value">${userInfo.address || userInfo.street_address || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="recent-tickets-section">
                <h4><i class="bi bi-clock-history"></i> Recent Tickets</h4>
                <div class="recent-tickets-list">
                    ${this.generateRecentTicketsHTML()}
                </div>
            </div>
        `;
    }
    
    generateRecentTicketsHTML() {
        const tickets = [
            { id: 'TK-2024-001', title: 'Password Reset Request', priority: 'high', status: 'open', time: '2 hours ago', icon: 'bi-exclamation-triangle' },
            { id: 'TK-2024-002', title: 'Software Installation', priority: 'medium', status: 'resolved', time: '1 day ago', icon: 'bi-laptop' },
            { id: 'TK-2024-003', title: 'General Inquiry', priority: 'low', status: 'closed', time: '3 days ago', icon: 'bi-question-circle' },
            { id: 'TK-2024-004', title: 'Printer Configuration', priority: 'medium', status: 'resolved', time: '4 days ago', icon: 'bi-printer' },
            { id: 'TK-2024-005', title: 'Network Connectivity', priority: 'high', status: 'closed', time: '5 days ago', icon: 'bi-wifi' },
            { id: 'TK-2024-006', title: 'Hardware Replacement', priority: 'low', status: 'resolved', time: '1 week ago', icon: 'bi-keyboard' },
            { id: 'TK-2024-007', title: 'Security Update', priority: 'medium', status: 'closed', time: '1 week ago', icon: 'bi-shield-check' },
            { id: 'TK-2024-008', title: 'Audio Equipment', priority: 'low', status: 'resolved', time: '2 weeks ago', icon: 'bi-headphones' }
        ];
        
        return tickets.map(ticket => `
            <div class="ticket-item" onclick="window.showTicketModal('${ticket.id}', '${ticket.title}', '${ticket.priority}', '${ticket.status}')">
                <div class="ticket-icon ticket-priority-${ticket.priority}">
                    <i class="${ticket.icon}"></i>
                </div>
                <div class="ticket-content">
                    <div class="ticket-title">${ticket.title}</div>
                    <div class="ticket-meta">#${ticket.id} • ${ticket.time}</div>
                </div>
                <div class="ticket-status ticket-status-${ticket.status}">${ticket.status}</div>
            </div>
        `).join('');
    }
    
    generateErrorProfileHTML(clockId) {
        return `
            <div class="user-profile-header">
                <div class="user-profile-avatar">
                    <span class="user-profile-avatar-text">${clockId.slice(0, 2).toUpperCase()}</span>
                </div>
                <div class="user-profile-name">User ${clockId}</div>
                <div class="user-profile-title">Clock ID Lookup</div>
            </div>
            
            <div class="user-profile-info">
                <div class="user-profile-section">
                    <h4><i class="bi bi-exclamation-triangle"></i> Information</h4>
                    <div class="user-profile-fields">
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Clock ID</span>
                            <span class="user-profile-field-value">${clockId}</span>
                        </div>
                        <div class="user-profile-field">
                            <span class="user-profile-field-label">Status</span>
                            <span class="user-profile-field-value">Unknown</span>
                        </div>
                    </div>
                </div>
                
                <div class="user-profile-section">
                    <h4><i class="bi bi-tools"></i> Actions</h4>
                    <div class="user-profile-actions-consolidated">
                        <a href="/users?search=${encodeURIComponent(clockId)}" class="action-icon-btn" title="Search User">
                            <i class="bi bi-search"></i>
                        </a>
                        <a href="/tickets/new?user=${encodeURIComponent(clockId)}" class="action-icon-btn" title="Create Ticket">
                            <i class="bi bi-ticket"></i>
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    addServiceDeskHandlers(clockId, userInfo) {
        // Add service desk action handlers to the global scope
        window.createTicket = (userId) => {
            window.open(`/tickets/new?user=${encodeURIComponent(userId)}`, '_blank');
        };
        
        window.unlockAccount = async (userId) => {
            if (confirm('Are you sure you want to unlock this account?')) {
                try {
                    await this.apiModule.unlockAccount(userId);
                    alert('Account unlocked successfully!');
                    // Refresh the modal to show updated status
                    this.loadUserProfileData(clockId, userInfo);
                } catch (error) {
                    console.error('Error unlocking account:', error);
                    alert('Error unlocking account. Please try again.');
                }
            }
        };
        
        window.resetPassword = async (userId) => {
            if (confirm('Are you sure you want to reset the password for this user?')) {
                try {
                    const data = await this.apiModule.resetPassword(userId);
                    alert(`Password reset successfully! New password: ${data.new_password}`);
                } catch (error) {
                    console.error('Error resetting password:', error);
                    alert('Error resetting password. Please try again.');
                }
            }
        };
        
        window.enableAccount = async (userId) => {
            if (confirm('Are you sure you want to enable this account?')) {
                try {
                    await this.apiModule.enableAccount(userId);
                    alert('Account enabled successfully!');
                    // Refresh the modal to show updated status
                    this.loadUserProfileData(clockId, userInfo);
                } catch (error) {
                    console.error('Error enabling account:', error);
                    alert('Error enabling account. Please try again.');
                }
            }
        };
        
        window.disableAccount = async (userId) => {
            if (confirm('Are you sure you want to disable this account? This will prevent the user from logging in.')) {
                try {
                    await this.apiModule.disableAccount(userId);
                    alert('Account disabled successfully!');
                    // Refresh the modal to show updated status
                    this.loadUserProfileData(clockId, userInfo);
                } catch (error) {
                    console.error('Error disabling account:', error);
                    alert('Error disabling account. Please try again.');
                }
            }
        };
        
        window.viewHistory = (userId) => {
            window.open(`/admin/users/${userId}/history`, '_blank');
        };
        
        // Ticket modal functionality
        window.showTicketModal = (ticketId, title, priority, status) => {
            // This will be handled by the ticket module
            if (this.coreModule.ticketModule) {
                this.coreModule.ticketModule.showTicketModal(ticketId, title, priority, status);
            }
        };
    }
    
    closeUserProfileModal() {
        const modal = document.getElementById('userProfileModal');
        if (modal) {
            modal.remove();
        }
    }
    
    addUserProfileStyles() {
        if (!document.getElementById('userProfileModalStyles')) {
            const styles = `
                <style id="userProfileModalStyles">
                    .user-profile-modal-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.8);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 9999999;
                        animation: overlayFadeIn 0.2s ease-out;
                    }
                    
                    @keyframes overlayFadeIn {
                        from { opacity: 0; }
                        to { opacity: 1; }
                    }
                    
                    .user-profile-modal {
                        background: #1a1a1a;
                        border-radius: 16px;
                        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.1);
                        width: 95%;
                        max-width: 1400px;
                        height: 90vh;
                        overflow: hidden;
                        animation: modalBounceIn 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        display: flex;
                        flex-direction: column;
                    }
                    
                    @keyframes modalBounceIn {
                        0% {
                            opacity: 0;
                            transform: scale(0.3) translateY(-50px);
                        }
                        50% {
                            transform: scale(1.05) translateY(10px);
                        }
                        100% {
                            opacity: 1;
                            transform: scale(1) translateY(0);
                        }
                    }
                    
                    .user-profile-modal-header {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        padding: 20px 24px;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                        background: #2a2a2a;
                        position: relative;
                        flex-shrink: 0;
                    }
                    
                    .user-profile-modal-header h3 {
                        margin: 0;
                        color: #ffffff;
                        font-size: 20px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }
                    
                    .user-profile-modal-close {
                        background: rgba(255, 255, 255, 0.1);
                        border: none;
                        color: #ffffff;
                        font-size: 18px;
                        cursor: pointer;
                        padding: 8px;
                        border-radius: 50%;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        width: 36px;
                        height: 36px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        position: absolute;
                        top: 16px;
                        right: 20px;
                        z-index: 10;
                    }
                    
                    .user-profile-modal-close:hover {
                        background: rgba(255, 255, 255, 0.2);
                        transform: rotate(90deg) scale(1.1);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                    }
                    
                    .user-profile-modal-content {
                        padding: 20px;
                        flex: 1;
                        overflow: hidden;
                        display: flex;
                        flex-direction: column;
                        gap: 16px;
                    }
                    
                    .user-profile-loading {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 40px 20px;
                        color: #ffffff;
                    }
                    
                    .loading-spinner {
                        width: 40px;
                        height: 40px;
                        border: 3px solid rgba(255, 255, 255, 0.1);
                        border-top: 3px solid #ffffff;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                        margin-bottom: 16px;
                    }
                    
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                    
                    .user-profile-header {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        margin-bottom: 16px;
                        flex-shrink: 0;
                        padding: 0 20px;
                    }
                    
                    .user-profile-avatar {
                        width: 60px;
                        height: 60px;
                        border-radius: 50%;
                        background: #4169e1;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 24px;
                        font-weight: bold;
                        color: #ffffff;
                        position: relative;
                        z-index: 10;
                        box-shadow: 0 8px 24px rgba(65, 105, 225, 0.3);
                        border: 2px solid rgba(255, 255, 255, 0.2);
                        flex-shrink: 0;
                    }
                    
                    .user-profile-avatar-text {
                        position: relative;
                        z-index: 15;
                        color: #ffffff;
                        font-weight: 700;
                    }
                    
                    .user-profile-info-header {
                        display: flex;
                        flex-direction: column;
                        gap: 4px;
                    }
                    
                    .user-profile-actions-header {
                        display: flex;
                        gap: 8px;
                        align-items: center;
                        flex-shrink: 0;
                        min-width: 200px;
                        justify-content: flex-end;
                    }
                    
                    .user-profile-name-row {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }
                    
                    .user-profile-name {
                        font-size: 20px;
                        font-weight: 600;
                        color: #ffffff;
                        margin: 0;
                    }
                    
                    .user-profile-title {
                        font-size: 14px;
                        color: rgba(255, 255, 255, 0.7);
                        margin: 0;
                    }
                    
                    .user-profile-badges {
                        display: flex;
                        gap: 8px;
                        flex-wrap: wrap;
                    }
                    
                    .user-profile-badge {
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 500;
                        display: flex;
                        align-items: center;
                        gap: 4px;
                    }
                    
                    .badge-active {
                        background: rgba(76, 175, 80, 0.2);
                        color: #4caf50;
                        border: 1px solid rgba(76, 175, 80, 0.3);
                    }
                    
                    .badge-locked {
                        background: rgba(244, 67, 54, 0.2);
                        color: #f44336;
                        border: 1px solid rgba(244, 67, 54, 0.3);
                    }
                    
                    .badge-disabled {
                        background: rgba(158, 158, 158, 0.2);
                        color: #9e9e9e;
                        border: 1px solid rgba(158, 158, 158, 0.3);
                    }
                    
                    .badge-admin {
                        background: rgba(33, 150, 243, 0.2);
                        color: #2196f3;
                        border: 1px solid rgba(33, 150, 243, 0.3);
                    }
                    
                    .badge-vip {
                        background: rgba(255, 193, 7, 0.2);
                        color: #ffc107;
                        border: 1px solid rgba(255, 193, 7, 0.3);
                    }
                    
                    .user-profile-info {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 16px;
                        flex: 1;
                        overflow: hidden;
                        margin-bottom: 16px;
                    }
                    
                    .user-profile-section {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 16px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        display: flex;
                        flex-direction: column;
                        overflow: hidden;
                    }
                    
                    .user-profile-section h4 {
                        margin: 0 0 12px 0;
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        flex-shrink: 0;
                    }
                    
                    .user-profile-fields {
                        flex: 1;
                        overflow-y: auto;
                        scrollbar-width: thin;
                        scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                    }
                    
                    .user-profile-fields::-webkit-scrollbar {
                        width: 4px;
                    }
                    
                    .user-profile-fields::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    
                    .user-profile-fields::-webkit-scrollbar-thumb {
                        background: rgba(255, 255, 255, 0.2);
                        border-radius: 2px;
                    }
                    
                    .user-profile-field {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 6px 0;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    }
                    
                    .user-profile-field:last-child {
                        border-bottom: none;
                    }
                    
                    .user-profile-field-label {
                        color: rgba(255, 255, 255, 0.7);
                        font-size: 12px;
                        font-weight: 500;
                    }
                    
                    .user-profile-field-value {
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: 500;
                        text-align: right;
                        max-width: 60%;
                        word-break: break-word;
                    }
                    
                    .user-profile-status {
                        display: flex;
                        align-items: center;
                        gap: 4px;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 500;
                    }
                    
                    .status-active {
                        background: rgba(76, 175, 80, 0.2);
                        color: #4caf50;
                    }
                    
                    .status-locked {
                        background: rgba(244, 67, 54, 0.2);
                        color: #f44336;
                    }
                    
                    .status-disabled {
                        background: rgba(158, 158, 158, 0.2);
                        color: #9e9e9e;
                    }
                    
                    .user-profile-actions-consolidated {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                        gap: 8px;
                        justify-content: center;
                        align-items: center;
                        flex-shrink: 0;
                    }
                    
                    .action-icon-btn {
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        color: #ffffff;
                        padding: 8px;
                        border-radius: 50%;
                        cursor: pointer;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        text-decoration: none;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        width: 36px;
                        height: 36px;
                        position: relative;
                        overflow: hidden;
                    }
                    
                    .action-icon-btn-header {
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        color: #ffffff;
                        padding: 6px;
                        border-radius: 50%;
                        cursor: pointer;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        text-decoration: none;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        width: 32px;
                        height: 32px;
                        position: relative;
                        overflow: hidden;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                    }
                    
                    .action-icon-btn::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: -100%;
                        width: 100%;
                        height: 100%;
                        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                        transition: left 0.5s;
                    }
                    
                    .action-icon-btn:hover::before {
                        left: 100%;
                    }
                    
                    .action-icon-btn:hover {
                        background: rgba(255, 255, 255, 0.2);
                        transform: translateY(-3px) scale(1.05);
                        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
                        border-color: rgba(255, 255, 255, 0.3);
                    }
                    
                    .action-icon-btn:active {
                        transform: translateY(-1px) scale(1.02);
                    }
                    
                    .action-icon-btn i {
                        font-size: 14px;
                        transition: transform 0.3s ease;
                    }
                    
                    .action-icon-btn:hover i {
                        transform: scale(1.2);
                    }
                    
                    .action-icon-btn-header:hover {
                        background: rgba(255, 255, 255, 0.15);
                        transform: translateY(-2px) scale(1.1);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                        border-color: rgba(255, 255, 255, 0.2);
                        color: #ffffff;
                    }
                    
                    .action-icon-btn-header:active {
                        transform: translateY(-1px) scale(1.05);
                    }
                    
                    .action-icon-btn-header i {
                        font-size: 12px;
                        transition: transform 0.3s ease;
                    }
                    
                    .action-icon-btn-header:hover i {
                        transform: scale(1.2);
                    }
                    
                    /* Tooltip styles */
                    .tooltip {
                        position: relative;
                    }
                    
                    .tooltip .tooltiptext {
                        visibility: hidden;
                        width: auto;
                        background-color: rgba(0, 0, 0, 0.9);
                        color: #fff;
                        text-align: center;
                        border-radius: 6px;
                        padding: 6px 10px;
                        position: absolute;
                        z-index: 10000000;
                        bottom: 125%;
                        left: 50%;
                        transform: translateX(-50%);
                        opacity: 0;
                        transition: opacity 0.3s;
                        font-size: 11px;
                        font-weight: 500;
                        white-space: nowrap;
                        pointer-events: none;
                    }
                    
                    .tooltip .tooltiptext::after {
                        content: "";
                        position: absolute;
                        top: 100%;
                        left: 50%;
                        margin-left: -5px;
                        border-width: 5px;
                        border-style: solid;
                        border-color: rgba(0, 0, 0, 0.9) transparent transparent transparent;
                    }
                    
                    .tooltip:hover .tooltiptext {
                        visibility: visible;
                        opacity: 1;
                    }
                    
                    .recent-tickets-section {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 16px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        flex-shrink: 0;
                        margin-top: 16px;
                    }
                    
                    .recent-tickets-section h4 {
                        margin: 0 0 12px 0;
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    
                    .recent-tickets-list {
                        display: flex;
                        flex-direction: column;
                        gap: 6px;
                        max-height: 150px;
                        overflow-y: auto;
                        scrollbar-width: thin;
                        scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                    }
                    
                    .recent-tickets-list::-webkit-scrollbar {
                        width: 4px;
                    }
                    
                    .recent-tickets-list::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    
                    .recent-tickets-list::-webkit-scrollbar-thumb {
                        background: rgba(255, 255, 255, 0.2);
                        border-radius: 2px;
                    }
                    
                    .ticket-item {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        padding: 8px;
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 6px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        transition: all 0.2s ease;
                        cursor: pointer;
                    }
                    
                    .ticket-item:hover {
                        background: rgba(255, 255, 255, 0.08);
                        transform: translateX(4px);
                        border-color: rgba(255, 255, 255, 0.2);
                    }
                    
                    .ticket-icon {
                        width: 24px;
                        height: 24px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 12px;
                        flex-shrink: 0;
                    }
                    
                    .ticket-priority-high {
                        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                        color: #ffffff;
                    }
                    
                    .ticket-priority-medium {
                        background: linear-gradient(135deg, #ffa726, #ff9800);
                        color: #ffffff;
                    }
                    
                    .ticket-priority-low {
                        background: linear-gradient(135deg, #66bb6a, #4caf50);
                        color: #ffffff;
                    }
                    
                    .ticket-content {
                        flex: 1;
                        min-width: 0;
                    }
                    
                    .ticket-title {
                        font-size: 12px;
                        font-weight: 600;
                        color: #ffffff;
                        margin-bottom: 2px;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }
                    
                    .ticket-meta {
                        font-size: 10px;
                        color: rgba(255, 255, 255, 0.7);
                    }
                    
                    .ticket-status {
                        font-size: 10px;
                        font-weight: 600;
                        padding: 3px 6px;
                        border-radius: 4px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        flex-shrink: 0;
                    }
                    
                    .ticket-status-open {
                        background: rgba(255, 193, 7, 0.2);
                        color: #ffc107;
                        border: 1px solid rgba(255, 193, 7, 0.3);
                    }
                    
                    .ticket-status-resolved {
                        background: rgba(76, 175, 80, 0.2);
                        color: #4caf50;
                        border: 1px solid rgba(76, 175, 80, 0.3);
                    }
                    
                    .ticket-status-closed {
                        background: rgba(158, 158, 158, 0.2);
                        color: #9e9e9e;
                        border: 1px solid rgba(158, 158, 158, 0.3);
                    }
                    
                    @media (max-width: 1200px) {
                        .user-profile-modal {
                            width: 95%;
                            height: 90vh;
                        }
                        
                        .user-profile-info {
                            grid-template-columns: 1fr 1fr;
                        }
                        
                        .user-profile-actions-consolidated {
                            gap: 8px;
                        }
                        
                        .action-icon-btn {
                            min-width: 100px;
                            padding: 10px 12px;
                            font-size: 13px;
                        }
                    }
                    
                    @media (max-width: 768px) {
                        .user-profile-modal {
                            width: 98%;
                            height: 95vh;
                        }
                        
                        .user-profile-modal-content {
                            padding: 16px;
                        }
                        
                        .user-profile-info {
                            grid-template-columns: 1fr;
                        }
                        
                        .user-profile-header {
                            flex-direction: column;
                            gap: 12px;
                            align-items: flex-start;
                        }
                        
                        .user-profile-actions-header {
                            gap: 6px;
                            flex-wrap: wrap;
                        }
                        
                        .action-icon-btn-header {
                            width: 28px;
                            height: 28px;
                        }
                        
                        .action-icon-btn-header i {
                            font-size: 11px;
                        }
                    }
                </style>
            `;
            document.head.insertAdjacentHTML('beforeend', styles);
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserProfileModule;
} else {
    window.UserProfileModule = UserProfileModule;
} 