#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "influxdb-client>=1.38.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
InfluxDB Observability Hook Script
Sends Claude Code hook events directly to InfluxDB for observability.
"""

import json
import sys
import os
import argparse
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug logging function
def debug_log(message, data=None):
    """Write debug information to a log file"""
    try:
        log_path = os.path.join(os.path.dirname(__file__), '..', 'hook_debug.log')
        with open(log_path, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] {message}\n")
            if data:
                f.write(f"  Data: {json.dumps(data, indent=2)}\n")
            f.write("\n")
    except Exception as e:
        print(f"Debug logging failed: {e}", file=sys.stderr)

class InfluxDBEventSender:
    def __init__(self):
        self.url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.token = os.getenv('INFLUXDB_TOKEN')
        self.org = os.getenv('INFLUXDB_ORG', 'events-org')
        self.bucket = os.getenv('INFLUXDB_BUCKET', 'application-events')
        
        if not self.token:
            print("Warning: INFLUXDB_TOKEN not found, hook will fail silently", file=sys.stderr)
            self.client = None
            return
        
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        except Exception as e:
            print(f"Failed to initialize InfluxDB client: {e}", file=sys.stderr)
            self.client = None
    
    def send_event(self, event_data: dict) -> bool:
        if not self.client:
            return False
            
        try:
            # Extract chat data if available
            chat_data = event_data.get('chat', {})
            if isinstance(chat_data, list) and chat_data:
                # If chat is a list, take the last message or summarize
                chat_summary = {
                    'message_count': len(chat_data),
                    'last_message_type': chat_data[-1].get('type', 'unknown') if chat_data else 'none'
                }
            else:
                chat_summary = chat_data if isinstance(chat_data, dict) else {}
            
            # Create InfluxDB point
            point = Point("claude_code_events") \
                .tag("source_app", event_data.get('source_app', 'unknown')) \
                .tag("session_id", event_data.get('session_id', 'unknown')) \
                .tag("hook_event_type", event_data.get('hook_event_type', 'unknown')) \
                .field("payload", json.dumps(event_data.get('payload', {}))) \
                .field("chat_data", json.dumps(chat_summary)) \
                .field("summary", event_data.get('summary', '')) \
                .time(event_data.get('timestamp', int(datetime.now().timestamp() * 1000)), WritePrecision.MS)
            
            # Add additional fields from payload for easier querying
            payload = event_data.get('payload', {})
            if isinstance(payload, dict):
                # Add tool information if available
                tool_data = payload.get('tool', {})
                if tool_data:
                    point = point.tag("tool_name", tool_data.get('name', 'unknown'))
                
                # Add message type if available
                if 'type' in payload:
                    point = point.tag("message_type", payload['type'])
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
            
        except Exception as e:
            print(f"Failed to send event to InfluxDB: {e}", file=sys.stderr)
            return False
    
    def close(self):
        if self.client:
            self.client.close()

def main():
    debug_log("Hook script started")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send Claude Code hook events to InfluxDB')
    parser.add_argument('--source-app', required=True, help='Source application name')
    parser.add_argument('--event-type', required=True, help='Hook event type (PreToolUse, PostToolUse, etc.)')
    parser.add_argument('--add-chat', action='store_true', help='Include chat transcript if available')
    
    args = parser.parse_args()
    debug_log(f"Parsed args", {
        'source_app': args.source_app,
        'event_type': args.event_type,
        'add_chat': args.add_chat
    })
    
    sender = InfluxDBEventSender()
    debug_log(f"InfluxDB sender initialized, client exists: {sender.client is not None}")
    
    try:
        # Read hook data from stdin
        input_data = json.load(sys.stdin)
        debug_log("Received input data", input_data)
    except json.JSONDecodeError as e:
        debug_log(f"Failed to parse JSON input: {e}")
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
    
    # Send to InfluxDB
    debug_log("Attempting to send event to InfluxDB", event_data)
    success = sender.send_event(event_data)
    debug_log(f"Event send result: {success}")
    
    if success:
        debug_log(f"Event {args.event_type} sent to InfluxDB successfully")
        print(f"Event {args.event_type} sent to InfluxDB successfully", file=sys.stderr)
    else:
        debug_log(f"Failed to send event {args.event_type} to InfluxDB")
    
    sender.close()
    debug_log("Hook script completed")
    
    # Always exit with 0 to not block Claude Code operations
    sys.exit(0)

if __name__ == '__main__':
    main()