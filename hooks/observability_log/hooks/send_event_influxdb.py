#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
File-based Observability Hook Script
Logs Claude Code hook events to a file in JSON Lines format.
"""

import json
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_log_file_path() -> Path:
    """Get the log file path from environment or use default."""
    log_file = os.getenv('CLAUDE_LOG_FILE', 'claude_events.jsonl')
    
    # If it's not an absolute path, make it relative to current directory
    if not os.path.isabs(log_file):
        log_file = Path.cwd() / log_file
    else:
        log_file = Path(log_file)
    
    # Ensure parent directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    return log_file

class FileEventLogger:
    def __init__(self):
        self.log_file = get_log_file_path()
    
    def log_event(self, event_data: dict) -> bool:
        """Log event data to file in JSON Lines format."""
        try:
            # Add timestamp if not present
            if 'timestamp' not in event_data:
                event_data['timestamp'] = int(datetime.now().timestamp() * 1000)
            
            # Add ISO timestamp for readability
            event_data['timestamp_iso'] = datetime.fromtimestamp(
                event_data['timestamp'] / 1000
            ).isoformat()
            
            # Write to file as JSON line
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
            
            return True
            
        except Exception as e:
            print(f"Failed to log event to file: {e}", file=sys.stderr)
            return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Log Claude Code hook events to file')
    parser.add_argument('--source-app', required=True, help='Source application name')
    parser.add_argument('--event-type', required=True, help='Hook event type (PreToolUse, PostToolUse, etc.)')
    parser.add_argument('--add-chat', action='store_true', help='Include chat transcript if available')
    
    args = parser.parse_args()
    
    logger = FileEventLogger()
    
    try:
        # Read hook data from stdin
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON input: {e}", file=sys.stderr)
        sys.exit(0)  # Exit with 0 to not block Claude Code
    
    # Prepare event data
    event_data = {
        'source_app': args.source_app,
        'session_id': input_data.get('session_id', 'unknown'),
        'hook_event_type': args.event_type,
        'payload': input_data,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    # Handle --add-chat option
    if args.add_chat and 'transcript_path' in input_data:
        transcript_path = input_data['transcript_path']
        if os.path.exists(transcript_path):
            # Read .jsonl file and convert to JSON array
            chat_data = []
            try:
                with open(transcript_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                chat_data.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass  # Skip invalid lines
                
                # Add chat to event data
                event_data['chat'] = chat_data
            except Exception as e:
                print(f"Failed to read transcript: {e}", file=sys.stderr)
    
    # Log to file
    success = logger.log_event(event_data)
    
    if success:
        print(f"Event {args.event_type} logged to {logger.log_file}", file=sys.stderr)
    else:
        print(f"Failed to log event {args.event_type}", file=sys.stderr)
    
    # Always exit with 0 to not block Claude Code operations
    sys.exit(0)

if __name__ == '__main__':
    main()