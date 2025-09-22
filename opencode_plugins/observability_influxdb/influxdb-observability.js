#!/usr/bin/env node

/**
 * OpenCode InfluxDB Observability Plugin - Complete Event Capture
 * 
 * This plugin captures ALL OpenCode events including MCP tools with comprehensive logging.
 * Based on OpenCode Plugin System documentation with full event coverage.
 * 
 * @version 3.0.0
 * @author OpenCode Observability Team
 * @license MIT
 */

import { InfluxDB, Point } from '@influxdata/influxdb-client';
import { config } from 'dotenv';
import { appendFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from .env file in the same directory
config({ path: join(__dirname, '.env') });

/**
 * Enhanced debug logging utility
 * Logs everything when DEBUG_LOGGING is enabled
 */
function debugLog(message, data = null) {
  if (!process.env.DEBUG_LOGGING) return;
  
  try {
    const logPath = join(__dirname, 'plugin-debug.log');
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}\n`;
    const dataMessage = data ? `  Data: ${JSON.stringify(data, null, 2)}\n\n` : '\n';
    
    appendFileSync(logPath, logMessage + dataMessage);
  } catch (error) {
    console.error('Debug logging failed:', error);
  }
}

/**
 * Enhanced InfluxDB Event Sender Class
 */
class OpenCodeInfluxDBSender {
  constructor() {
    this.url = process.env.INFLUXDB_URL || 'http://localhost:8086';
    this.token = process.env.INFLUXDB_TOKEN;
    this.org = process.env.INFLUXDB_ORG || 'my-org';
    this.bucket = process.env.INFLUXDB_BUCKET || 'application-events';
    
    if (!this.token) {
      throw new Error('INFLUXDB_TOKEN environment variable is required');
    }
    
    this.client = new InfluxDB({ url: this.url, token: this.token });
    this.writeApi = this.client.getWriteApi(this.org, this.bucket);
    this.writeApi.useDefaultTags({ source_app: 'opencode-observability' });
    
    debugLog('InfluxDB client initialized', { url: this.url, org: this.org, bucket: this.bucket });
  }

  /**
   * Enhanced event sender with comprehensive data capture
   */
  async sendEvent(eventType, eventData) {
    try {
      const sessionId = this.extractSessionId(eventData);
      const toolName = this.extractToolName(eventData);
      
      debugLog(`📤 Sending event: ${eventType}`, {
        sessionId,
        toolName,
        eventType,
        hasData: !!eventData
      });

      const point = new Point('opencode_events')
        .tag('event_type', eventType)
        .tag('session_id', sessionId)
        .tag('tool_name', toolName || 'none')
        .timestamp(new Date(eventData.timestamp || Date.now()));

      // Add comprehensive fields based on event type
      if (eventType.includes('tool') || eventType === 'mcp_tool_detected') {
        this.addToolFields(point, eventData, toolName);
      } else if (eventType.startsWith('chat')) {
        this.addChatFields(point, eventData);
      } else if (eventType.startsWith('storage')) {
        this.addStorageFields(point, eventData);
      } else if (eventType.startsWith('message')) {
        this.addMessageFields(point, eventData);
      } else {
        // Generic fields for all other events
        point
          .stringField('payload', JSON.stringify(eventData))
          .intField('event_count', 1);
      }

      this.writeApi.writePoint(point);
      await this.writeApi.flush();
      
      debugLog(`✅ Event ${eventType} sent successfully`, { sessionId, toolName });
    } catch (error) {
      debugLog(`❌ Failed to send event ${eventType}: ${error.message}`, { eventData });
      // Don't throw - keep the plugin running even if InfluxDB fails
    }
  }

  /**
   * Extract session ID from various event structures
   */
  extractSessionId(eventData) {
    if (eventData.sessionId) return eventData.sessionId;
    if (eventData.session_id) return eventData.session_id;
    if (eventData.event?.sessionId) return eventData.event.sessionId;
    if (eventData.properties?.key) {
      // Match session ID from keys like: session/message/ses_7092ed68effekR7PG9gYSq5evd/msg_...
      const match = eventData.properties.key.match(/session\/[^\/]+\/(ses_[^\/]+)/);
      if (match) return match[1];
    }
    // Also try to extract from data.key if available
    if (eventData.key) {
      const match = eventData.key.match(/session\/[^\/]+\/(ses_[^\/]+)/);
      if (match) return match[1];
    }
    return 'unknown';
  }

  /**
   * Extract tool name from various event structures
   */
  extractToolName(eventData) {
    // Direct tool name
    if (eventData.tool) return eventData.tool;
    if (eventData.toolName) return eventData.toolName;
    
    // From storage events
    if (eventData.properties?.key) {
      const key = eventData.properties.key;
      if (key.includes('node_hardware')) return 'Node_hardware_get_cpu_info';
      if (key.includes('tool')) return 'mcp_tool';
    }
    
    // From event data
    if (eventData.event?.tool) return eventData.event.tool;
    if (eventData.event?.properties?.content?.type === 'tool') return 'mcp_tool';
    
    return null;
  }

  /**
   * Add tool-specific fields to the point
   */
  addToolFields(point, eventData, toolName) {
    point
      .tag('call_id', eventData.callId || 'unknown')
      .stringField('tool_data', JSON.stringify(eventData))
      .stringField('args', JSON.stringify(eventData.args || {}))
      .stringField('result', JSON.stringify(eventData.result || {}))
      .intField('event_count', 1);
      
    if (eventData.result?.success !== undefined) {
      point.booleanField('success', eventData.result.success);
    }
  }

  /**
   * Add chat-specific fields
   */
  addChatFields(point, eventData) {
    point
      .intField('message_count', eventData.parts?.length || 0)
      .stringField('message_data', JSON.stringify(eventData.message || {}))
      .intField('event_count', 1);

    if (eventData.model?.name) {
      point.tag('model_name', eventData.model.name);
    }
    if (eventData.provider?.info?.id) {
      point.tag('provider_id', eventData.provider.info.id);
    }
    if (eventData.temperature !== undefined) {
      point.floatField('temperature', eventData.temperature);
    }
  }

  /**
   * Add storage-specific fields
   */
  addStorageFields(point, eventData) {
    point
      .stringField('storage_key', eventData.properties?.key || 'unknown')
      .stringField('content_type', eventData.properties?.content?.type || 'unknown')
      .stringField('storage_data', JSON.stringify(eventData))
      .intField('event_count', 1);
  }

  /**
   * Add message-specific fields
   */
  addMessageFields(point, eventData) {
    point
      .stringField('message_content', JSON.stringify(eventData.event || {}))
      .intField('event_count', 1);
  }

  async close() {
    try {
      await this.writeApi.close();
      debugLog('InfluxDB connection closed');
    } catch (error) {
      debugLog(`Error closing InfluxDB connection: ${error.message}`);
    }
  }
}

/**
 * OpenCode Plugin Export - Complete Event Capture
 */
export const InfluxDBObservabilityPlugin = async ({ app, client, $ }) => {
  debugLog('🚀 Initializing OpenCode InfluxDB Observability Plugin v3.0.0');
  debugLog('App context', { 
    hasApp: !!app, 
    hasClient: !!client, 
    hasShell: !!$,
    cwd: app?.path?.cwd 
  });
  
  // Initialize the InfluxDB sender
  const sender = new OpenCodeInfluxDBSender();
  
  // Test connection on startup
  try {
    await sender.sendEvent('plugin_startup', {
      sessionId: 'startup',
      timestamp: new Date().toISOString(),
      message: 'OpenCode InfluxDB plugin v3.0.0 started successfully',
      app_info: {
        cwd: app?.path?.cwd,
        root: app?.path?.root
      }
    });
    debugLog('✅ Plugin startup test event sent successfully');
  } catch (error) {
    debugLog(`❌ Plugin startup test failed: ${error.message}`);
  }
  
  debugLog('🎯 OpenCode InfluxDB plugin initialized successfully');
  
  return {
    // Plugin metadata
    name: 'opencode-influxdb-observability',
    version: '3.0.0',
    description: 'InfluxDB observability plugin - complete event capture including MCP tools',
    
    // GENERIC EVENT HANDLER - Captures ALL events including MCP tools
    event: async ({ event }) => {
      const eventType = event?.type || 'unknown_event';
      const sessionId = sender.extractSessionId({ event, sessionId: event?.sessionId, properties: event?.properties });
      const toolName = sender.extractToolName({ event, properties: event?.properties });
      
      debugLog(`🔍 GENERIC EVENT: ${eventType}`, {
        type: eventType,
        sessionId,
        toolName,
        hasProperties: !!event?.properties,
        hasContent: !!event?.properties?.content,
        contentType: event?.properties?.content?.type,
        key: event?.properties?.key
      });

      // Special handling for storage events (where MCP tools are)
      if (eventType === 'storage.write') {
        const contentType = event?.properties?.content?.type;
        const storageKey = event?.properties?.key || '';
        
        debugLog(`📁 STORAGE EVENT - ${contentType}`, {
          key: storageKey,
          contentType,
          sessionId,
          isToolContent: contentType === 'tool',
          isMCPTool: storageKey.includes('node_hardware') || storageKey.includes('mcp')
        });

        if (contentType === 'tool' || storageKey.includes('node_hardware')) {
          debugLog('🎯 MCP TOOL DETECTED!', {
            sessionId,
            toolName: toolName || 'detected_mcp_tool',
            key: storageKey,
            contentType
          });
          
          // Send specific MCP tool event
          await sender.sendEvent('mcp_tool_execution', {
            sessionId,
            toolName: toolName || 'mcp_tool',
            storage_key: storageKey,
            content_type: contentType,
            tool_content: event.properties?.content,
            timestamp: new Date().toISOString(),
            event
          });
        }
      }

      // Send the generic event
      await sender.sendEvent(eventType, {
        sessionId,
        toolName,
        timestamp: new Date().toISOString(),
        event
      });
    },
    
    // SPECIFIC HOOK EVENTS with enhanced logging
    "chat.message": async ({ message, parts, sessionId }) => {
      debugLog('💬 CHAT MESSAGE', { 
        sessionId, 
        partsCount: parts?.length,
        messageType: typeof message,
        hasContent: !!message 
      });
      
      await sender.sendEvent('chat.message', {
        sessionId,
        message,
        parts,
        timestamp: new Date().toISOString()
      });
    },
    
    "chat.params": async ({ model, provider, temperature, topP, sessionId }) => {
      debugLog('⚙️ CHAT PARAMS', { 
        sessionId, 
        modelName: model?.name,
        providerId: provider?.info?.id,
        temperature,
        topP
      });
      
      await sender.sendEvent('chat.params', {
        sessionId,
        model,
        provider,
        temperature,
        topP,
        timestamp: new Date().toISOString()
      });
    },
    
    "permission.ask": async ({ permission, sessionId }) => {
      debugLog('🔒 PERMISSION REQUEST', { 
        sessionId, 
        permissionType: permission?.type,
        permissionId: permission?.id
      });
      
      await sender.sendEvent('permission.ask', {
        sessionId,
        permission,
        timestamp: new Date().toISOString()
      });
    },
    
    "tool.execute.before": async (eventData) => {
      const sessionId = eventData.sessionId;
      const toolName = eventData.tool;
      
      debugLog('🔧 TOOL EXECUTE BEFORE', {
        sessionId,
        tool: toolName,
        callId: eventData.callId,
        hasArgs: !!eventData.args
      });
      
      await sender.sendEvent('tool.execute.before', {
        sessionId,
        tool: toolName,
        callId: eventData.callId,
        args: eventData.args,
        timestamp: new Date().toISOString()
      });
    },
    
    "tool.execute.after": async (eventData) => {
      const sessionId = eventData.sessionId;
      const toolName = eventData.tool;
      
      debugLog('✅ TOOL EXECUTE AFTER', {
        sessionId,
        tool: toolName,
        callId: eventData.callId,
        success: eventData.result?.success,
        hasResult: !!eventData.result
      });
      
      await sender.sendEvent('tool.execute.after', {
        sessionId,
        tool: toolName,
        callId: eventData.callId,
        result: eventData.result,
        timestamp: new Date().toISOString()
      });
    },
    
    config: async (configData) => {
      debugLog('🔧 CONFIG EVENT', { 
        configKeys: Object.keys(configData || {}),
        hasPlugins: !!(configData?.plugin),
        pluginCount: Array.isArray(configData?.plugin) ? configData.plugin.length : 0
      });
      
      await sender.sendEvent('config', {
        config: configData,
        timestamp: new Date().toISOString()
      });
    },
    
    auth: async (authData) => {
      debugLog('🔐 AUTH EVENT', { 
        authKeys: Object.keys(authData || {}),
        hasAuthData: !!authData
      });
      
      await sender.sendEvent('auth', {
        auth: authData,
        timestamp: new Date().toISOString()
      });
    }
  };
};
