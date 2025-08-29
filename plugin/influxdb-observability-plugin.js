#!/usr/bin/env node
/**
 * InfluxDB Observability Plugin for OpenCode (Final Correct Version)
 * 
 * This plugin uses the correct OpenCode property-based plugin API
 * based on diagnostic analysis of actual OpenCode behavior.
 */

import { appendFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import https from 'https';
import http from 'http';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class SimpleInfluxDBEventSender {
  constructor() {
    this.url = process.env.INFLUXDB_URL || 'http://localhost:8086';
    this.token = process.env.INFLUXDB_TOKEN || 'claude-observability-token';
    this.org = 'events-org';  // Fixed: always use correct org
    this.bucket = 'application-events';  // Fixed: always use correct bucket
    
    if (!this.token) {
      console.warn('Warning: INFLUXDB_TOKEN not found, plugin will fail silently');
      this.enabled = false;
      return;
    }
    
    this.enabled = true;
    this.writeUrl = `${this.url}/api/v2/write?org=${this.org}&bucket=${this.bucket}&precision=ms`;
  }

  debugLog(message, data = null) {
    try {
      const logPath = join(__dirname, 'opencode_observability_debug.log');
      const timestamp = new Date().toISOString();
      appendFileSync(logPath, `[${timestamp}] ${message}\n`);
      if (data) {
        appendFileSync(logPath, `  Data: ${JSON.stringify(data, null, 2)}\n`);
      }
      appendFileSync(logPath, '\n');
    } catch (error) {
      console.error(`Debug logging failed: ${error}`);
    }
  }

  createLineProtocol(measurement, tags, fields, timestamp) {
    // Format tags
    const tagStr = Object.entries(tags)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => `${key}=${this.escapeTagValue(String(value))}`)
      .join(',');
    
    // Format fields
    const fieldStr = Object.entries(fields)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => {
        if (typeof value === 'string') {
          return `${key}="${this.escapeStringValue(value)}"`;
        } else if (typeof value === 'number') {
          // Ensure integers are sent as integers, not floats
          return Number.isInteger(value) ? `${key}=${value}i` : `${key}=${value}`;
        } else if (typeof value === 'boolean') {
          return `${key}=${value}`;
        } else {
          return `${key}="${this.escapeStringValue(JSON.stringify(value))}"`;
        }
      })
      .join(',');
    
    const line = `${measurement}${tagStr ? ',' + tagStr : ''} ${fieldStr} ${timestamp}`;
    return line;
  }

  escapeTagValue(value) {
    return value.replace(/[,= ]/g, '\\$&');
  }

  escapeStringValue(value) {
    return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  }

  simplifyPayload(payload) {
    try {
      if (typeof payload === 'object' && payload !== null) {
        // Create a simplified version of complex objects
        const simplified = {};
        
        // Extract key information without deep nesting
        if (payload.type) simplified.type = payload.type;
        if (payload.tool?.name) simplified.tool_name = payload.tool.name;
        if (payload.event?.type) simplified.event_type = payload.event.type;
        
        // Avoid including huge nested objects like 'system' arrays
        Object.keys(payload).forEach(key => {
          const value = payload[key];
          if (typeof value === 'string' && value.length < 200) {
            simplified[key] = value;
          } else if (typeof value === 'number' || typeof value === 'boolean') {
            simplified[key] = value;
          } else if (Array.isArray(value) && value.length < 5) {
            simplified[key + '_count'] = value.length;
          } else if (typeof value === 'object' && value !== null) {
            simplified[key + '_type'] = 'object';
          }
        });
        
        return JSON.stringify(simplified);
      } else {
        return JSON.stringify(payload);
      }
    } catch (error) {
      this.debugLog('Payload simplification error', error);
      return 'payload_parse_error';
    }
  }

  async sendEvent(eventData) {
    if (!this.enabled) {
      return false;
    }
    
    try {
      const chatData = eventData.chat || {};
      let chatSummary;
      
      if (Array.isArray(chatData) && chatData.length > 0) {
        chatSummary = {
          message_count: chatData.length,
          last_message_type: chatData[chatData.length - 1]?.type || 'unknown'
        };
      } else {
        chatSummary = typeof chatData === 'object' ? chatData : {};
      }
      
      const tags = {
        source_app: eventData.source_app || 'opencode-observability',
        session_id: eventData.session_id || 'unknown',
        hook_event_type: eventData.hook_event_type || 'unknown'
      };
      
      const payload = eventData.payload || {};
      if (typeof payload === 'object' && payload.tool?.name) {
        tags.tool_name = payload.tool.name;
      }
      
      if (typeof payload === 'object' && payload.type) {
        tags.message_type = payload.type;
      }
      
      const fields = {
        payload: this.simplifyPayload(payload),
        chat_data: JSON.stringify(chatSummary),
        summary: eventData.summary || '',
        event_count: 1,
        message_count: chatSummary.message_count || 0
      };
      
      const timestamp = eventData.timestamp || Date.now();
      const lineProtocol = this.createLineProtocol('opencode_events', tags, fields, timestamp);
      
      this.debugLog('Sending to InfluxDB', { url: this.writeUrl, data: lineProtocol });
      
      return await this.httpPost(this.writeUrl, lineProtocol);
      
    } catch (error) {
      this.debugLog(`Failed to send event to InfluxDB: ${error}`);
      return false;
    }
  }

  httpPost(url, data) {
    return new Promise((resolve, reject) => {
      const urlObj = new URL(url);
      const isHttps = urlObj.protocol === 'https:';
      const client = isHttps ? https : http;
      
      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || (isHttps ? 443 : 80),
        path: urlObj.pathname + urlObj.search,
        method: 'POST',
        headers: {
          'Authorization': `Token ${this.token}`,
          'Content-Type': 'text/plain',
          'Content-Length': Buffer.byteLength(data)
        }
      };
      
      const req = client.request(options, (res) => {
        let responseBody = '';
        res.on('data', (chunk) => {
          responseBody += chunk;
        });
        
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            this.debugLog('Successfully sent to InfluxDB', { status: res.statusCode });
            resolve(true);
          } else {
            this.debugLog('InfluxDB error response', { 
              status: res.statusCode, 
              body: responseBody 
            });
            resolve(false);
          }
        });
      });
      
      req.on('error', (err) => {
        this.debugLog('HTTP request error', err);
        resolve(false);
      });
      
      req.write(data);
      req.end();
    });
  }
}

