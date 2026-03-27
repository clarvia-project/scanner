// ---------------------------------------------------------------------------
// Format scan results for PR comments and Job Summary
// ---------------------------------------------------------------------------

const DIMENSION_LABELS = {
  api_accessibility: 'API Accessibility',
  data_structuring: 'Data Structuring',
  agent_compatibility: 'Agent Compatibility',
  trust_signals: 'Trust Signals',
};

const RATING_EMOJI = {
  excellent: ':star2:',
  strong: ':white_check_mark:',
  moderate: ':warning:',
  weak: ':x:',
};

const GRADE_EMOJI = {
  AGENT_NATIVE: ':robot:',
  AGENT_FRIENDLY: ':handshake:',
  AGENT_POSSIBLE: ':construction:',
  AGENT_HOSTILE: ':no_entry_sign:',
};

/**
 * Format a progress bar using Unicode block characters.
 */
function progressBar(score, max, width = 20) {
  const ratio = Math.min(score / max, 1);
  const filled = Math.round(ratio * width);
  const empty = width - filled;
  return '\u2588'.repeat(filled) + '\u2591'.repeat(empty);
}

/**
 * Format results as a GitHub PR comment body.
 */
function formatComment(results, failUnder) {
  if (results.length === 0) {
    return '## Clarvia AEO Check\n\nNo scan results available.\n';
  }

  const lines = [];
  lines.push('## :owl: Clarvia AEO Check Results\n');

  if (results.length === 1) {
    lines.push(formatSingleResult(results[0], failUnder));
  } else {
    // Summary table for multiple results
    lines.push('| Source | Score | Rating | Grade |');
    lines.push('|--------|-------|--------|-------|');

    for (const r of results) {
      const emoji = RATING_EMOJI[r.rating] || '';
      const grade = r.agent_grade || 'N/A';
      lines.push(
        `| \`${r.source}\` | **${r.clarvia_score}/100** | ${emoji} ${capitalize(r.rating || 'unknown')} | ${grade} |`
      );
    }

    lines.push('');

    // Detailed breakdown for the primary (highest-scoring) result
    lines.push(`### Best Result: \`${results[0].source}\`\n`);
    lines.push(formatSingleResult(results[0], failUnder));
  }

  // Footer
  lines.push('---');
  lines.push(
    '<sub>:owl: Powered by <a href="https://clarvia.art">Clarvia</a> | ' +
    '<a href="https://github.com/marketplace/actions/clarvia-aeo-check">GitHub Action</a></sub>'
  );

  return lines.join('\n');
}

/**
 * Format a single scan result with dimension breakdown.
 */
function formatSingleResult(result, failUnder) {
  const lines = [];

  // Score header
  const emoji = RATING_EMOJI[result.rating] || '';
  const gradeEmoji = GRADE_EMOJI[result.agent_grade] || '';
  lines.push(`**Score: ${result.clarvia_score}/100** ${emoji} ${capitalize(result.rating || 'unknown')}`);
  lines.push(`**Agent Grade:** ${gradeEmoji} ${result.agent_grade || 'N/A'}\n`);

  // Badge
  if (result.badge_url) {
    lines.push(`[![AEO Score](${result.badge_url})](${result.details_url || 'https://clarvia.art'})\n`);
  }

  // Dimension breakdown
  if (result.dimensions) {
    lines.push('### Dimension Scores\n');
    lines.push('| Dimension | Score | Bar |');
    lines.push('|-----------|-------|-----|');

    for (const [key, label] of Object.entries(DIMENSION_LABELS)) {
      const dim = result.dimensions[key];
      if (dim) {
        const bar = progressBar(dim.score, dim.max);
        lines.push(`| ${label} | ${dim.score}/${dim.max} | \`${bar}\` |`);
      }
    }

    // Onchain bonus
    if (result.onchain_bonus && result.onchain_bonus.applicable) {
      const ob = result.onchain_bonus;
      const bar = progressBar(ob.score, ob.max);
      lines.push(`| :link: Onchain Bonus | ${ob.score}/${ob.max} | \`${bar}\` |`);
    }

    lines.push('');
  }

  // Recommendations
  if (result.top_recommendations && result.top_recommendations.length > 0) {
    lines.push('<details>');
    lines.push('<summary><strong>Top Recommendations</strong></summary>\n');
    for (let i = 0; i < result.top_recommendations.length; i++) {
      lines.push(`${i + 1}. ${result.top_recommendations[i]}`);
    }
    lines.push('\n</details>\n');
  }

  // Threshold status
  if (failUnder > 0) {
    const passed = result.clarvia_score >= failUnder;
    if (passed) {
      lines.push(`:white_check_mark: Score ${result.clarvia_score} meets threshold ${failUnder}\n`);
    } else {
      lines.push(`:x: Score ${result.clarvia_score} is below threshold ${failUnder}\n`);
    }
  }

  // Details link
  if (result.details_url) {
    lines.push(`:mag: [View full report](${result.details_url})\n`);
  }

  return lines.join('\n');
}

/**
 * Format results as a GitHub Actions Job Summary.
 */
function formatSummary(results, failUnder) {
  const lines = [];
  lines.push('## :owl: Clarvia AEO Scan Results\n');

  for (const result of results) {
    lines.push(`### ${result.source}\n`);
    lines.push('| Property | Value |');
    lines.push('|----------|-------|');
    lines.push(`| URL | \`${result.url || result.source}\` |`);
    lines.push(`| Score | **${result.clarvia_score}/100** |`);
    lines.push(`| Rating | ${capitalize(result.rating || 'unknown')} |`);
    lines.push(`| Agent Grade | ${result.agent_grade || 'N/A'} |`);

    if (result.scan_id) {
      lines.push(`| Scan ID | \`${result.scan_id}\` |`);
    }

    lines.push('');

    // Dimensions
    if (result.dimensions) {
      lines.push('| Dimension | Score |');
      lines.push('|-----------|-------|');

      for (const [key, label] of Object.entries(DIMENSION_LABELS)) {
        const dim = result.dimensions[key];
        if (dim) {
          lines.push(`| ${label} | ${dim.score}/${dim.max} |`);
        }
      }

      lines.push('');
    }

    if (result.badge_url) {
      lines.push(`[![AEO Score](${result.badge_url})](${result.details_url || 'https://clarvia.art'})\n`);
    }
  }

  return lines.join('\n');
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

module.exports = { formatComment, formatSummary };
