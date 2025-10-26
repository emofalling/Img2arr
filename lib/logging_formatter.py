import logging

ANSI_RESET_ALL  = "\x1b[0m"
ANSI_BOLD       = "\x1b[1m"
ANSI_WEAK       = "\x1b[2m"
ANSI_ITALIC     = "\x1b[3m"
ANSI_UNDERLINE  = "\x1b[4m"
ANSI_BLINK      = "\x1b[5m"
ANSI_BLINK_FAST = "\x1b[6m"
ANSI_REVERSE    = "\x1b[7m"
ANSI_HIDE       = "\x1b[8m"

ANSI_FCOLOR_DEFAULT      = "\x1b[39m"
ANSI_FCOLOR_BLACK        = "\x1b[30m"
ANSI_FCOLOR_RED          = "\x1b[31m"
ANSI_FCOLOR_GREEN        = "\x1b[32m"
ANSI_FCOLOR_YELLOW       = "\x1b[33m"
ANSI_FCOLOR_BLUE         = "\x1b[34m"
ANSI_FCOLOR_PURPLE       = "\x1b[35m"
ANSI_FCOLOR_CYAN         = "\x1b[36m"
ANSI_FCOLOR_WHITE        = "\x1b[37m"
ANSI_FCOLOR_LIGHT_BLACK  = "\x1b[90m"
ANSI_FCOLOR_LIGHT_RED    = "\x1b[91m"
ANSI_FCOLOR_LIGHT_GREEN  = "\x1b[92m"
ANSI_FCOLOR_LIGHT_YELLOW = "\x1b[93m"
ANSI_FCOLOR_LIGHT_BLUE   = "\x1b[94m"
ANSI_FCOLOR_LIGHT_PURPLE = "\x1b[95m"
ANSI_FCOLOR_LIGHT_CYAN   = "\x1b[96m"
ANSI_FCOLOR_LIGHT_WHITE  = "\x1b[97m"

ANSI_COLOR_DICT = {
    logging.DEBUG: ANSI_FCOLOR_BLUE,
    logging.INFO: ANSI_FCOLOR_GREEN,
    logging.WARNING: ANSI_FCOLOR_YELLOW,
    logging.ERROR: ANSI_FCOLOR_RED,
    logging.CRITICAL: ANSI_FCOLOR_LIGHT_RED+ANSI_BOLD,
} 


class ColoredFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record):
        log = super().format(record)
        return f"{ANSI_COLOR_DICT.get(record.levelno, ANSI_FCOLOR_DEFAULT)}{log}{ANSI_RESET_ALL}"