// OpenCode Plugin with Property-Based API
export default function createInfluxDBObservabilityPlugin() {
  const sender = new SimpleInfluxDBEventSender();
  sender.debugLog('InfluxDB Observability Plugin created', { enabled: sender.enabled });

  const createEventData = (eventType, eventData, sessionId = 'unknown') => ({
    source_app: 'opencode-observability',
    session_id: sessionId,
    hook_event_type: eventType,
    payload: eventData,
    timestamp: Date.now()
  });

  return {
    name: "influxdb-observability",
    version: "1.0.0",
    
    // Tool execution hooks - these are the actual properties OpenCode accesses
    "tool.execute.before": async (eventData) => {
      sender.debugLog('tool.execute.before triggered', eventData);
      const event = createEventData('PreToolCall', eventData);
      await sender.sendEvent(event);
    },
    
    "tool.execute.after": async (eventData) => {
      sender.debugLog('tool.execute.after triggered', eventData);
      const event = createEventData('PostToolCall', eventData);
      await sender.sendEvent(event);
    },
    
    // Chat/message hooks - based on property accesses we observed
    "chat.message": async (eventData) => {
      sender.debugLog('chat.message triggered', eventData);
      const event = createEventData('ChatMessage', eventData);
      await sender.sendEvent(event);
    },
    
    "chat.params": async (eventData) => {
      sender.debugLog('chat.params triggered', eventData);
      const event = createEventData('ChatParams', eventData);
      await sender.sendEvent(event);
    },
    
    // Generic event handler for other property accesses
    event: async (eventData) => {
      sender.debugLog('event property accessed', eventData);
      const event = createEventData('GenericEvent', eventData);
      await sender.sendEvent(event);
    },
    
    // Config and auth handlers
    config: async (configData) => {
      sender.debugLog('config property accessed', configData);
      const event = createEventData('Config', configData);
      await sender.sendEvent(event);
    },
    
    auth: async (authData) => {
      sender.debugLog('auth property accessed', authData);
      const event = createEventData('Auth', authData);
      await sender.sendEvent(event);
    }
  };
}