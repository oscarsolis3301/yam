import logging
import sys
from logging.handlers import RotatingFileHandler
import os

class ColoredFormatter(logging.Formatter):
    """Custom formatter with bright/bold colors for all log levels and specific tags."""
    # Bright/bold ANSI color codes
    grey = "\x1b[38;5;250m"
    blue = "\x1b[1;34m"         # Bold Blue
    cyan = "\x1b[1;36m"         # Bright Cyan
    yellow = "\x1b[1;33m"       # Bright Yellow
    red = "\x1b[1;31m"          # Bright Red
    magenta = "\x1b[1;35m"      # Bright Magenta
    green = "\x1b[1;32m"        # Bright Green
    white = "\x1b[1;37m"        # Bright White
    orange = "\x1b[1;38;5;208m" # Bright Orange
    pink = "\x1b[1;38;5;213m"   # Bright Pink
    reset = "\x1b[0m"

    # Map log levels to colors
    LEVEL_COLORS = {
        logging.DEBUG: grey,
        logging.INFO: cyan,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: magenta,
    }

    # Map tags to colors (for additional highlighting)
    TAG_COLORS = {
        '[INFO]': cyan,
        '[OK]': green,
        '[WARN]': yellow,
        '[ERROR]': red,
        '[FATAL]': magenta,
        '[STEP]': magenta,
        '[TIME]': white,
        '[DEBUG]': grey,
        '[SUCCESS]': green,
        '[LAUNCH]': orange,
        '[ELECTRON]': pink,
        '[FLASK]': blue,
        '[NODE]': green,
        '[NPM]': yellow,
        '[DEPS]': cyan,
        '[PROCESS]': magenta,
        '[WEB]': blue,
        '[DESKTOP]': orange,
        '[CHECK]': cyan,
        '[CLEANUP]': yellow,
        '[SHUTDOWN]': red,
        '[STARTUP]': green,
        '[PERF]': magenta,
        '[MEMORY]': cyan,
        '[CACHE]': green,
        '[SOCKET]': pink,
        '[READY]': green,
        '[LOGIN]': blue,
    }

    # Default format
    PLAIN_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def format(self, record):
        msg = record.getMessage()
        
        # Replace Unicode symbols with ASCII equivalents on Windows if needed
        if os.name == 'nt' and (getattr(sys.stdout, 'encoding', None) or '').lower() != 'utf-8':
            # Replace checkmark and other common symbols
            msg = msg.replace('✔︎', '[OK]').replace('✗', '[X]').replace('⚠️', '[WARN]').replace('🛑', '[STOP]').replace('🚀', '[START]').replace('✅', '[OK]').replace('❌', '[ERR]').replace('🖥️', '[DESKTOP]').replace('📡', '[NET]').replace('🔧', '[CFG]').replace('📝', '[NOTE]').replace('🎯', '[GO]').replace('🔄', '[RETRY]').replace('🔐', '[AUTH]').replace('📋', '[CLIP]').replace('🧵', '[THREAD]').replace('🗂️', '[FILES]').replace('🗑️', '[DEL]').replace('🕒', '[TIME]').replace('🗃️', '[DB]').replace('🗨️', '[MSG]').replace('🗳️', '[VOTE]').replace('🗝️', '[KEY]').replace('🗺️', '[MAP]').replace('🗞️', '[NEWS]').replace('🗻', '[MNT]').replace('🗼', '[TWR]').replace('🗽', '[STATUE]').replace('🗿', '[MOAI]').replace('🛠️', '[TOOLS]').replace('🛡️', '[SHLD]').replace('🧩', '[PIECE]').replace('🧪', '[LAB]').replace('🧬', '[DNA]').replace('🧭', '[COMPASS]').replace('🧱', '[BRICK]').replace('🧲', '[MAGNET]').replace('🧰', '[TOOLBOX]').replace('🧳', '[BAG]').replace('🧴', '[LOTION]').replace('🧵', '[THREAD]').replace('🧶', '[YARN]').replace('🧿', '[NAZAR]').replace('🩰', '[BALLET]').replace('🩸', '[BLOOD]').replace('🩹', '[BANDAGE]').replace('🩺', '[STETHO]').replace('🪀', '[YOYO]').replace('🪁', '[KITE]').replace('🪂', '[PARACHUTE]').replace('🪃', '[BOOMERANG]').replace('🪄', '[WAND]').replace('🪅', '[PINATA]').replace('🪆', '[NESTDOLL]').replace('🪐', '[PLANET]').replace('🪑', '[CHAIR]').replace('🪒', '[RAZOR]').replace('🪓', '[AXE]').replace('🪔', '[LAMP]').replace('🪕', '[BANJO]').replace('🪙', '[COIN]').replace('🪚', '[SAW]').replace('🪛', '[SCREWDRIVER]').replace('🪜', '[LADDER]').replace('🪝', '[HOOK]').replace('🪞', '[MIRROR]').replace('🪟', '[WINDOW]').replace('🪠', '[PLUNGER]').replace('🪡', '[NEEDLE]').replace('🪢', '[KNOT]').replace('🪣', '[BUCKET]').replace('🪤', '[TRAP]').replace('🪥', '[TOOTHBRUSH]').replace('🪦', '[HEADSTONE]').replace('🪧', '[PLACARD]').replace('🪨', '[ROCK]').replace('🪰', '[FLY]').replace('🪱', '[WORM]').replace('🪲', '[BEETLE]').replace('🪳', '[COCKROACH]').replace('🪴', '[PLANT]').replace('🪵', '[LOG]').replace('🪶', '[FEATHER]').replace('🪷', '[LOTUS]').replace('🪸', '[CORAL]').replace('🪹', '[EMPTY NEST]').replace('🪺', '[NEST]').replace('🪻', '[HYACINTH]').replace('🪼', '[JELLY]').replace('🪽', '[WING]').replace('🪿', '[GOOSE]').replace('🫀', '[HEART]').replace('🫁', '[LUNG]').replace('🫂', '[HUG]').replace('🫃', '[PREGNANT]').replace('🫄', '[PREGNANT]').replace('🫅', '[ROYAL]').replace('🫎', '[MOOSE]').replace('🫏', '[DONKEY]').replace('🫐', '[BERRY]').replace('🫑', '[PEPPER]').replace('🫒', '[OLIVE]').replace('🫓', '[FLATBREAD]').replace('🫔', '[TAMALE]').replace('🫕', '[FONDUE]').replace('🫖', '[TEAPOT]')
        
        # Check if terminal supports colors
        supports_color = (
            sys.stdout.isatty() and (
                os.name != 'nt' or  # Not Windows
                'ANSICON' in os.environ or  # ANSICON
                'WT_SESSION' in os.environ or  # Windows Terminal
                'TERM' in os.environ or  # Unix-like terminal
                hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()  # Fallback
            )
        )
        
        if supports_color:
            # Get base color for log level
            level_color = self.LEVEL_COLORS.get(record.levelno, self.white)
            
            # Check for specific tags and use their color if present
            tag_color = None
            for tag, color in self.TAG_COLORS.items():
                if tag in msg:
                    tag_color = color
                    break
            
            # Use tag color if present, otherwise use level color
            color = tag_color if tag_color else level_color
            
            # Apply color to the message
            colored_msg = f"{color}{msg}{self.reset}"
            
            # Format the complete log line
            log_fmt = f"%(asctime)s - %(name)s - %(levelname)s - {colored_msg}"
            formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
            return formatter.format(record)
        else:
            # Fallback to plain formatting
            formatter = logging.Formatter(self.PLAIN_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
            return formatter.format(record)

def setup_logging():
    """Configure logging for the application"""
    logger = logging.getLogger('spark')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger
    
    # Create console handler with proper encoding for Windows
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Fix Unicode encoding issues on Windows
    if os.name == 'nt':
        # Force UTF-8 encoding for stdout on Windows
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception:
                pass
        # Use a safer formatter that handles Unicode
        console_handler.setFormatter(ColoredFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())
    
    # Create file handler with UTF-8 encoding
    file_handler = RotatingFileHandler(
        'spark.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger 