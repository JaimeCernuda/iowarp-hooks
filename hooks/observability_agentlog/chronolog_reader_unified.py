#!/usr/bin/env -S uv run --python 3.11 --script
# /// script
# requires-python = ">=3.11"
# ///

"""
ChronoLog Unified Data Reader
============================
Reads data from the unified claude_code_event chronicle and logs story
Specifically designed for the unified hook structure
"""

import sys
import time
import os
import json
from datetime import datetime

# Add ChronoLog library to path
chronolog_lib = os.path.expandvars("$HOME/chronolog-install/Debug/lib")
if chronolog_lib not in sys.path:
    sys.path.insert(0, chronolog_lib)

import py_chronolog_client

class ChronoLogUnifiedReader:
    def __init__(self):
        self.client = None
        self.connected = False
        
        # Unified chronicle and story names (matches the hook)
        self.chronicle_name = "claude_code_event"
        self.story_name = "logs"
        
        # ChronoVisor and ChronoPlayer hosts from actual configuration  
        self.portal_host = "172.25.101.25"  # ChronoVisor host (ares-comp-25)
        self.portal_port = 5555              # Portal service port
        
        # Use the correct query service configuration from the player config
        self.query_host = "127.0.0.1"   # ChronoPlayer host (ares-comp-27)  
        self.query_port = 5557               # PlaybackQueryService port from actual config
    
    def connect(self):
        """Connect to ChronoLog services"""
        try:
            print(f"Connecting to ChronoLog...")
            print(f"Portal service: {self.portal_host}:{self.portal_port}")
            print(f"Query service: {self.query_host}:{self.query_port}")
            
            # Create client configuration with both portal and query services (required for ReplayStory)
            portalConf = py_chronolog_client.ClientPortalServiceConf("ofi+sockets", self.portal_host, self.portal_port, 55)
            queryConf = py_chronolog_client.ClientQueryServiceConf("ofi+sockets", self.query_host, self.query_port, 57)
            
            # Create client with both services (needed for reading/replay operations)
            self.client = py_chronolog_client.Client(portalConf, queryConf)
            print("Created client with portal service only")
            # Connect
            result = self.client.Connect()
            if result == 0:
                self.connected = True
                print("Connected successfully to both services")
                return True
            else:
                print(f"Connection failed with code: {result}")
                print("Trying portal service only as fallback...")
                
                # Fallback to portal service only
                self.client = py_chronolog_client.Client(portalConf)
                result = self.client.Connect()
                if result == 0:
                    self.connected = True
                    print("Connected successfully to portal service (query operations may be limited)")
                    return True
                else:
                    print(f"Portal-only connection also failed with code: {result}")
                    return False
                
        except Exception as e:
            print(f"Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def read_unified_events(self, start_time=None, end_time=None, session_filter=None):
        """Read events from the unified chronicle and story"""
        if not self.connected:
            print("Error: Not connected to ChronoLog")
            return []
        
        try:
            print(f"Reading from chronicle: {self.chronicle_name}, story: {self.story_name}")
            
            # Acquire the story
            attributes = {}
            flags = 0
            print(f"Attempting to acquire story...")
            acquire_result = self.client.AcquireStory(self.chronicle_name, self.story_name, attributes, flags)
            
            print(f"AcquireStory result: {acquire_result} (type: {type(acquire_result)})")
            
            if isinstance(acquire_result, tuple):
                result_code = acquire_result[0]
                story_handle = acquire_result[1] if len(acquire_result) > 1 else None
                print(f"Acquire result code from tuple: {result_code}")
            else:
                result_code = acquire_result
                story_handle = None
                print(f"Acquire result code: {result_code}")
            
            if result_code != 0:
                print(f"Failed to acquire story {self.story_name}: code {result_code}")
                return []
            
            print("Story acquired successfully!")
            
            # Since ReplayStory might need query service, let's try to read events differently
            # Try to get events using the story handle directly if possible
            if story_handle:
                print("Trying to read events using story handle...")
                try:
                    # Check if story handle has any methods to read events
                    print(f"Story handle methods: {dir(story_handle)}")
                    
                    # ReplayStory might still work with portal service only
                    # Create event list to store results
                    event_list = py_chronolog_client.EventList()
                    
                    # Set time range based on actual file timestamps observed
                    if start_time is None:
                        start_time = 0  # Include our actual data timestamp
                    if end_time is None:
                        # end_time = 1859165000000000    # Include our actual data timestamp
                        end_time = int(time.time() * 1000000000) + 1000000000
                    
                    print(f"Querying events from {start_time} to {end_time}")
                    
                    # Try ReplayStory even with portal service only
                    replay_result = self.client.ReplayStory(self.chronicle_name, self.story_name, start_time, end_time, event_list)
                    
                    print(f"ReplayStory result: {replay_result}")
                    print(f"Event list length: {len(event_list)}")
                    
                    # Release the story
                    release_result = self.client.ReleaseStory(self.chronicle_name, self.story_name)
                    print(f"ReleaseStory result: {release_result}")
                    
                    if replay_result == 0 and len(event_list) > 0:
                        events = []
                        for i in range(len(event_list)):
                            event = event_list[i]
                            try:
                                record_data = json.loads(event.log_record())
                                
                                # Apply session filter if specified
                                if session_filter:
                                    event_session = record_data.get('session_id', '')
                                    if session_filter not in event_session:
                                        continue
                                
                                events.append({
                                    'timestamp': event.time(),
                                    'client_id': event.client_id(),
                                    'index': event.index(),
                                    'data': record_data
                                })
                            except json.JSONDecodeError:
                                events.append({
                                    'timestamp': event.time(),
                                    'client_id': event.client_id(),
                                    'index': event.index(),
                                    'raw_data': event.log_record()
                                })
                        
                        print(f"Retrieved {len(events)} events")
                        return events
                    else:
                        if replay_result != 0:
                            error_messages = {
                                -11: "Chronicle/Story not found",
                                -5: "Service error",
                                -9: "Story not acquired",
                                -12: "Invalid argument",
                                -1: "Operation not permitted"
                            }
                            error_msg = error_messages.get(replay_result, f"Unknown error code: {replay_result}")
                            print(f"ReplayStory failed: {error_msg}")
                            print("This suggests query service is required for ReplayStory operations")
                        else:
                            print("ReplayStory succeeded but no events found in the time range")
                        return []
                    
                except Exception as e:
                    print(f"Error trying to read with story handle: {e}")
                    import traceback
                    traceback.print_exc()
                    return []
            else:
                print("No story handle returned from AcquireStory")
                return []
                
        except Exception as e:
            print(f"Read error for unified story: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.client.ReleaseStory(self.chronicle_name, self.story_name)
            except:
                pass
            return []
    
    def format_timestamp(self, timestamp):
        """Format timestamp to readable date"""
        try:
            # Convert nanoseconds to seconds
            timestamp_sec = timestamp / 1000000000
            return datetime.fromtimestamp(timestamp_sec).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        except:
            return str(timestamp)
    
    def print_event_summary(self, event, event_num):
        """Print a complete summary of an event for unified structure - NO TRUNCATION"""
        print(f"\n  Event {event_num}:")
        print(f"    Timestamp: {self.format_timestamp(event['timestamp'])}")
        print(f"    Client ID: {event['client_id']}")
        print(f"    Index: {event['index']}")
        
        if 'data' in event:
            data = event['data']
            
            # Print key information from unified structure
            if 'hook_event_type' in data:
                print(f"    Event Type: {data['hook_event_type']}")
            
            if 'source_app' in data:
                print(f"    Source: {data['source_app']}")
            
            if 'session_id' in data:
                print(f"    Session: {data['session_id']}")  # Full session ID
            
            if 'processed_at' in data:
                print(f"    Processed: {data['processed_at']}")
            
            # Show complete payload
            if 'payload' in data:
                payload = data['payload']
                if isinstance(payload, dict):
                    # User prompt information - COMPLETE
                    if 'text' in payload:
                        print(f"    User Input: \"{payload['text']}\"")  # Full text
                    
                    # Tool information - COMPLETE
                    if 'tool' in payload:
                        tool_info = payload['tool']
                        if isinstance(tool_info, dict):
                            tool_name = tool_info.get('name', 'unknown')
                            print(f"    Tool Used: {tool_name}")
                            if 'input' in tool_info:
                                print(f"    Tool Input: {tool_info['input']}")  # Full input
            
            # Show complete tool results for PostToolUse events
            if data.get('hook_event_type') == 'PostToolUse':
                if 'tool_result' in data:
                    print(f"    Tool Result: {data['tool_result']}")  # Full result
                
                if 'latest_agent_response' in data:
                    agent_response = data['latest_agent_response']
                    if isinstance(agent_response, list) and len(agent_response) > 0:
                        response_text = ""
                        for content in agent_response:
                            if isinstance(content, dict) and content.get('type') == 'text':
                                response_text = content.get('text', '')
                                break
                        if response_text:
                            print(f"    Agent Response: \"{response_text}\"")  # Full response
            
            # Show chat data summary if present
            if 'chat_data' in data and data['chat_data']:
                chat_data = data.get('chat_data', [])
                if isinstance(chat_data, list) and len(chat_data) > 0:
                    print(f"    Chat Messages: {len(chat_data)} messages included")
                    # Print complete chat data
                    print(f"    Complete Chat Data: {json.dumps(chat_data, indent=6)}")
        else:
            print(f"    Raw Data: {event.get('raw_data', 'No data')}")  # Full raw data
    
    def analyze_session_activity(self, events):
        """Analyze session activity from unified events"""
        sessions = {}
        
        for event in events:
            if 'data' in event:
                data = event['data']
                session_id = data.get('session_id', 'unknown')
                event_type = data.get('hook_event_type', 'unknown')
                timestamp = event.get('timestamp', 0)
                
                if session_id not in sessions:
                    sessions[session_id] = {
                        'events': [],
                        'event_types': set(),
                        'start_time': timestamp,
                        'end_time': timestamp
                    }
                
                sessions[session_id]['events'].append(event)
                sessions[session_id]['event_types'].add(event_type)
                sessions[session_id]['start_time'] = min(sessions[session_id]['start_time'], timestamp)
                sessions[session_id]['end_time'] = max(sessions[session_id]['end_time'], timestamp)
        
        return sessions
    
    def read_all_unified_data(self, session_filter=None):
        """Read all data from unified chronicle with analysis"""
        print("=" * 70)
        print("ChronoLog Unified Data Reader")
        print("=" * 70)
        print(f"Chronicle: {self.chronicle_name}")
        print(f"Story: {self.story_name}")
        if session_filter:
            print(f"Session Filter: {session_filter}")
        print("=" * 70)
        
        # Read events
        events = self.read_unified_events(session_filter=session_filter)
        
        if not events:
            print("\nNo events found in unified chronicle")
            return {}
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda x: x.get('timestamp', 0))
        
        # Analyze sessions
        sessions = self.analyze_session_activity(sorted_events)
        
        print(f"\nTotal Events: {len(sorted_events)}")
        print(f"Sessions Found: {len(sessions)}")
        
        # Print session summary
        print(f"\nSession Summary:")
        for session_id, session_info in sessions.items():
            event_count = len(session_info['events'])
            event_types = sorted(list(session_info['event_types']))
            start_time = self.format_timestamp(session_info['start_time'])
            end_time = self.format_timestamp(session_info['end_time'])
            
            print(f"  Session {session_id}:")  # Full session ID
            print(f"    Events: {event_count}")
            print(f"    Types: {', '.join(event_types)}")
            print(f"    Time Range: {start_time} -> {end_time}")
        
        # Print chronological event flow
        print(f"\nChronological Event Flow:")
        print("-" * 50)
        
        for i, event in enumerate(sorted_events, 1):
            self.print_event_summary(event, i)
        
        return {
            'chronicle': self.chronicle_name,
            'story': self.story_name,
            'events': sorted_events,
            'sessions': sessions,
            'total_events': len(sorted_events),
            'total_sessions': len(sessions)
        }
    
    def save_complete_raw_data(self, events, filename):
        """Save complete raw event data without any processing or truncation"""
        try:
            raw_data = []
            for event in events:
                raw_data.append({
                    'timestamp': event.get('timestamp'),
                    'client_id': event.get('client_id'),
                    'index': event.get('index'),
                    'complete_data': event.get('data'),
                    'raw_data': event.get('raw_data')
                })
            
            with open(filename, 'w') as f:
                json.dump(raw_data, f, indent=2, default=str, ensure_ascii=False)
            print(f"\nComplete raw data saved to: {filename}")
        except Exception as e:
            print(f"Error saving raw data to file: {e}")
    
    def save_to_file(self, data, filename):
        """Save data to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            print(f"\nData saved to: {filename}")
        except Exception as e:
            print(f"Error saving to file: {e}")
    
    def disconnect(self):
        """Disconnect from ChronoLog"""
        if self.connected and self.client:
            try:
                result = self.client.Disconnect()
                print(f"\nDisconnected: {result}")
                self.connected = False
            except Exception as e:
                print(f"Disconnect error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Read ChronoLog unified chronicle data')
    parser.add_argument('--session', help='Filter by session ID (partial match)')
    parser.add_argument('--save', help='Save output to JSON file')
    parser.add_argument('--raw', help='Save complete raw data to JSON file (no truncation)')
    parser.add_argument('--full', action='store_true', help='Show complete data in console (no truncation)')
    
    args = parser.parse_args()
    
    reader = ChronoLogUnifiedReader()
    
    try:
        if reader.connect():
            # Read all unified data
            data = reader.read_all_unified_data(session_filter=args.session)
            
            # Save raw data if requested
            if args.raw and data:
                reader.save_complete_raw_data(data['events'], args.raw)
            
            # Save processed data if requested
            if args.save and data:
                reader.save_to_file(data, args.save)
            elif data and not args.save and not args.raw:
                # Auto-save with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"chronolog_unified_data_{timestamp}.json"
                reader.save_to_file(data, filename)
                
                # Also save raw data
                raw_filename = f"chronolog_raw_data_{timestamp}.json"
                reader.save_complete_raw_data(data['events'], raw_filename)
        
    finally:
        reader.disconnect()

if __name__ == "__main__":
    main()
