from loguru import logger

def configure_logger():
    logger.remove()
    logger.add("debug.log", rotation="1 MB", level="DEBUG", backtrace=True, diagnose=True)
