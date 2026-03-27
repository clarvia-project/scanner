const fs = require('fs');
const core = require('@actions/core');

// ---------------------------------------------------------------------------
// Clarvia API client
// ---------------------------------------------------------------------------

const USER_AGENT = 'clarvia-aeo-check/1.0.0 (GitHub Action)';
const REQUEST_TIMEOUT_MS = 120_000; // 2 minutes

/**
 * Scan a URL via the Clarvia /api/scan endpoint.
 */
async function scanUrl(apiUrl, url, apiKey) {
  const endpoint = `${apiUrl}/api/scan`;

  core.debug(`POST ${endpoint} with url=${url}`);

  const headers = {
    'Content-Type': 'application/json',
    'User-Agent': USER_AGENT,
  };

  if (apiKey) {
    headers['X-Clarvia-Key'] = apiKey;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify({ url }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      let errorMessage;
      try {
        const parsed = JSON.parse(errorBody);
        errorMessage = parsed.detail || parsed.error?.message || errorBody;
      } catch {
        errorMessage = errorBody;
      }
      throw new Error(`API returned HTTP ${response.status}: ${errorMessage}`);
    }

    const data = await response.json();

    // Normalize response with computed fields
    return {
      ...data,
      badge_url: `${apiUrl}/api/badge/${data.service_name || data.scan_id}`,
      details_url: `https://clarvia.art/scan/${data.scan_id}`,
    };
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Scan a local config file by extracting URLs and scanning each.
 */
async function scanConfig(apiUrl, configPath, apiKey) {
  const workspace = process.env.GITHUB_WORKSPACE || process.cwd();
  const fullPath = require('path').resolve(workspace, configPath);

  if (!fs.existsSync(fullPath)) {
    throw new Error(`Config file not found: ${configPath}`);
  }

  const content = fs.readFileSync(fullPath, 'utf8');
  let data;
  try {
    data = JSON.parse(content);
  } catch {
    throw new Error(`Failed to parse ${configPath} as JSON`);
  }

  // Try to extract a URL to scan
  const url = data.url || data.endpoint || data.baseUrl || data.homepage;
  if (!url) {
    throw new Error(`No scannable URL found in ${configPath}`);
  }

  return scanUrl(apiUrl, url, apiKey);
}

module.exports = { scanUrl, scanConfig };
