"""
Modal API Routes

These routes provide modal content for the YAM dashboard modal system.
"""

from flask import jsonify, request, render_template_string, current_app
from flask_login import login_required, current_user
import logging

logger = logging.getLogger(__name__)

from . import bp

# Modal content templates
MODAL_TEMPLATES = {
    'userPresenceModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-user-presence-map">
                <h4><i class="bi bi-people-fill"></i> User Presence Map</h4>
                <div class="yam-presence-grid">
                    <div class="yam-presence-card">
                        <div class="yam-presence-avatar">
                            <i class="bi bi-person-circle"></i>
                        </div>
                        <div class="yam-presence-info">
                            <h5>{{ current_user.username }}</h5>
                            <span class="yam-status online">Online</span>
                        </div>
                    </div>
                    <!-- Add more user presence cards here -->
                </div>
            </div>
        </div>
    ''',
    
    'userAnalyticsModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-user-analytics">
                <h4><i class="bi bi-graph-up"></i> User Analytics</h4>
                <div class="yam-analytics-grid">
                    <div class="yam-analytics-card">
                        <h5>Activity Overview</h5>
                        <div class="yam-chart-container">
                            <canvas id="userActivityChart"></canvas>
                        </div>
                    </div>
                    <div class="yam-analytics-card">
                        <h5>Performance Metrics</h5>
                        <div class="yam-metrics-list">
                            <div class="yam-metric">
                                <span>Login Time</span>
                                <span>2:30 PM</span>
                            </div>
                            <div class="yam-metric">
                                <span>Session Duration</span>
                                <span>4h 23m</span>
                            </div>
                            <div class="yam-metric">
                                <span>Actions Performed</span>
                                <span>47</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'activityHeatmapModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-activity-heatmap">
                <h4><i class="bi bi-calendar-heart"></i> Activity Heatmap</h4>
                <div class="yam-heatmap-container">
                    <div class="yam-heatmap-grid">
                        <!-- 7x24 grid for weekly activity -->
                        {% for day in range(7) %}
                            {% for hour in range(24) %}
                                <div class="yam-heatmap-cell" 
                                     data-day="{{ day }}" 
                                     data-hour="{{ hour }}"
                                     style="background-color: rgba(88, 101, 242, {{ (hour + day) % 10 / 10 }})">
                                </div>
                            {% endfor %}
                        {% endfor %}
                    </div>
                    <div class="yam-heatmap-legend">
                        <span>Less Active</span>
                        <div class="yam-legend-gradient"></div>
                        <span>More Active</span>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'advancedStatusModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-advanced-status">
                <h4><i class="bi bi-gear-wide-connected"></i> Advanced User Status</h4>
                <div class="yam-status-grid">
                    <div class="yam-status-card">
                        <h5>System Status</h5>
                        <div class="yam-status-indicators">
                            <div class="yam-status-item online">
                                <i class="bi bi-circle-fill"></i>
                                <span>Network</span>
                            </div>
                            <div class="yam-status-item online">
                                <i class="bi bi-circle-fill"></i>
                                <span>Database</span>
                            </div>
                            <div class="yam-status-item warning">
                                <i class="bi bi-circle-fill"></i>
                                <span>Cache</span>
                            </div>
                        </div>
                    </div>
                    <div class="yam-status-card">
                        <h5>User Permissions</h5>
                        <div class="yam-permissions-list">
                            <div class="yam-permission granted">
                                <i class="bi bi-check-circle"></i>
                                <span>Admin Access</span>
                            </div>
                            <div class="yam-permission granted">
                                <i class="bi bi-check-circle"></i>
                                <span>User Management</span>
                            </div>
                            <div class="yam-permission granted">
                                <i class="bi bi-check-circle"></i>
                                <span>System Monitoring</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'systemMonitorModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-system-monitor">
                <h4><i class="bi bi-cpu"></i> System Monitor</h4>
                <div class="yam-monitor-grid">
                    <div class="yam-monitor-card">
                        <h5>CPU Usage</h5>
                        <div class="yam-progress-ring">
                            <svg width="120" height="120">
                                <circle cx="60" cy="60" r="50" fill="none" stroke="#2f3136" stroke-width="8"/>
                                <circle cx="60" cy="60" r="50" fill="none" stroke="#5865f2" stroke-width="8" 
                                        stroke-dasharray="314" stroke-dashoffset="157" transform="rotate(-90 60 60)"/>
                            </svg>
                            <div class="yam-progress-text">50%</div>
                        </div>
                    </div>
                    <div class="yam-monitor-card">
                        <h5>Memory Usage</h5>
                        <div class="yam-progress-ring">
                            <svg width="120" height="120">
                                <circle cx="60" cy="60" r="50" fill="none" stroke="#2f3136" stroke-width="8"/>
                                <circle cx="60" cy="60" r="50" fill="none" stroke="#f093fb" stroke-width="8" 
                                        stroke-dasharray="314" stroke-dashoffset="94" transform="rotate(-90 60 60)"/>
                            </svg>
                            <div class="yam-progress-text">70%</div>
                        </div>
                    </div>
                    <div class="yam-monitor-card">
                        <h5>Disk Usage</h5>
                        <div class="yam-progress-ring">
                            <svg width="120" height="120">
                                <circle cx="60" cy="60" r="50" fill="none" stroke="#2f3136" stroke-width="8"/>
                                <circle cx="60" cy="60" r="50" fill="none" stroke="#f5576c" stroke-width="8" 
                                        stroke-dasharray="314" stroke-dashoffset="47" transform="rotate(-90 60 60)"/>
                            </svg>
                            <div class="yam-progress-text">85%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'systemHealthModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-system-health">
                <h4><i class="bi bi-heart-pulse"></i> System Health Monitor</h4>
                <div class="yam-health-grid">
                    <div class="yam-health-card healthy">
                        <h5>Overall Health</h5>
                        <div class="yam-health-score">
                            <span class="yam-score">92%</span>
                            <span class="yam-status">Healthy</span>
                        </div>
                    </div>
                    <div class="yam-health-card">
                        <h5>Service Status</h5>
                        <div class="yam-service-list">
                            <div class="yam-service online">
                                <i class="bi bi-circle-fill"></i>
                                <span>Web Server</span>
                            </div>
                            <div class="yam-service online">
                                <i class="bi bi-circle-fill"></i>
                                <span>Database</span>
                            </div>
                            <div class="yam-service online">
                                <i class="bi bi-circle-fill"></i>
                                <span>Cache Service</span>
                            </div>
                            <div class="yam-service warning">
                                <i class="bi bi-circle-fill"></i>
                                <span>Email Service</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'teamPerformanceModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-team-performance">
                <h4><i class="bi bi-trophy"></i> Team Performance Analytics</h4>
                <div class="yam-performance-grid">
                    <div class="yam-performance-card">
                        <h5>Team Metrics</h5>
                        <div class="yam-metrics-grid">
                            <div class="yam-metric">
                                <span>Active Users</span>
                                <span class="yam-value">24</span>
                            </div>
                            <div class="yam-metric">
                                <span>Tasks Completed</span>
                                <span class="yam-value">156</span>
                            </div>
                            <div class="yam-metric">
                                <span>Response Time</span>
                                <span class="yam-value">2.3s</span>
                            </div>
                        </div>
                    </div>
                    <div class="yam-performance-card">
                        <h5>Performance Chart</h5>
                        <div class="yam-chart-container">
                            <canvas id="teamPerformanceChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'teamCollaborationModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-team-collaboration">
                <h4><i class="bi bi-people"></i> Team Collaboration</h4>
                <div class="yam-collaboration-grid">
                    <div class="yam-collaboration-card">
                        <h5>Active Projects</h5>
                        <div class="yam-project-list">
                            <div class="yam-project">
                                <span class="yam-project-name">System Migration</span>
                                <span class="yam-project-progress">75%</span>
                            </div>
                            <div class="yam-project">
                                <span class="yam-project-name">Security Update</span>
                                <span class="yam-project-progress">90%</span>
                            </div>
                            <div class="yam-project">
                                <span class="yam-project-name">User Training</span>
                                <span class="yam-project-progress">45%</span>
                            </div>
                        </div>
                    </div>
                    <div class="yam-collaboration-card">
                        <h5>Team Members</h5>
                        <div class="yam-team-members">
                            <div class="yam-member">
                                <div class="yam-member-avatar">
                                    <i class="bi bi-person-circle"></i>
                                </div>
                                <div class="yam-member-info">
                                    <span class="yam-member-name">John Doe</span>
                                    <span class="yam-member-role">Admin</span>
                                </div>
                                <span class="yam-member-status online"></span>
                            </div>
                            <div class="yam-member">
                                <div class="yam-member-avatar">
                                    <i class="bi bi-person-circle"></i>
                                </div>
                                <div class="yam-member-info">
                                    <span class="yam-member-name">Jane Smith</span>
                                    <span class="yam-member-role">Developer</span>
                                </div>
                                <span class="yam-member-status online"></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'recentActivityModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-recent-activity">
                <h4><i class="bi bi-clock-history"></i> Recent Activity</h4>
                <div class="yam-activity-list">
                    <div class="yam-activity-item">
                        <div class="yam-activity-icon">
                            <i class="bi bi-person-plus"></i>
                        </div>
                        <div class="yam-activity-content">
                            <span class="yam-activity-text">New user registered</span>
                            <span class="yam-activity-time">2 minutes ago</span>
                        </div>
                    </div>
                    <div class="yam-activity-item">
                        <div class="yam-activity-icon">
                            <i class="bi bi-gear"></i>
                        </div>
                        <div class="yam-activity-content">
                            <span class="yam-activity-text">System settings updated</span>
                            <span class="yam-activity-time">5 minutes ago</span>
                        </div>
                    </div>
                    <div class="yam-activity-item">
                        <div class="yam-activity-icon">
                            <i class="bi bi-file-earmark-text"></i>
                        </div>
                        <div class="yam-activity-content">
                            <span class="yam-activity-text">Report generated</span>
                            <span class="yam-activity-time">10 minutes ago</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'activityTrackerModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-activity-tracker">
                <h4><i class="bi bi-activity"></i> User Activity Tracker</h4>
                <div class="yam-tracker-grid">
                    <div class="yam-tracker-card">
                        <h5>Today's Activity</h5>
                        <div class="yam-activity-stats">
                            <div class="yam-stat">
                                <span class="yam-stat-label">Logins</span>
                                <span class="yam-stat-value">3</span>
                            </div>
                            <div class="yam-stat">
                                <span class="yam-stat-label">Actions</span>
                                <span class="yam-stat-value">47</span>
                            </div>
                            <div class="yam-stat">
                                <span class="yam-stat-label">Searches</span>
                                <span class="yam-stat-value">12</span>
                            </div>
                        </div>
                    </div>
                    <div class="yam-tracker-card">
                        <h5>Activity Timeline</h5>
                        <div class="yam-timeline">
                            <div class="yam-timeline-item">
                                <span class="yam-timeline-time">2:30 PM</span>
                                <span class="yam-timeline-event">Logged in</span>
                            </div>
                            <div class="yam-timeline-item">
                                <span class="yam-timeline-time">2:35 PM</span>
                                <span class="yam-timeline-event">Viewed dashboard</span>
                            </div>
                            <div class="yam-timeline-item">
                                <span class="yam-timeline-time">2:40 PM</span>
                                <span class="yam-timeline-event">Searched for user</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'notificationsModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-notifications">
                <h4><i class="bi bi-bell"></i> Notifications</h4>
                <div class="yam-notifications-list">
                    <div class="yam-notification unread">
                        <div class="yam-notification-icon">
                            <i class="bi bi-exclamation-triangle"></i>
                        </div>
                        <div class="yam-notification-content">
                            <span class="yam-notification-title">System Alert</span>
                            <span class="yam-notification-message">High CPU usage detected</span>
                            <span class="yam-notification-time">5 minutes ago</span>
                        </div>
                        <button class="yam-notification-close">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <div class="yam-notification">
                        <div class="yam-notification-icon">
                            <i class="bi bi-info-circle"></i>
                        </div>
                        <div class="yam-notification-content">
                            <span class="yam-notification-title">Update Available</span>
                            <span class="yam-notification-message">New version ready for installation</span>
                            <span class="yam-notification-time">1 hour ago</span>
                        </div>
                        <button class="yam-notification-close">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    ''',
    
    'teamChatModal': '''
        <div class="yam-modal-full-content">
            <div class="yam-team-chat">
                <h4><i class="bi bi-chat-dots"></i> Team Chat</h4>
                <div class="yam-chat-container">
                    <div class="yam-chat-messages">
                        <div class="yam-message">
                            <div class="yam-message-avatar">
                                <i class="bi bi-person-circle"></i>
                            </div>
                            <div class="yam-message-content">
                                <span class="yam-message-author">John Doe</span>
                                <span class="yam-message-text">Has anyone seen the latest system logs?</span>
                                <span class="yam-message-time">2:30 PM</span>
                            </div>
                        </div>
                        <div class="yam-message">
                            <div class="yam-message-avatar">
                                <i class="bi bi-person-circle"></i>
                            </div>
                            <div class="yam-message-content">
                                <span class="yam-message-author">Jane Smith</span>
                                <span class="yam-message-text">I'll check them now</span>
                                <span class="yam-message-time">2:32 PM</span>
                            </div>
                        </div>
                    </div>
                    <div class="yam-chat-input">
                        <input type="text" placeholder="Type a message..." class="yam-chat-textbox">
                        <button class="yam-chat-send">
                            <i class="bi bi-send"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    '''
}

@bp.route('/<modal_type>', methods=['POST'])
@login_required
def get_modal_content(modal_type):
    """Get modal content for the specified modal type."""
    try:
        # Get request data
        data = request.get_json() or {}
        modal_data = data.get('data', {})
        options = data.get('options', {})
        
        # Check if modal type exists
        if modal_type not in MODAL_TEMPLATES:
            return jsonify({
                'error': f'Modal type "{modal_type}" not found'
            }), 404
        
        # Get the template for this modal type
        template = MODAL_TEMPLATES[modal_type]
        
        # Render the template with current user context
        content = render_template_string(template, current_user=current_user)
        
        # Return the content
        return jsonify({
            'content': content,
            'modal_type': modal_type,
            'success': True
        })
        
    except Exception as e:
        logger.error(f'Error getting modal content for {modal_type}: {e}')
        return jsonify({
            'error': f'Failed to load modal content: {str(e)}'
        }), 500

@bp.route('/list', methods=['GET'])
@login_required
def list_modals():
    """List all available modal types."""
    return jsonify({
        'modals': list(MODAL_TEMPLATES.keys()),
        'count': len(MODAL_TEMPLATES)
    }) 