from flask import jsonify, request, render_template
from flask_login import login_required, current_user
from . import bp
from extensions import db, socketio
from app.models import Outage
from app.config import FRESH_ENDPOINT, FRESH_API, TICKET_STATUSES, TICKET_SOURCES, TICKET_PRIORITIES
import logging
import requests
import datetime
import json

logger = logging.getLogger(__name__)

# Constants for ticket status mapping
statuses = {
    2: "Open",
    3: "Pending",
    4: "Resolved",
    5: "Closed"
}

source = {
    1: "Email",
    2: "Portal",
    3: "Phone",
    4: "Chat",
    5: "Feedback Widget",
    6: "Outbound Email"
}

priorities = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Urgent"
}

@bp.route('/')
@login_required
def outages():
    """Render the outages page"""
    # Template relocated to the root templates folder (app/templates/outages.html)
    return render_template('outages.html', active_page='outages')

@bp.route('/<int:outage_id>')
@login_required
def view_outage(outage_id):
    """View a specific outage"""
    try:
        outage = Outage.query.get_or_404(outage_id)
        return render_template('outages/outage_detail.html', outage=outage)
    except Exception as e:
        logger.error(f"Error viewing outage {outage_id}: {str(e)}")
        return render_template('404.html'), 404

@bp.route('/api/outages', methods=['GET'])
@login_required
def get_outages():
    """Get all outages"""
    try:
        outages = Outage.query.all()
        return jsonify([outage.to_dict() for outage in outages])
    except Exception as e:
        logger.error(f"Error getting outages: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/outages', methods=['POST'])
@login_required
def create_outage():
    """Create a new outage"""
    try:
        data = request.get_json()
        outage = Outage(
            title=data['title'],
            description=data['description'],
            status=data.get('status', 'active'),
            severity=data.get('severity', 'medium'),
            created_by=current_user.id
        )
        db.session.add(outage)
        db.session.commit()
        
        # Emit socket event
        socketio.emit('new_outage', outage.to_dict())
        
        return jsonify(outage.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating outage: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/outages/<int:outage_id>', methods=['GET'])
@login_required
def get_outage(outage_id):
    """Get a specific outage"""
    try:
        outage = Outage.query.get_or_404(outage_id)
        return jsonify(outage.to_dict())
    except Exception as e:
        logger.error(f"Error getting outage {outage_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/outages/<int:outage_id>', methods=['PUT'])
@login_required
def update_outage(outage_id):
    """Update an outage"""
    try:
        outage = Outage.query.get_or_404(outage_id)
        data = request.get_json()
        
        for key, value in data.items():
            if hasattr(outage, key):
                setattr(outage, key, value)
        
        db.session.commit()
        
        # Emit socket event
        socketio.emit('outage_update', outage.to_dict())
        
        return jsonify(outage.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating outage {outage_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/outages/<int:outage_id>/resolve', methods=['POST'])
@login_required
def resolve_outage(outage_id):
    """Resolve an outage"""
    try:
        outage = Outage.query.get_or_404(outage_id)
        outage.status = 'resolved'
        db.session.commit()
        
        # Emit socket event
        socketio.emit('outage_update', outage.to_dict())
        
        return jsonify(outage.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resolving outage {outage_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/outages/<int:outage_id>', methods=['DELETE'])
@login_required
def delete_outage(outage_id):
    """Delete an outage"""
    try:
        outage = Outage.query.get_or_404(outage_id)
        outage_data = outage.to_dict()
        db.session.delete(outage)
        db.session.commit()
        
        # Emit socket event
        socketio.emit('outage_deleted', outage_data)
        
        return '', 204
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting outage {outage_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/all', methods=['GET', 'POST'])
@login_required
def all_outages():
    ticket = request.args.get('ticket')

    if ticket:
        print("Fetching data from API...")
        ticket_response = requests.get(f"{FRESH_ENDPOINT}tickets/{str(ticket)}?include=conversations", auth=(FRESH_API, 'PARENT_TICKET'))

        if ticket_response.status_code != 200:
            print(f"Failed to fetch activities. Status code: {ticket_response.status_code}")
        else:
            ticket = ticket_response.json()

            with open('ticket_data.json', 'w', encoding='utf-8') as f:
                json.dump(ticket, f, ensure_ascii=False, indent=4)
            print("Data saved successfully.")

            ticket_info = {}

            ticket_info["ticket_number"] = ticket['ticket']['id']
            ticket_info["title"] = ticket['ticket']['subject']
            ticket_info['description'] = ticket['ticket']['description_text']
            date = datetime.datetime.strptime(str(ticket['ticket']['created_at']), "%Y-%m-%dT%H:%M:%SZ")
            ticket_info['created_date'] = date.strftime("%m-%d-%Y")
            ticket_info["status"] = TICKET_STATUSES[int(ticket['ticket']['status'])]
            ticket_info['source'] = TICKET_SOURCES[int(ticket['ticket']['source'])]
            ticket_info['priority'] = TICKET_PRIORITIES[int(ticket['ticket']['priority'])]
            ticket_info['category'] = ticket['ticket']['category']
            ticket_info['subcat'] = ticket['ticket']['sub_category']
            ticket_info['itemcat'] = ticket['ticket']['item_category']
            
            return render_template('outages/spark1.html', ticket=ticket_info)

    else:
        ticket_info = {}
        data = {}

        try:
            all_tickets_request = requests.get(f"{FRESH_ENDPOINT}tickets/filter?query=\"tag:spark\"", auth=(FRESH_API, 'TICKETS'))
            all_tickets = all_tickets_request.json().get('tickets', [])
            print(all_tickets)
            filtered_tickets = []
            
            for item in all_tickets:
                ticket = {}
                ticket["ticket_number"] = item['id']
                ticket["title"] = item['subject']
                ticket['description'] = item['description_text']
                date = datetime.datetime.strptime(str(item['created_at']), "%Y-%m-%dT%H:%M:%SZ")
                ticket['created_date'] = date.strftime("%m-%d-%Y")
                ticket["status"] = TICKET_STATUSES[int(item['status'])]
                ticket['source'] = TICKET_SOURCES[int(item['source'])]
                ticket['priority'] = TICKET_PRIORITIES[int(item['priority'])]
                ticket['category'] = item['category']
                ticket['subcat'] = item['sub_category']
                ticket['itemcat'] = item['item_category']
                ticket['status_code'] = int(item['status'])
                filtered_tickets.append(ticket)
        except Exception as e:
            print(f"Failed. {e}")
            logger.error(f"Error fetching tickets: {str(e)}")
    return render_template('outages/spark3.html', tickets=filtered_tickets)

@bp.route('/previous', methods=['GET', 'POST'])
@login_required
def previous_outages():
    filtered_tickets = []
    ticket_info = {}

    ticket = request.args.get('ticket')

    if ticket:
        print("Fetching data from API...")
        ticket_response = requests.get(f"{FRESH_ENDPOINT}tickets/{str(ticket)}?include=conversations", auth=(FRESH_API, 'PARENT_TICKET'))

        if ticket_response.status_code != 200:
            print(f"Failed to fetch activities. Status code: {ticket_response.status_code}")
        else:
            ticket = ticket_response.json()

            with open('ticket_data.json', 'w', encoding='utf-8') as f:
                json.dump(ticket, f, ensure_ascii=False, indent=4)
            print("Data saved successfully.")
            ticket_info["ticket_number"] = ticket['ticket']['id']
            ticket_info["title"] = ticket['ticket']['subject']
            ticket_info['description'] = ticket['ticket']['description_text']
            date = datetime.datetime.strptime(str(ticket['ticket']['created_at']), "%Y-%m-%dT%H:%M:%SZ")
            ticket_info['created_date'] = date.strftime("%m-%d-%Y")
            ticket_info["status"] = TICKET_STATUSES[int(ticket['ticket']['status'])]
            ticket_info['source'] = TICKET_SOURCES[int(ticket['ticket']['source'])]
            ticket_info['priority'] = TICKET_PRIORITIES[int(ticket['ticket']['priority'])]
            ticket_info['category'] = ticket['ticket']['category']
            ticket_info['subcat'] = ticket['ticket']['sub_category']
            ticket_info['itemcat'] = ticket['ticket']['item_category']
            return render_template('outages/spark1.html', ticket=ticket_info)

    else:
        ticket_info = {}
        data = {}

        try:
            all_tickets_request = requests.get(f"{FRESH_ENDPOINT}tickets/filter?query=\"tag:spark AND status:4 OR tag:spark AND status:5\"", auth=(FRESH_API, 'TICKETS'))
            all_tickets = all_tickets_request.json().get('tickets', [])
            print(all_tickets)
            
            for item in all_tickets:
                ticket = {}
                ticket["ticket_number"] = item['id']
                ticket["title"] = item['subject']
                ticket['description'] = item['description_text']
                date = datetime.datetime.strptime(str(item['created_at']), "%Y-%m-%dT%H:%M:%SZ")
                ticket['created_date'] = date.strftime("%m-%d-%Y")
                ticket["status"] = TICKET_STATUSES[int(item['status'])]
                ticket['source'] = TICKET_SOURCES[int(item['source'])]
                ticket['priority'] = TICKET_PRIORITIES[int(item['priority'])]
                ticket['category'] = item['category']
                ticket['subcat'] = item['sub_category']
                ticket['itemcat'] = item['item_category']
                ticket['status_code'] = int(item['status'])
                filtered_tickets.append(ticket)

        except Exception as e:
            print(f"Failed. {e}")
            logger.error(f"Error fetching tickets: {str(e)}")
    return render_template('outages/spark3.html', tickets=filtered_tickets)

@bp.route('/current', methods=['GET', 'POST'])
@login_required
def current_outages():
    ticket_info = {}
    data = {}
    filtered_tickets = []
    ticket = request.args.get('ticket')

    if ticket:
        print("Fetching data from API...")
        ticket_response = requests.get(f"{FRESH_ENDPOINT}tickets/{str(ticket)}?include=conversations", auth=(FRESH_API, 'PARENT_TICKET'))

        if ticket_response.status_code != 200:
            print(f"Failed to fetch activities. Status code: {ticket_response.status_code}")
        else:
            ticket = ticket_response.json()
            with open('ticket_data.json', 'w', encoding='utf-8') as f:
                json.dump(ticket, f, ensure_ascii=False, indent=4)
            print("Data saved successfully.")
            ticket_info["ticket_number"] = ticket['ticket']['id']
            ticket_info["title"] = ticket['ticket']['subject']
            ticket_info['description'] = ticket['ticket']['description_text']
            date = datetime.datetime.strptime(str(ticket['ticket']['created_at']), "%Y-%m-%dT%H:%M:%SZ")
            ticket_info['created_date'] = date.strftime("%m-%d-%Y")
            ticket_info["status"] = TICKET_STATUSES[int(ticket['ticket']['status'])]
            ticket_info['source'] = TICKET_SOURCES[int(ticket['ticket']['source'])]
            ticket_info['priority'] = TICKET_PRIORITIES[int(ticket['ticket']['priority'])]
            ticket_info['category'] = ticket['ticket']['category']
            ticket_info['subcat'] = ticket['ticket']['sub_category']
            ticket_info['itemcat'] = ticket['ticket']['item_category']
            return render_template('outages/spark1.html', ticket=ticket_info)

    else:
        try:
            all_tickets_request = requests.get(f"{FRESH_ENDPOINT}tickets/filter?query=\"tag:spark AND status:2 OR tag:spark AND status:3 or tag:spark AND status:8 OR tag:spark AND status:9 OR tag:spark AND status:10\"", auth=(FRESH_API, 'TICKETS'))
            all_tickets = all_tickets_request.json().get('tickets', [])
            print(all_tickets)
            
            for item in all_tickets:
                ticket = {}
                ticket["ticket_number"] = item['id']
                ticket["title"] = item['subject']
                ticket['description'] = item['description_text']
                date = datetime.datetime.strptime(str(item['created_at']), "%Y-%m-%dT%H:%M:%SZ")
                ticket['created_date'] = date.strftime("%m-%d-%Y")
                ticket["status"] = TICKET_STATUSES[int(item['status'])]
                ticket['source'] = TICKET_SOURCES[int(item['source'])]
                ticket['priority'] = TICKET_PRIORITIES[int(item['priority'])]
                ticket['category'] = item['category']
                ticket['subcat'] = item['sub_category']
                ticket['itemcat'] = item['item_category']
                ticket['status_code'] = int(item['status'])
                filtered_tickets.append(ticket)
            
            # Save to file
            with open('./json/filtered_tickets.json', 'w', encoding='utf-8') as f:
                json.dump(filtered_tickets, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed. {e}")
            logger.error(f"Error fetching tickets: {str(e)}")
    return render_template('outages/spark3.html', tickets=filtered_tickets) 

@bp.route('/saved', methods=['GET'])
@login_required
def saved_outages():
    try:
        with open('./json/filtered_tickets.json', 'r', encoding='utf-8') as f:
            filtered_tickets = json.load(f)
    except Exception as e:
        logger.error(f"Error loading saved tickets: {str(e)}")
        filtered_tickets = []

    return render_template('outages/spark3.html', tickets=filtered_tickets, active_page='saved_outages') 