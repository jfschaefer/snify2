import configparser
import functools
from pathlib import Path

from ffutil.__main__ import logger


CACHE_DIR = Path('~/.cache/stextools').expanduser()


@functools.cache
def get_config() -> configparser.ConfigParser:
    config_path = Path('~/.config/stextools/config.ini').expanduser()
    config = configparser.ConfigParser()
    if config_path.exists():
        logger.info(f'Loading config from {config_path}')
        config.read(config_path)
    else:
        logger.info(f'No config file found at {config_path}. Using defaults.')
    return config
