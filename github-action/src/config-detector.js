const fs = require('fs');
const path = require('path');
const core = require('@actions/core');

// ---------------------------------------------------------------------------
// MCP config file detection
// ---------------------------------------------------------------------------

// Known config file patterns and their parsers
const CONFIG_PATTERNS = [
  { glob: 'mcp.json', parser: parseMcpJson },
  { glob: 'server.json', parser: parseMcpJson },
  { glob: 'claude_desktop_config.json', parser: parseClaudeDesktopConfig },
  { glob: '.cursor/mcp.json', parser: parseMcpJson },
  { glob: '.vscode/mcp.json', parser: parseMcpJson },
  { glob: '.claude/mcp.json', parser: parseMcpJson },
  { glob: 'smithery.yaml', parser: parseSmitheryYaml },
  { glob: 'package.json', parser: parsePackageJsonMcp },
];

/**
 * Auto-detect MCP server configs in the workspace.
 * Returns array of { path, servers: [{ name, url, transport }] }
 */
async function detectConfigs() {
  const workspace = process.env.GITHUB_WORKSPACE || process.cwd();
  const found = [];

  for (const pattern of CONFIG_PATTERNS) {
    const filePath = path.join(workspace, pattern.glob);
    if (fs.existsSync(filePath)) {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        const servers = pattern.parser(content, filePath);
        if (servers.length > 0) {
          found.push({ path: pattern.glob, servers });
          core.info(`  Detected ${servers.length} server(s) in ${pattern.glob}`);
        }
      } catch (err) {
        core.debug(`Failed to parse ${filePath}: ${err.message}`);
      }
    }
  }

  // Also scan for any **/mcp.json or **/server.json in common directories
  const extraDirs = ['src', 'config', 'configs', '.config', 'mcp'];
  for (const dir of extraDirs) {
    for (const filename of ['mcp.json', 'server.json']) {
      const filePath = path.join(workspace, dir, filename);
      if (fs.existsSync(filePath)) {
        try {
          const content = fs.readFileSync(filePath, 'utf8');
          const servers = parseMcpJson(content, filePath);
          if (servers.length > 0) {
            const relPath = path.join(dir, filename);
            found.push({ path: relPath, servers });
            core.info(`  Detected ${servers.length} server(s) in ${relPath}`);
          }
        } catch (err) {
          core.debug(`Failed to parse ${filePath}: ${err.message}`);
        }
      }
    }
  }

  return found;
}

// ---------------------------------------------------------------------------
// Parsers
// ---------------------------------------------------------------------------

/**
 * Parse standard MCP JSON config format:
 * { "mcpServers": { "name": { "url": "...", "command": "..." } } }
 * or { "servers": { ... } }
 */
function parseMcpJson(content, filePath) {
  const data = JSON.parse(content);
  const servers = [];

  const serverMap = data.mcpServers || data.servers || data;

  if (typeof serverMap !== 'object' || Array.isArray(serverMap)) {
    return servers;
  }

  for (const [name, config] of Object.entries(serverMap)) {
    if (!config || typeof config !== 'object') continue;

    // Skip non-server entries (metadata fields)
    if (['$schema', 'version', 'name', 'description'].includes(name)) continue;

    const url = extractServerUrl(config);
    if (url) {
      servers.push({
        name,
        url,
        transport: config.transport || (config.command ? 'stdio' : 'sse'),
      });
    }
  }

  return servers;
}

/**
 * Parse Claude Desktop config format:
 * { "mcpServers": { "name": { "command": "...", "args": [...] } } }
 */
function parseClaudeDesktopConfig(content, filePath) {
  const data = JSON.parse(content);
  const servers = [];

  if (!data.mcpServers || typeof data.mcpServers !== 'object') {
    return servers;
  }

  for (const [name, config] of Object.entries(data.mcpServers)) {
    if (!config || typeof config !== 'object') continue;

    const url = extractServerUrl(config);
    if (url) {
      servers.push({
        name,
        url,
        transport: config.transport || (config.command ? 'stdio' : 'sse'),
      });
    }
  }

  return servers;
}

/**
 * Parse package.json for MCP-related fields.
 * Looks for: mcp, mcpServers, or bin entries with mcp-related names.
 */
function parsePackageJsonMcp(content, filePath) {
  const data = JSON.parse(content);
  const servers = [];

  // Check for explicit mcp config
  if (data.mcp && typeof data.mcp === 'object') {
    const mcpServers = data.mcp.servers || data.mcp.mcpServers;
    if (mcpServers) {
      for (const [name, config] of Object.entries(mcpServers)) {
        const url = extractServerUrl(config);
        if (url) {
          servers.push({ name, url, transport: config.transport || 'stdio' });
        }
      }
    }
  }

  // Check for homepage/repository URL as fallback for npm MCP packages
  if (servers.length === 0 && data.keywords && Array.isArray(data.keywords)) {
    const isMcp = data.keywords.some(
      k => typeof k === 'string' && (k.includes('mcp') || k.includes('model-context-protocol'))
    );
    if (isMcp) {
      const url = data.homepage || (typeof data.repository === 'string' ? data.repository : data.repository?.url);
      if (url) {
        servers.push({
          name: data.name || 'mcp-server',
          url: url.replace(/^git\+/, '').replace(/\.git$/, ''),
          transport: 'npm',
        });
      }
    }
  }

  return servers;
}

/**
 * Parse smithery.yaml for MCP server definitions.
 * Basic YAML parsing (avoids extra dependency).
 */
function parseSmitheryYaml(content, filePath) {
  const servers = [];

  // Simple line-based extraction for startCommand / url patterns
  const lines = content.split('\n');
  let currentName = null;

  for (const line of lines) {
    const nameMatch = line.match(/^\s*name:\s*['"]?(.+?)['"]?\s*$/);
    if (nameMatch) currentName = nameMatch[1];

    const urlMatch = line.match(/^\s*(?:url|endpoint|baseUrl):\s*['"]?(.+?)['"]?\s*$/);
    if (urlMatch) {
      const url = urlMatch[1];
      if (url.startsWith('http')) {
        servers.push({
          name: currentName || 'smithery-server',
          url,
          transport: 'sse',
        });
      }
    }
  }

  return servers;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extract a scannable URL from a server config object.
 */
function extractServerUrl(config) {
  if (!config || typeof config !== 'object') return null;

  // Direct URL field
  if (config.url && typeof config.url === 'string') {
    return normalizeUrl(config.url);
  }

  // SSE/streamable-http transport
  if (config.transport === 'sse' || config.transport === 'streamable-http') {
    if (config.url) return normalizeUrl(config.url);
    if (config.endpoint) return normalizeUrl(config.endpoint);
  }

  // HTTP-based args (e.g., "npx @mcp/server --port 3000")
  if (config.args && Array.isArray(config.args)) {
    for (const arg of config.args) {
      if (typeof arg === 'string' && arg.match(/^https?:\/\//)) {
        return normalizeUrl(arg);
      }
    }
  }

  // env.URL or env.BASE_URL
  if (config.env && typeof config.env === 'object') {
    for (const [key, val] of Object.entries(config.env)) {
      if (
        typeof val === 'string' &&
        val.match(/^https?:\/\//) &&
        /url|endpoint|base|host/i.test(key)
      ) {
        return normalizeUrl(val);
      }
    }
  }

  return null;
}

function normalizeUrl(url) {
  url = url.trim();
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = `https://${url}`;
  }
  return url.replace(/\/+$/, '');
}

module.exports = { detectConfigs };
