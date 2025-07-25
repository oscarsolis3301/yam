// Ticket Module
// Handles ticket modals and ticket-related functionality

class TicketModule {
    constructor() {
        this.addTicketModalStyles();
    }
    
    showTicketModal(ticketId, title, priority, status) {
        console.log('Ticket Module: showTicketModal called with:', { ticketId, title, priority, status });
        
        // Generate dummy ticket data based on the ticket ID
        const ticketData = this.generateDummyTicketData(ticketId, title, priority, status);
        
        // Create modal HTML
        const modalHTML = `
            <div id="ticketModal" class="ticket-modal-overlay">
                <div class="ticket-modal">
                    <div class="ticket-modal-header">
                        <h3><i class="bi bi-ticket-detailed"></i> ${ticketData.title}</h3>
                        <button class="ticket-modal-close" onclick="window.closeTicketModal()">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                    <div class="ticket-modal-content">
                        <div class="ticket-details">
                            <div class="ticket-section">
                                <h4><i class="bi bi-info-circle"></i> Ticket Information</h4>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Ticket ID</span>
                                    <span class="ticket-field-value">${ticketData.id}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Status</span>
                                    <span class="ticket-field-value">
                                        <span class="ticket-status ticket-status-${ticketData.status}">${ticketData.status}</span>
                                    </span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Priority</span>
                                    <span class="ticket-field-value">
                                        <span class="ticket-priority ticket-priority-${ticketData.priority}">${ticketData.priority}</span>
                                    </span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Category</span>
                                    <span class="ticket-field-value">${ticketData.category}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Created</span>
                                    <span class="ticket-field-value">${ticketData.created}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Updated</span>
                                    <span class="ticket-field-value">${ticketData.updated}</span>
                                </div>
                            </div>
                            
                            <div class="ticket-section">
                                <h4><i class="bi bi-person"></i> User Information</h4>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Requester</span>
                                    <span class="ticket-field-value">${ticketData.requester}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Department</span>
                                    <span class="ticket-field-value">${ticketData.department}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Location</span>
                                    <span class="ticket-field-value">${ticketData.location}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Contact</span>
                                    <span class="ticket-field-value">${ticketData.contact}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Assigned To</span>
                                    <span class="ticket-field-value">${ticketData.assignedTo}</span>
                                </div>
                                <div class="ticket-field">
                                    <span class="ticket-field-label">Escalation</span>
                                    <span class="ticket-field-value">${ticketData.escalation}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="ticket-description">
                            <h4><i class="bi bi-chat-text"></i> Description</h4>
                            <p class="ticket-description-text">${ticketData.description}</p>
                        </div>
                        
                        <div class="ticket-timeline">
                            <h4><i class="bi bi-clock-history"></i> Timeline</h4>
                            ${ticketData.timeline.map(item => `
                                <div class="timeline-item">
                                    <div class="timeline-icon ticket-priority-${item.priority}">
                                        <i class="bi ${item.icon}"></i>
                                    </div>
                                    <div class="timeline-content">
                                        <div class="timeline-action">${item.action}</div>
                                        <div class="timeline-meta">${item.meta}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        
                        <div class="ticket-actions">
                            <button class="ticket-action-btn" onclick="window.editTicket('${ticketId}')">
                                <i class="bi bi-pencil"></i>
                                Edit Ticket
                            </button>
                            <button class="ticket-action-btn" onclick="window.addComment('${ticketId}')">
                                <i class="bi bi-chat"></i>
                                Add Comment
                            </button>
                            <button class="ticket-action-btn" onclick="window.escalateTicket('${ticketId}')">
                                <i class="bi bi-arrow-up"></i>
                                Escalate
                            </button>
                            <button class="ticket-action-btn" onclick="window.closeTicket('${ticketId}')">
                                <i class="bi bi-check-circle"></i>
                                Close Ticket
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add click outside to close functionality
        const modalOverlay = document.getElementById('ticketModal');
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                this.closeTicketModal();
            }
        });
        
        // Add escape key to close functionality
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                this.closeTicketModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        // Add global close function
        window.closeTicketModal = () => {
            this.closeTicketModal();
        };
        
        // Add ticket action handlers
        window.editTicket = (ticketId) => {
            alert(`Edit ticket ${ticketId} - This would open the edit form`);
        };
        
        window.addComment = (ticketId) => {
            alert(`Add comment to ticket ${ticketId} - This would open the comment form`);
        };
        
        window.escalateTicket = (ticketId) => {
            alert(`Escalate ticket ${ticketId} - This would escalate the ticket`);
        };
        
        window.closeTicket = (ticketId) => {
            if (confirm('Are you sure you want to close this ticket?')) {
                alert(`Ticket ${ticketId} closed successfully`);
                this.closeTicketModal();
            }
        };
    }
    
    generateDummyTicketData(ticketId, title, priority, status) {
        const priorities = {
            high: { color: '#ff6b6b', icon: 'bi-exclamation-triangle' },
            medium: { color: '#ffa726', icon: 'bi-exclamation-circle' },
            low: { color: '#66bb6a', icon: 'bi-info-circle' }
        };
        
        const categories = [
            'Hardware', 'Software', 'Network', 'Access', 'Account', 'Email', 'Printing', 'Security'
        ];
        
        const departments = [
            'IT Support', 'HR', 'Finance', 'Operations', 'Sales', 'Marketing', 'Engineering'
        ];
        
        const locations = [
            'Main Office', 'Branch A', 'Branch B', 'Remote', 'HQ', 'Satellite Office'
        ];
        
        const assignees = [
            'John Smith', 'Sarah Johnson', 'Mike Davis', 'Lisa Wilson', 'David Brown', 'Emily Chen'
        ];
        
        const descriptions = {
            'TK-2024-001': 'User is unable to log into their account and has been locked out after multiple failed attempts. Need immediate password reset and account unlock.',
            'TK-2024-002': 'Request for installation of Adobe Creative Suite and Microsoft Office 365 on user workstation. User needs these applications for daily work tasks.',
            'TK-2024-003': 'General inquiry about VPN access and remote work setup. User wants to understand the process for working from home.',
            'TK-2024-004': 'Printer is not responding and showing offline status. Need to troubleshoot network connectivity and driver issues.',
            'TK-2024-005': 'User experiencing intermittent network connectivity issues. Connection drops frequently and affects work productivity.',
            'TK-2024-006': 'Keyboard keys are sticking and some are not responding. Need replacement keyboard for user workstation.',
            'TK-2024-007': 'Security update required for user workstation. System is showing outdated antivirus definitions.',
            'TK-2024-008': 'Audio equipment not working properly. Headphones and microphone need configuration or replacement.'
        };
        
        const timelines = {
            'TK-2024-001': [
                { action: 'Ticket Created', meta: '2 hours ago by User', priority: 'high', icon: 'bi-plus-circle' },
                { action: 'Assigned to IT Support', meta: '1 hour 45 minutes ago by System', priority: 'medium', icon: 'bi-person-check' },
                { action: 'Password Reset Initiated', meta: '1 hour 30 minutes ago by John Smith', priority: 'high', icon: 'bi-key' },
                { action: 'Account Unlocked', meta: '1 hour 15 minutes ago by John Smith', priority: 'high', icon: 'bi-unlock' }
            ],
            'TK-2024-002': [
                { action: 'Ticket Created', meta: '1 day ago by User', priority: 'medium', icon: 'bi-plus-circle' },
                { action: 'Assigned to IT Support', meta: '23 hours ago by System', priority: 'medium', icon: 'bi-person-check' },
                { action: 'Software Installation Started', meta: '22 hours ago by Sarah Johnson', priority: 'medium', icon: 'bi-download' },
                { action: 'Installation Completed', meta: '21 hours ago by Sarah Johnson', priority: 'medium', icon: 'bi-check-circle' },
                { action: 'Ticket Resolved', meta: '20 hours ago by Sarah Johnson', priority: 'medium', icon: 'bi-check-double' }
            ],
            'TK-2024-003': [
                { action: 'Ticket Created', meta: '3 days ago by User', priority: 'low', icon: 'bi-plus-circle' },
                { action: 'Assigned to IT Support', meta: '2 days 23 hours ago by System', priority: 'low', icon: 'bi-person-check' },
                { action: 'Information Provided', meta: '2 days 22 hours ago by Mike Davis', priority: 'low', icon: 'bi-chat-text' },
                { action: 'Ticket Closed', meta: '2 days 21 hours ago by Mike Davis', priority: 'low', icon: 'bi-x-circle' }
            ]
        };
        
        // Generate random data for tickets not in the predefined lists
        const randomCategory = categories[Math.floor(Math.random() * categories.length)];
        const randomDepartment = departments[Math.floor(Math.random() * departments.length)];
        const randomLocation = locations[Math.floor(Math.random() * locations.length)];
        const randomAssignee = assignees[Math.floor(Math.random() * assignees.length)];
        
        const description = descriptions[ticketId] || `Standard ${randomCategory.toLowerCase()} issue requiring attention. User has reported problems with their system and needs assistance.`;
        
        const timeline = timelines[ticketId] || [
            { action: 'Ticket Created', meta: '1 week ago by User', priority: 'medium', icon: 'bi-plus-circle' },
            { action: 'Assigned to IT Support', meta: '6 days 23 hours ago by System', priority: 'medium', icon: 'bi-person-check' },
            { action: 'Work Started', meta: '6 days 22 hours ago by ' + randomAssignee, priority: 'medium', icon: 'bi-play-circle' },
            { action: 'Issue Resolved', meta: '6 days 21 hours ago by ' + randomAssignee, priority: 'medium', icon: 'bi-check-circle' },
            { action: 'Ticket Closed', meta: '6 days 20 hours ago by ' + randomAssignee, priority: 'medium', icon: 'bi-x-circle' }
        ];
        
        return {
            id: ticketId,
            title: title,
            status: status,
            priority: priority,
            category: randomCategory,
            created: '2024-01-15 09:30:00',
            updated: '2024-01-15 11:45:00',
            requester: 'John Doe',
            department: randomDepartment,
            location: randomLocation,
            contact: 'john.doe@company.com',
            assignedTo: randomAssignee,
            escalation: 'None',
            description: description,
            timeline: timeline
        };
    }
    
    closeTicketModal() {
        const modal = document.getElementById('ticketModal');
        if (modal) {
            modal.remove();
        }
    }
    
    addTicketModalStyles() {
        if (!document.getElementById('ticketModalStyles')) {
            const styles = `
                <style id="ticketModalStyles">
                    /* Ticket Modal Styles */
                    .ticket-modal-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.8);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 99999999;
                        animation: overlayFadeIn 0.2s ease-out;
                    }
                    
                    .ticket-modal {
                        background: #1a1a1a;
                        border-radius: 16px;
                        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.1);
                        width: 95%;
                        max-width: 800px;
                        max-height: 90vh;
                        overflow: hidden;
                        animation: modalBounceIn 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        display: flex;
                        flex-direction: column;
                    }
                    
                    .ticket-modal-header {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        padding: 20px 24px;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                        background: #2a2a2a;
                        position: relative;
                        flex-shrink: 0;
                    }
                    
                    .ticket-modal-header h3 {
                        margin: 0;
                        color: #ffffff;
                        font-size: 18px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }
                    
                    .ticket-modal-close {
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
                    
                    .ticket-modal-close:hover {
                        background: rgba(255, 255, 255, 0.2);
                        transform: rotate(90deg) scale(1.1);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                    }
                    
                    .ticket-modal-content {
                        padding: 20px;
                        flex: 1;
                        overflow-y: auto;
                        scrollbar-width: thin;
                        scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                    }
                    
                    .ticket-modal-content::-webkit-scrollbar {
                        width: 4px;
                    }
                    
                    .ticket-modal-content::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    
                    .ticket-modal-content::-webkit-scrollbar-thumb {
                        background: rgba(255, 255, 255, 0.2);
                        border-radius: 2px;
                    }
                    
                    .ticket-details {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                        margin-bottom: 20px;
                    }
                    
                    .ticket-section {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 16px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                    }
                    
                    .ticket-section h4 {
                        margin: 0 0 12px 0;
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    
                    .ticket-field {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 6px 0;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    }
                    
                    .ticket-field:last-child {
                        border-bottom: none;
                    }
                    
                    .ticket-field-label {
                        color: rgba(255, 255, 255, 0.7);
                        font-size: 12px;
                        font-weight: 500;
                    }
                    
                    .ticket-field-value {
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: 500;
                        text-align: right;
                        max-width: 60%;
                        word-break: break-word;
                    }
                    
                    .ticket-description {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 16px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        margin-bottom: 20px;
                    }
                    
                    .ticket-description h4 {
                        margin: 0 0 12px 0;
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    
                    .ticket-description-text {
                        color: #ffffff;
                        font-size: 13px;
                        line-height: 1.5;
                        margin: 0;
                    }
                    
                    .ticket-timeline {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 16px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                    }
                    
                    .ticket-timeline h4 {
                        margin: 0 0 12px 0;
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    
                    .timeline-item {
                        display: flex;
                        gap: 12px;
                        padding: 8px 0;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    }
                    
                    .timeline-item:last-child {
                        border-bottom: none;
                    }
                    
                    .timeline-icon {
                        width: 24px;
                        height: 24px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 12px;
                        flex-shrink: 0;
                        margin-top: 2px;
                    }
                    
                    .timeline-content {
                        flex: 1;
                    }
                    
                    .timeline-action {
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: 600;
                        margin-bottom: 2px;
                    }
                    
                    .timeline-meta {
                        color: rgba(255, 255, 255, 0.7);
                        font-size: 11px;
                    }
                    
                    .ticket-actions {
                        display: flex;
                        gap: 8px;
                        justify-content: flex-end;
                        margin-top: 16px;
                    }
                    
                    .ticket-action-btn {
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        color: #ffffff;
                        padding: 8px 16px;
                        border-radius: 8px;
                        cursor: pointer;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        text-decoration: none;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        font-size: 12px;
                        font-weight: 500;
                    }
                    
                    .ticket-action-btn:hover {
                        background: rgba(255, 255, 255, 0.2);
                        transform: translateY(-2px);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                    }
                    
                    .ticket-status {
                        padding: 3px 6px;
                        border-radius: 4px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        font-size: 10px;
                        font-weight: 600;
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
                    
                    .ticket-priority {
                        padding: 3px 8px;
                        border-radius: 12px;
                        font-size: 10px;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    
                    .ticket-priority-high {
                        background: rgba(244, 67, 54, 0.2);
                        color: #f44336;
                        border: 1px solid rgba(244, 67, 54, 0.3);
                    }
                    
                    .ticket-priority-medium {
                        background: rgba(255, 152, 0, 0.2);
                        color: #ff9800;
                        border: 1px solid rgba(255, 152, 0, 0.3);
                    }
                    
                    .ticket-priority-low {
                        background: rgba(76, 175, 80, 0.2);
                        color: #4caf50;
                        border: 1px solid rgba(76, 175, 80, 0.3);
                    }
                    
                    @media (max-width: 768px) {
                        .ticket-modal {
                            width: 98%;
                            max-height: 95vh;
                        }
                        
                        .ticket-details {
                            grid-template-columns: 1fr;
                        }
                        
                        .ticket-actions {
                            flex-direction: column;
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
    module.exports = TicketModule;
} else {
    window.TicketModule = TicketModule;
} 