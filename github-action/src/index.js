const core = require('@actions/core');
const github = require('@actions/github');
const { detectConfigs } = require('./config-detector');
const { scanUrl, scanConfig } = require('./api-client');
const { formatComment, formatSummary } = require('./formatter');

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

async function run() {
  try {
    const url = core.getInput('url');
    const configPaths = core.getInput('config-paths');
    const failUnder = parseInt(core.getInput('fail-under'), 10) || 0;
    const apiUrl = core.getInput('api-url');
    const apiKey = core.getInput('api-key');
    const postComment = core.getInput('post-comment') === 'true';
    const commentHeader = core.getInput('comment-header');
    const failOnError = core.getInput('fail-on-error') === 'true';
    const githubToken = core.getInput('github-token');

    let results = [];

    // Strategy 1: Explicit URL scan
    if (url) {
      core.info(`Scanning URL: ${url}`);
      const result = await scanUrl(apiUrl, url, apiKey);
      results.push({ source: url, type: 'url', ...result });
    }

    // Strategy 2: Explicit config paths
    if (configPaths) {
      const paths = configPaths.split(',').map(p => p.trim()).filter(Boolean);
      core.info(`Scanning ${paths.length} config file(s): ${paths.join(', ')}`);
      for (const path of paths) {
        try {
          const result = await scanConfig(apiUrl, path, apiKey);
          results.push({ source: path, type: 'config', ...result });
        } catch (err) {
          core.warning(`Failed to scan config ${path}: ${err.message}`);
        }
      }
    }

    // Strategy 3: Auto-detect MCP configs in the repo
    if (!url && !configPaths) {
      core.info('No URL or config paths specified. Auto-detecting MCP server configs...');
      const configs = await detectConfigs();
      core.setOutput('configs-found', configs.length.toString());

      if (configs.length === 0) {
        core.warning(
          'No MCP server configs found. Provide a URL or config-paths input, ' +
          'or add an MCP config file (mcp.json, server.json, claude_desktop_config.json, etc.).'
        );
        core.setOutput('score', '0');
        core.setOutput('passed', 'true');
        return;
      }

      core.info(`Found ${configs.length} config(s): ${configs.map(c => c.path).join(', ')}`);

      for (const config of configs) {
        for (const server of config.servers) {
          try {
            core.info(`  Scanning server "${server.name}" from ${config.path}...`);
            const result = await scanUrl(apiUrl, server.url, apiKey);
            results.push({
              source: `${config.path} -> ${server.name}`,
              type: 'auto-detected',
              serverName: server.name,
              ...result,
            });
          } catch (err) {
            core.warning(`Failed to scan server "${server.name}": ${err.message}`);
          }
        }
      }
    }

    if (results.length === 0) {
      if (failOnError) {
        core.setFailed('No scan results obtained.');
      } else {
        core.warning('No scan results obtained.');
        core.setOutput('score', '0');
        core.setOutput('passed', 'true');
      }
      return;
    }

    // Use the best score as the primary result
    results.sort((a, b) => (b.clarvia_score || 0) - (a.clarvia_score || 0));
    const primary = results[0];

    // Set outputs
    core.setOutput('score', String(primary.clarvia_score || 0));
    core.setOutput('rating', primary.rating || 'unknown');
    core.setOutput('agent-grade', primary.agent_grade || 'AGENT_HOSTILE');
    core.setOutput('scan-id', primary.scan_id || '');
    core.setOutput('badge-url', primary.badge_url || '');
    core.setOutput('details-url', primary.details_url || '');
    core.setOutput('results-json', JSON.stringify(results));
    core.setOutput('configs-found', String(results.length));

    const passed = primary.clarvia_score >= failUnder;
    core.setOutput('passed', String(passed));

    // Write Job Summary
    const summary = formatSummary(results, failUnder);
    await core.summary.addRaw(summary).write();

    // Post PR comment
    if (postComment && github.context.payload.pull_request) {
      await postPRComment(githubToken, commentHeader, results, failUnder);
    }

    // Threshold check
    if (!passed) {
      core.setFailed(
        `AEO score ${primary.clarvia_score}/100 is below threshold ${failUnder}. ` +
        `Improve your score at ${primary.details_url || 'https://clarvia.art'}`
      );
    }
  } catch (error) {
    const failOnError = core.getInput('fail-on-error') === 'true';
    if (failOnError) {
      core.setFailed(`Clarvia AEO Check failed: ${error.message}`);
    } else {
      core.warning(`Clarvia AEO Check encountered an error: ${error.message}`);
    }
  }
}

// ---------------------------------------------------------------------------
// Post / update PR comment
// ---------------------------------------------------------------------------

async function postPRComment(token, header, results, failUnder) {
  try {
    const octokit = github.getOctokit(token);
    const { owner, repo } = github.context.repo;
    const prNumber = github.context.payload.pull_request.number;

    const body = header + '\n' + formatComment(results, failUnder);

    // Find existing comment to update
    const { data: comments } = await octokit.rest.issues.listComments({
      owner,
      repo,
      issue_number: prNumber,
      per_page: 100,
    });

    const existing = comments.find(c => c.body && c.body.includes(header));

    if (existing) {
      await octokit.rest.issues.updateComment({
        owner,
        repo,
        comment_id: existing.id,
        body,
      });
      core.info(`Updated existing PR comment #${existing.id}`);
    } else {
      await octokit.rest.issues.createComment({
        owner,
        repo,
        issue_number: prNumber,
        body,
      });
      core.info('Posted new PR comment with AEO results');
    }
  } catch (err) {
    core.warning(`Failed to post PR comment: ${err.message}`);
  }
}

run();
