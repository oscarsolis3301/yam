import pandas as pd
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from fuzzywuzzy import process, fuzz
from . import bp
from app.extensions import Config

# Load and prepare office data
df = pd.read_csv(Config.BASE_DIR / "Offices" / "offices.csv")
df.rename(columns={"#": "Number"}, inplace=True)

df1 = pd.read_csv(Config.BASE_DIR / "Offices" / "offices_info.csv")
df1.rename(columns={"#": "Number"}, inplace=True)

df = df.merge(df1[['Mnemonic', 'IP', 'Number']], on='Number', how='left')

# Check if 'IP' column is merged correctly
    # Debug print removed for cleaner output

# Fix pandas warning by converting numeric columns to string before filling NaN
for col in df.columns:
    if df[col].dtype == 'float64':
        df[col] = df[col].fillna('').astype(str)
    else:
        df[col] = df[col].fillna('')

df['Location'] = df['City'] + ', ' + df['State']
df['search_string'] = (
    df['Internal Name'].astype(str) + ' ' +
    df['Number'].astype(str)
).str.lower()

@bp.route('/')
@login_required
def offices():
    return render_template('offices.html', offices=df.to_dict(orient='records'), active_page='offices')

@bp.route('/search')
@login_required
def search_offices():
    query = request.args.get('q', '')
    # add_recent_search(current_user.id, query, 'Office')
    if not query:
        return jsonify([])

    # Get exact matches first
    exact_matches = df[
        df['search_string'].str.contains(query, case=False, na=False) |
        df['Mnemonic'].str.contains(query, case=False, na=False)
    ]

    # If we have exact matches, return those
    if not exact_matches.empty:
        return jsonify(exact_matches[[
            'Internal Name', 'Location', 'Phone', 'Address', 'Operations Manager', 'Mnemonic', 'IP', 'Number'
        ]].rename(columns={'Operations Manager': 'Manager'}).to_dict(orient='records'))

    # Otherwise, use fuzzy matching with a higher threshold
    partial_results = process.extract(
        query, 
        df['search_string'].tolist(), 
        scorer=fuzz.partial_ratio, 
        limit=10
    )
    
    # Only include results with score > 70
    matched_indices = [i for _, score, i in partial_results if score > 70]
    matches = df.loc[matched_indices]

    return jsonify(matches[[
        'Internal Name', 'Location', 'Phone', 'Address', 'Operations Manager', 'Mnemonic', 'IP', 'Number'
    ]].rename(columns={'Operations Manager': 'Manager'}).to_dict(orient='records'))

@bp.route('/detail')
@login_required
def office_detail():
    """Get detailed information for a specific office by name."""
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Office name is required'}), 400
    
    # Try exact match first
    exact_match = df[df['Internal Name'].str.lower() == name.lower()]
    if not exact_match.empty:
        office = exact_match.iloc[0]
        return jsonify({
            'Internal Name': str(office['Internal Name']),
            'Location': str(office['Location']),
            'Phone': str(office['Phone']),
            'Address': str(office['Address']),
            'Manager': str(office['Operations Manager']),
            'Mnemonic': str(office['Mnemonic']),
            'IP': str(office['IP']),
            'Number': int(office['Number']) if pd.notna(office['Number']) else None
        })
    
    # Try fuzzy matching if no exact match
    try:
        # Get all office names for fuzzy matching
        office_names = df['Internal Name'].dropna().tolist()
        if not office_names:
            return jsonify({'error': 'No offices found'}), 404
        
        # Find best match
        best_match, score = process.extractOne(name, office_names, scorer=fuzz.ratio)
        
        if score >= 80:  # High confidence threshold
            office = df[df['Internal Name'] == best_match].iloc[0]
            return jsonify({
                'Internal Name': str(office['Internal Name']),
                'Location': str(office['Location']),
                'Phone': str(office['Phone']),
                'Address': str(office['Address']),
                'Manager': str(office['Operations Manager']),
                'Mnemonic': str(office['Mnemonic']),
                'IP': str(office['IP']),
                'Number': int(office['Number']) if pd.notna(office['Number']) else None
            })
        else:
            return jsonify({'error': f'No office found matching "{name}"'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Error searching for office: {str(e)}'}), 500 