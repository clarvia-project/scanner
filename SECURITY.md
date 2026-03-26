# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Clarvia, please report it responsibly.

### How to Report

1. **Do NOT open a public issue** for security vulnerabilities
2. Email security concerns to the repository maintainers via GitHub's private vulnerability reporting
3. Go to [Security Advisories](https://github.com/clarvia-project/scanner/security/advisories) and click "Report a vulnerability"

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix/Patch**: Depends on severity (critical: ASAP, high: 1 week, medium: 2 weeks)

## Security Practices

### API Security
- All API endpoints use HTTPS
- Rate limiting is enforced
- No authentication required for read-only public data
- API keys required for write operations

### Data Handling
- Clarvia indexes publicly available tool metadata only
- No user credentials or private data are stored
- Tool scores are computed from public signals

### MCP Server Security
- The MCP server operates in read-only mode
- No filesystem access beyond its own configuration
- All external API calls use HTTPS
- No sensitive data is transmitted to third parties

### Dependencies
- Dependencies are regularly updated
- npm audit and pip audit are run on CI
- Known vulnerabilities are patched promptly

## Scope

The following are in scope for security reports:
- Clarvia API (clarvia-api.onrender.com)
- Clarvia MCP Server (npm: clarvia-mcp-server)
- Clarvia website (clarvia.art)
- GitHub repository code

Out of scope:
- Third-party services we integrate with
- Social engineering attacks
- Denial of service attacks
