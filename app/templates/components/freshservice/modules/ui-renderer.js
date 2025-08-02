<!-- FRESHSERVICE UI RENDERER MODULE -->
<script>
// Extend FreshServiceApp with UI rendering functionality
Object.assign(window.FreshServiceApp, {
    // Render tickets table
    renderTickets: function() {
        const tableBody = document.getElementById('ticketsTableBody');
        const ticketsTable = document.querySelector('.tickets-table-container');
        const emptyState = document.getElementById('emptyState');
        
        if (!tableBody) return;
        
        if (this.state.allTickets.length === 0) {
            if (ticketsTable) ticketsTable.style.display = 'none';
            if (emptyState) emptyState.style.display = 'flex';
            return;
        }
        
        if (ticketsTable) ticketsTable.style.display = 'block';
        if (emptyState) emptyState.style.display = 'none';
        
        tableBody.innerHTML = '';
        
        this.state.allTickets.forEach((ticket, index) => {
            const row = this.createTicketRow(ticket, index);
            tableBody.appendChild(row);
        });
    },

    // Create a single ticket row
    createTicketRow: function(ticket, index) {
        const row = document.createElement('tr');
        row.className = 'ticket-row';
        row.setAttribute('data-ticket-id', ticket.id);
        
        row.innerHTML = `
            <td class="checkbox-col">
                <input type="checkbox" class="form-check-input ticket-checkbox" data-ticket-id="${ticket.id}">
            </td>
            <td class="status-col">
                <span class="status-badge status-${ticket.status.toLowerCase()}">${ticket.status}</span>
            </td>
            <td class="subject-col">
                <div class="ticket-subject">${ticket.subject}</div>
                <div class="ticket-number">#${ticket.ticket_number}</div>
            </td>
            <td class="priority-col">
                <span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span>
            </td>
            <td class="modified-col">
                <div class="date-info">
                    <div class="date-main">${this.formatDate(ticket.updated_at)}</div>
                    <div class="date-secondary">${new Date(ticket.updated_at).toLocaleTimeString()}</div>
                </div>
            </td>
            <td class="requester-col">
                <div class="requester-info">
                    <div class="requester-avatar">${this.getInitials(ticket.requester.name)}</div>
                    <div class="requester-details">
                        <div class="requester-name">${ticket.requester.name}</div>
                        <div class="requester-email">${ticket.requester.email}</div>
                    </div>
                </div>
            </td>
        `;
        
        // Add click event to open ticket details
        row.addEventListener('click', (e) => {
            if (!e.target.classList.contains('ticket-checkbox')) {
                this.openTicketDetails(ticket.id, index);
            }
        });
        
        // Add checkbox event
        const checkbox = row.querySelector('.ticket-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                e.stopPropagation();
                this.handleTicketSelection(ticket.id, e.target.checked);
            });
        }
        
        return row;
    },

    // Render ticket details in modal
    renderTicketDetails: function(ticket) {
        const modalBody = document.getElementById('ticketDetailBody');
        const modalTitle = document.getElementById('ticketDetailTitle');
        
        if (!modalBody || !modalTitle) return;
        
        modalTitle.textContent = `Ticket #${ticket.ticket_number} - ${ticket.subject}`;
        
        modalBody.innerHTML = `
            <div class="ticket-detail-content">
                <div class="ticket-detail-header">
                    <h2 class="ticket-detail-title">${ticket.subject}</h2>
                    <div class="ticket-detail-meta">
                        <div class="meta-item">
                            <div class="meta-label">Status</div>
                            <div class="meta-value">
                                <span class="status-badge status-${ticket.status.toLowerCase()}">${ticket.status}</span>
                            </div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Priority</div>
                            <div class="meta-value">
                                <span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span>
                            </div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Requester</div>
                            <div class="meta-value">${ticket.requester.name}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Created</div>
                            <div class="meta-value">${new Date(ticket.created_at).toLocaleDateString()}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Updated</div>
                            <div class="meta-value">${new Date(ticket.updated_at).toLocaleDateString()}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Agent</div>
                            <div class="meta-value">${ticket.agent ? ticket.agent.name : 'Unassigned'}</div>
                        </div>
                    </div>
                </div>
                
                <div class="ticket-detail-description">
                    <h3 class="description-title">Description</h3>
                    <div class="description-content">${ticket.description || 'No description provided.'}</div>
                </div>
                
                <div class="ticket-detail-comments">
                    <h3 class="comments-title">Comments (${ticket.comments ? ticket.comments.length : 0})</h3>
                    ${this.renderComments(ticket.comments || [])}
                </div>
            </div>
        `;
        
        // Initialize modal navigation
        this.initModalNavigation();
    },

    // Render comments
    renderComments: function(comments) {
        if (comments.length === 0) {
            return '<p>No comments yet.</p>';
        }
        
        return comments.map(comment => `
            <div class="comment-item">
                <div class="comment-header">
                    <div class="requester-avatar">${this.getInitials(comment.author.name)}</div>
                    <div class="comment-author">${comment.author.name}</div>
                    <div class="comment-date">${this.formatDate(comment.created_at)}</div>
                </div>
                <div class="comment-content">${comment.body}</div>
            </div>
        `).join('');
    },

    // Open ticket details modal
    openTicketDetails: function(ticketId, index) {
        this.state.currentTicketIndex = index;
        this.loadTicketDetails(ticketId);
        
        const modal = new bootstrap.Modal(document.getElementById('ticketDetailModal'));
        modal.show();
    },

    // Initialize modal navigation
    initModalNavigation: function() {
        const prevButton = document.getElementById('prevTicket');
        const nextButton = document.getElementById('nextTicket');
        
        if (prevButton) {
            prevButton.addEventListener('click', () => {
                if (this.state.currentTicketIndex > 0) {
                    this.state.currentTicketIndex--;
                    const ticket = this.state.allTickets[this.state.currentTicketIndex];
                    this.openTicketDetails(ticket.id, this.state.currentTicketIndex);
                }
            });
        }
        
        if (nextButton) {
            nextButton.addEventListener('click', () => {
                if (this.state.currentTicketIndex < this.state.allTickets.length - 1) {
                    this.state.currentTicketIndex++;
                    const ticket = this.state.allTickets[this.state.currentTicketIndex];
                    this.openTicketDetails(ticket.id, this.state.currentTicketIndex);
                }
            });
        }
    },

    // Handle ticket selection
    handleTicketSelection: function(ticketId, isSelected) {
        const row = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
        if (row) {
            if (isSelected) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
            }
        }
        
        this.updateSelectAllCheckbox();
    },

    // Update select all checkbox
    updateSelectAllCheckbox: function() {
        const selectAllCheckbox = document.getElementById('selectAll');
        const ticketCheckboxes = document.querySelectorAll('.ticket-checkbox');
        
        if (!selectAllCheckbox || ticketCheckboxes.length === 0) return;
        
        const checkedBoxes = document.querySelectorAll('.ticket-checkbox:checked');
        
        if (checkedBoxes.length === 0) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = false;
        } else if (checkedBoxes.length === ticketCheckboxes.length) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = true;
        } else {
            selectAllCheckbox.indeterminate = true;
        }
    },

    // Initialize select all functionality
    initSelectAll: function() {
        const selectAllCheckbox = document.getElementById('selectAll');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                const ticketCheckboxes = document.querySelectorAll('.ticket-checkbox');
                ticketCheckboxes.forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                    const ticketId = checkbox.getAttribute('data-ticket-id');
                    this.handleTicketSelection(ticketId, e.target.checked);
                });
            });
        }
    }
});

// Initialize select all functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.FreshServiceApp) {
        window.FreshServiceApp.initSelectAll();
    }
});
</script> 