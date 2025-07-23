import os
import re

# 1. File patterns to update
TARGET_DIRS = [
    "app/blueprints",
    "app"
]
TARGET_FILES = [
    "app/YAM_refactored.py"
]

# 2. Patterns to search and replace
REPLACEMENTS = [
    # Replace full import with db
    (re.compile(r"from app import db, memory_manager, _initialization_state, _app_initialized, _blueprints_registered"),
     "from extensions import db\nfrom app.shared_state import memory_manager, _initialization_state, _app_initialized, _blueprints_registered"),
    # Replace full import without db
    (re.compile(r"from app import memory_manager, _initialization_state, _app_initialized, _blueprints_registered"),
     "from app.shared_state import memory_manager, _initialization_state, _app_initialized, _blueprints_registered"),
    # Replace shared_state import with db
    (re.compile(r"from app.shared_state import db, memory_manager, _initialization_state, _app_initialized, _blueprints_registered"),
     "from extensions import db\nfrom app.shared_state import memory_manager, _initialization_state, _app_initialized, _blueprints_registered"),
    # Replace db from app
    (re.compile(r"from app import db"), "from extensions import db"),
    # Replace db from shared_state
    (re.compile(r"from app.shared_state import db"), "from extensions import db"),
]

# 3. Remove global variable definitions in YAM_refactored.py
YAM_GLOBALS_PATTERN = re.compile(
    r"# Flag to track if blueprints have been registered to prevent duplicates\n"
    r"_blueprints_registered = False\n\n"
    r"# Enhanced global initialization tracking with performance monitoring\n"
    r"_app_initialized = False\n"
    r"_background_init_started = False\n"
    r"_initialization_state = \{[^}]+\}\n", re.DOTALL
)
YAM_IMPORT_SHARED_STATE = (
    "# Import shared state variables (defined in app.shared_state)\n"
    "from app.shared_state import (\n"
    "    memory_manager, \n"
    "    _initialization_state, \n"
    "    _app_initialized, \n"
    "    _blueprints_registered, \n"
    "    _background_init_started,\n"
    "    update_initialization_status,\n"
    "    get_initialization_status,\n"
    "    set_app_initialized,\n"
    "    set_blueprints_registered,\n"
    "    set_background_init_started\n"
    ")\n"
)

def update_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Apply all replacements
    for pattern, replacement in REPLACEMENTS:
        content = pattern.sub(replacement, content)

    # Special handling for YAM_refactored.py
    if filepath.endswith("YAM_refactored.py"):
        content = YAM_GLOBALS_PATTERN.sub(YAM_IMPORT_SHARED_STATE, content)

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated: {filepath}")

def walk_and_update():
    for target_dir in TARGET_DIRS:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".py"):
                    update_file(os.path.join(root, file))
    for file in TARGET_FILES:
        if os.path.exists(file):
            update_file(file)

if __name__ == "__main__":
    walk_and_update()
    print("Refactor complete! Please review your changes and test your app.")