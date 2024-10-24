from loguru import logger
import sys


def configure_logger():
    logger.remove()
    logger.add(sys.stdout, level="DEBUG", backtrace=True, diagnose=True)
    logger.add(
        "debug.log", level="DEBUG", backtrace=True, diagnose=True
    )
