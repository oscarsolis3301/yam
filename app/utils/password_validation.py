import re
import string
from typing import Tuple, List

def validate_password(password: str, username: str = None, first_name: str = None, last_name: str = None) -> Tuple[bool, List[str]]:
    """
    Validate password strength and check against user information.
    
    Args:
        password: The password to validate
        username: User's username
        first_name: User's first name
        last_name: User's last name
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for uppercase letters
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letters
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for numbers
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    # Check for symbols
    symbols = string.punctuation
    if not any(char in symbols for char in password):
        errors.append("Password must contain at least one symbol")
    
    # Check against user information
    user_info = []
    if username:
        user_info.append(username.lower())
    if first_name:
        user_info.append(first_name.lower())
    if last_name:
        user_info.append(last_name.lower())
    
    password_lower = password.lower()
    
    for info in user_info:
        if info and len(info) >= 3:  # Only check if info is meaningful
            # Check if any part of the user info is in the password
            if info in password_lower:
                errors.append(f"Password cannot contain your {info} name")
            # Check for reversed user info
            if info[::-1] in password_lower:
                errors.append(f"Password cannot contain your {info} name reversed")
            # Check for common variations
            variations = [
                info.replace(' ', ''),
                info.replace(' ', '_'),
                info.replace(' ', '-'),
                info.capitalize(),
                info.title()
            ]
            for variation in variations:
                if variation.lower() in password_lower:
                    errors.append(f"Password cannot contain variations of your {info} name")
    
    # Check for common weak patterns
    weak_patterns = [
        'password', '123456', 'qwerty', 'admin', 'user', 'login',
        'welcome', 'letmein', 'monkey', 'dragon', 'master', 'hello'
    ]
    
    for pattern in weak_patterns:
        if pattern in password_lower:
            errors.append("Password contains common weak patterns")
            break
    
    # Check for sequential characters
    if re.search(r'(.)\1{2,}', password):
        errors.append("Password cannot contain 3 or more repeated characters")
    
    # Check for sequential numbers or letters
    if re.search(r'(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password_lower):
        errors.append("Password cannot contain sequential letters")
    
    if re.search(r'(?:012|123|234|345|456|567|678|789|890)', password):
        errors.append("Password cannot contain sequential numbers")
    
    return len(errors) == 0, errors

def get_password_strength(password: str) -> str:
    """
    Get a human-readable password strength indicator.
    
    Args:
        password: The password to evaluate
    
    Returns:
        String indicating strength: 'weak', 'medium', 'strong', 'very_strong'
    """
    score = 0
    
    # Length bonus
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    
    # Character variety bonus
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        score += 1
    
    # Complexity bonus
    if len(set(password)) >= len(password) * 0.8:  # High character variety
        score += 1
    
    # Determine strength
    if score <= 3:
        return 'weak'
    elif score <= 5:
        return 'medium'
    elif score <= 7:
        return 'strong'
    else:
        return 'very_strong'

def generate_password_suggestions(username: str = None, first_name: str = None, last_name: str = None) -> List[str]:
    """
    Generate password suggestions that meet the requirements.
    
    Args:
        username: User's username
        first_name: User's first name
        last_name: User's last name
    
    Returns:
        List of password suggestions
    """
    suggestions = [
        "SecurePass123!",
        "MySecure2024#",
        "StrongP@ssw0rd",
        "SafeLogin2024$",
        "ProtectMe2024!",
        "SecureAccess#1",
        "MyAccount2024@",
        "SafeLogin2024%",
        "ProtectData2024!",
        "SecureUser2024#"
    ]
    
    # Filter out suggestions that contain user information
    filtered_suggestions = []
    user_info = []
    if username:
        user_info.append(username.lower())
    if first_name:
        user_info.append(first_name.lower())
    if last_name:
        user_info.append(last_name.lower())
    
    for suggestion in suggestions:
        suggestion_lower = suggestion.lower()
        should_include = True
        
        for info in user_info:
            if info and len(info) >= 3 and info in suggestion_lower:
                should_include = False
                break
        
        if should_include:
            filtered_suggestions.append(suggestion)
    
    return filtered_suggestions[:5]  # Return top 5 suggestions 