#!!/usr/bin/env python3

import asyncio
import logging
from pathlib import Path

from argparse import ArgumentParser

from log2mqtt.controller import Controller

logger = None

async def main():
    global loggger

    parser = ArgumentParser(
        description="A tool to extract known activity types from proxy log data."
    )
    parser.add_argument(
        "-f", "--config-path", 
        type=Path, 
        help="The path to the config file."
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable detailed logging output."
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    controller = Controller()

    controller.load_config(args.config_path)

    logger.debug("Starting LogProcessor")
    try:
        await controller.start()
    except KeyboardInterrupt as kie:
        logger.debug("Exiting!")
    except asyncio.exceptions.CancelledError as e:
        logger.debug("Exiting!")

if __name__ == "__main__":    
    asyncio.run(main())