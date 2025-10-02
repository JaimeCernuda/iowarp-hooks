#!/usr/bin/env -S uv run --python 3.11 --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
ChronoLog Unified Observability Hook Script
Sends all Claude Code hook events to a single chronicle and story for unified logging.
All events go to chronicle 'claude_code_event' and story 'logs' with session_id embedded in data.
"""

import json
import sys
import os
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug logging function
def debug_log(message, data=None):
    """Write debug information to a log file"""
    try:
        # Create logs directory inside .claude folder
        claude_dir = os.path.join(os.path.dirname(__file__), '..', '.claude')
        logs_dir = os.path.join(claude_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Set log file path inside the logs directory
        log_path = os.path.join(logs_dir, 'chronolog_hook_debug.log')
        
        with open(log_path, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [UNIFIED] {message}\n")
            if data:
                f.write(f"  Data: {json.dumps(data, indent=2)}\n")
            f.write("\n")
    except Exception as e:
        pass  # Fail silently to not block Claude

# Get ChronoLog library path from environment
def get_chronolog_lib_path():
    """Get ChronoLog library path from environment variables"""
    # Try environment variable first
    env_path = os.getenv('CHRONOLOG_LIB_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    
    # Fallback search paths from environment
    search_paths_env = os.getenv('CHRONOLOG_SEARCH_PATHS', '')
    if search_paths_env:
        search_paths = search_paths_env.split(':')
    else:
        # No default paths - require environment configuration
        debug_log("No CHRONOLOG_SEARCH_PATHS configured - please set environment variables")
        return None
    
    for path in search_paths:
        if path and os.path.exists(path):
            # Check if py_chronolog_client library exists
            lib_files = [f for f in os.listdir(path) if f.startswith('py_chronolog_client')]
            if lib_files:
                return path
    
    return None

# Get Spack library paths from environment
def get_spack_lib_paths():
    """Get Spack library paths from environment variables"""
    spack_paths_env = os.getenv('SPACK_LIB_PATHS', '')
    if spack_paths_env:
        return spack_paths_env.split(':')
    else:
        # No default paths - require environment configuration
        debug_log("No SPACK_LIB_PATHS configured - please set environment variables")
        return []

class ChronoLogUnifiedEventSender:
    def __init__(self):
        # Load configuration from environment variables
        self.lib_path = get_chronolog_lib_path() or os.getenv('CHRONOLOG_DEFAULT_LIB_PATH', "/path/to/chronolog-install/Debug/lib")
        self.host = os.getenv('CHRONOLOG_HOST', "172.25.101.25")  # ChronoVisor host
        self.port = int(os.getenv('CHRONOLOG_PORT', '5555'))
        
        # Unified chronicle and story names
        self.chronicle_name = "claude_code_event"  # Single chronicle for all events
        self.story_name = "logs"  # Single story for all events
        
        # Global connection state
        self.client = None
        self.story_handle = None
        self.connected = False
        
        debug_log("ChronoLog unified client initialized", {
            'lib_path': self.lib_path,
            'host': self.host,
            'port': self.port,
            'chronicle': self.chronicle_name,
            'story': self.story_name
        })
        
        if not self.lib_path:
            debug_log("ChronoLog library not found - check CHRONOLOG_LIB_PATH or CHRONOLOG_SEARCH_PATHS")
            self.available = False
        else:
            self.available = True
    
    def _setup_environment(self):
        """Set up environment for ChronoLog Python API"""
        if not self.lib_path:
            return False
            
        # Get Spack library paths from environment
        spack_lib_paths = get_spack_lib_paths()
        
        # Build LD_LIBRARY_PATH
        all_lib_paths = [self.lib_path] + spack_lib_paths + [os.environ.get('LD_LIBRARY_PATH', '')]
        lib_path_str = ':'.join(filter(None, all_lib_paths))
        
        os.environ["LD_LIBRARY_PATH"] = lib_path_str
        os.environ["PYTHONPATH"] = f"{self.lib_path}:{os.environ.get('PYTHONPATH', '')}"
        
        sys.path.insert(0, self.lib_path)
        return True
    
    def _connect_to_chronolog(self, py_chronolog_client):
        """Establish connection to ChronoLog and acquire story handle"""
        if self.connected and self.client and self.story_handle:
            return True
        
        try:
            # Create new client connection
            portal_conf = py_chronolog_client.ClientPortalServiceConf("ofi+sockets", self.host, self.port, 55)
            self.client = py_chronolog_client.Client(portal_conf)
            
            # Connect to ChronoLog
            connect_result = self.client.Connect()
            if connect_result != 0:
                debug_log(f"ChronoLog connection failed: {connect_result}")
                return False
            
            # Create chronicle (will succeed if already exists)
            attrs = {}
            create_result = self.client.CreateChronicle(self.chronicle_name, attrs, 1)
            debug_log(f"Chronicle create result: {create_result}")
            
            # Acquire story handle
            acquire_result = self.client.AcquireStory(self.chronicle_name, self.story_name, attrs, 1)
            debug_log(f"AcquireStory result: {acquire_result}")
            
            if isinstance(acquire_result, tuple):
                acquire_status = acquire_result[0]
                self.story_handle = acquire_result[1] if len(acquire_result) > 1 else None
            else:
                acquire_status = acquire_result
                self.story_handle = None
                
            if acquire_status != 0:
                debug_log(f"Failed to acquire story: status={acquire_status}")
                return False
            
            if not self.story_handle:
                debug_log(f"No story handle returned")
                return False
            
            self.connected = True
            debug_log("Successfully connected to ChronoLog and acquired story handle")
            return True
            
        except Exception as e:
            debug_log(f"Exception during ChronoLog connection: {e}")
            return False
    
    def send_event(self, event_data: dict) -> bool:
        """Send event to unified ChronoLog chronicle and story"""
        if not self.available:
            debug_log("ChronoLog not available")
            return False
        
        try:
            # Set up environment
            if not self._setup_environment():
                debug_log("Failed to set up ChronoLog environment")
                return False
            
            # Import ChronoLog library
            import py_chronolog_client
            debug_log("ChronoLog library imported successfully")
            
            # Connect to ChronoLog (reuse connection if available)
            if not self._connect_to_chronolog(py_chronolog_client):
                debug_log("Failed to connect to ChronoLog")
                return False
            
            # Prepare unified event data with session_id embedded
            session_id = event_data.get('session_id', 'unknown')
            event_type = event_data.get('hook_event_type', 'unknown')
            
            # Create comprehensive event payload with session_id included
            event_payload = {
                'timestamp': event_data.get('timestamp', int(time.time() * 1000)),
                'source_app': event_data.get('source_app', 'claude_code'),
                'session_id': session_id,  # Always include session_id in the event data
                'hook_event_type': event_type,
                'processed_at': datetime.now().isoformat(),
                'payload': event_data.get('payload', {}),
                'chat_data': event_data.get('chat', {}),
                'summary': event_data.get('summary', ''),
                'chronicle': self.chronicle_name,
                'story': self.story_name
            }
            
            # Add tool information and response data if available
            payload = event_data.get('payload', {})
            if isinstance(payload, dict):
                # Tool information
                tool_data = payload.get('tool', {})
                if tool_data:
                    event_payload['tool_name'] = tool_data.get('name', 'unknown')
                    event_payload['tool_input'] = tool_data.get('input', {})
                
                # Message type
                if 'type' in payload:
                    event_payload['message_type'] = payload['type']
                
                # Extract agent response data
                if 'content' in payload:
                    event_payload['agent_content'] = payload['content']
                
                # For PostToolUse events, capture tool results/responses
                if event_type == 'PostToolUse':
                    if 'result' in payload:
                        event_payload['tool_result'] = payload['result']
                    if 'output' in payload:
                        event_payload['tool_output'] = payload['output']
                    if 'error' in payload:
                        event_payload['tool_error'] = payload['error']
                    
                    # Always capture recent chat for PostToolUse to get agent responses
                    if 'transcript_path' in payload:
                        transcript_path = payload['transcript_path']
                        if os.path.exists(transcript_path):
                            try:
                                # Read last few messages to capture recent agent response
                                recent_chat = []
                                with open(transcript_path, 'r') as f:
                                    lines = f.readlines()
                                    # Get last 5 messages
                                    for line in lines[-5:]:
                                        line = line.strip()
                                        if line:
                                            try:
                                                msg = json.loads(line)
                                                recent_chat.append(msg)
                                            except json.JSONDecodeError:
                                                pass
                                event_payload['recent_chat'] = recent_chat
                                
                                # Extract the latest agent response
                                for msg in reversed(recent_chat):
                                    if msg.get('role') == 'assistant':
                                        event_payload['latest_agent_response'] = msg.get('content', [])
                                        break
                                        
                            except Exception as e:
                                debug_log(f"Failed to read recent chat: {e}")
                
                # For UserPromptSubmit, capture user input
                if event_type == 'UserPromptSubmit':
                    if 'text' in payload:
                        event_payload['user_prompt'] = payload['text']
                    if 'messages' in payload:
                        event_payload['conversation_messages'] = payload['messages']
                
                # Extract any response or assistant content
                for key in ['response', 'assistant_response', 'text', 'message']:
                    if key in payload:
                        event_payload[f'extracted_{key}'] = payload[key]
            
            # Record event using the unified story handle
            event_json = json.dumps(event_payload)
            
            try:
                self.story_handle.log_event(event_json)
                debug_log(f"Event logged successfully to unified story")
            except Exception as e:
                debug_log(f"Failed to log event with story handle: {e}")
                # Reset connection on error
                self.connected = False
                self.client = None
                self.story_handle = None
                return False
            
            debug_log({
                "chronicle": self.chronicle_name,
                "story": self.story_name,
                "event_type": event_type,
                "session_id": session_id,
                "logged_via": "unified_story_handle"
            }, "ChronoLog unified operation successful")
            
            return True
            
        except ImportError as e:
            debug_log(f"ChronoLog library import error: {e}")
            return False
        except Exception as e:
            debug_log(f"ChronoLog API error: {e}")
            return False
    
    def close(self):
        """Clean up connection"""
        if self.connected and self.client and self.story_handle:
            try:
                self.client.ReleaseStory(self.chronicle_name, self.story_name)
                debug_log("Released unified story handle")
            except Exception as e:
                debug_log(f"Error releasing story: {e}")
            
            try:
                self.client.Disconnect()
                debug_log("Disconnected ChronoLog client")
            except Exception as e:
                debug_log(f"Error disconnecting client: {e}")
            
            self.connected = False
            self.client = None
            self.story_handle = None

def main():
    debug_log("Unified ChronoLog hook started")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send Claude Code hook events to unified ChronoLog chronicle')
    parser.add_argument('--source-app', required=True, help='Source application name')
    parser.add_argument('--event-type', required=True, help='Hook event type (PreToolUse, PostToolUse, etc.)')
    parser.add_argument('--add-chat', action='store_true', help='Include chat transcript if available')
    
    args = parser.parse_args()
    debug_log(f"Parsed args", {
        'source_app': args.source_app,
        'event_type': args.event_type,
        'add_chat': args.add_chat
    })
    
    sender = ChronoLogUnifiedEventSender()
    debug_log(f"ChronoLog unified sender initialized, available: {sender.available}")
    
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
                event_data['summary'] = f"Chat session with {len(chat_data)} messages"
            except Exception as e:
                debug_log(f"Failed to read transcript: {e}")
    
    # Send to ChronoLog unified chronicle
    debug_log("Attempting to send event to ChronoLog unified chronicle", event_data)
    success = sender.send_event(event_data)
    debug_log(f"Event send result: {success}")
    
    if success:
        debug_log(f"Event {args.event_type} sent to ChronoLog unified chronicle successfully")
        print(f"Event {args.event_type} sent to ChronoLog unified chronicle successfully", file=sys.stderr)
    else:
        debug_log(f"Failed to send event {args.event_type} to ChronoLog unified chronicle")
    
    sender.close()
    debug_log("Unified ChronoLog hook completed")
    
    # Always exit with 0 to not block Claude Code operations
    sys.exit(0)

if __name__ == '__main__':
    main()
