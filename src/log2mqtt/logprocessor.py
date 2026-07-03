
import asyncio
import os
import re
from typing import Callable, Dict, Any, List


class LogProcessor:
    """
    Reponsible for opening and processing new lines in the log file specified in the config. Ignores
    any existing content at the time the log is opened and only processes new lines. Works asynchronously,
    idenfitying whether new lines match defined patterns.
    """
    ...

    def __init__(self, config: Dict[str, Any], callback: Callable[[str, str, str, str, str], None]):
        """
        Initializes the LogProcessor.

        config: Configuration dictionary containing 'source' details.
                Example:
                {
                    'path': '/var/log/e2guardian/access.log',
                    'delimiter': '\t',
                    'emptyValue': '-'
                    'url': [{'index': 5}],
                    'method': [{'index': 6}],
                    'user': [{'index': 2}],
                    'client': [{'index': 4}, {'index': 3}],
                    'userAgent': [{'index': 10}]
                }
        callback: A function to call when a log line is successfully parsed.
                  Signature: callback(url, method, useragent)
        """
        self.log_path = config.get('path')
        self.delimiter = config.get('delimiter', '\t')
        self.empty_value = config.get('emptyValue', '') 

        # Pre-calculate indices for parsing
        self.url_indices = [item['index'] for item in config.get('url', [])]
        self.method_indices = [item['index'] for item in config.get('method', [])]
        self.user_indices = [item['index'] for item in config.get('user', [])]
        self.client_indices = [item['index'] for item in config.get('client', [])]
        self.useragent_indices = [item['index'] for item in config.get('userAgent', [])]

        self.callback = callback
        
        self._file = None
        self._running = False
        self._last_position = 0

    def read_line_blocking(self):
        """Standard blocking I/O."""
        # print("Calling readline....")
        return self._file.readline()

    async def start(self):
        loop = asyncio.get_running_loop()
        
        # Open the file normally (blocking)
        with open(self.log_path, 'r') as f:
            self._file = f
            # Seek to end
            self._file.seek(0, 2)
            
            while True:
                # Offload the blocking read to a thread executor
                line = await loop.run_in_executor(None, self.read_line_blocking)
                
                if not line:
                    await asyncio.sleep(0.1)
                    continue
                
                # print(f"Processing: {line.strip()}")
                self._process_line(line)
    
    def _process_line(self, line: str):
        if not line:
            return
            
        parts = line.split(self.delimiter)
        
        url = None
        method = None
        client = None
        user = None
        userAgent = None

        # Extract URL
        for idx in self.url_indices:
            if idx < len(parts) and parts[idx] != self.empty_value:
                url = parts[idx]
                break

        # Extract Method
        for idx in self.method_indices:
            if idx < len(parts) and parts[idx] != self.empty_value:
                method = parts[idx]
                break

        # Extract User
        for idx in self.user_indices:
            if idx < len(parts) and parts[idx] != self.empty_value:
                user = parts[idx]
                break

        # Extract Client
        for idx in self.client_indices:
            if idx < len(parts) and parts[idx] != self.empty_value:
                client = parts[idx]
                break

        # Extract UserAgent
        for idx in self.useragent_indices:
            if idx < len(parts) and parts[idx] != self.empty_value:
                userAgent = parts[idx]
                break

        if (client or user) and (url or userAgent):
            self.callback(user, client, url, method, userAgent)
        
        