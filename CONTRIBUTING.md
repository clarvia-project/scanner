# Contributing to Clarvia

Thank you for your interest in contributing to Clarvia! We welcome contributions from the community to help improve AI agent tool discovery and quality scoring.

## How to Contribute

### Reporting Issues

- Use [GitHub Issues](https://github.com/clarvia-project/scanner/issues) for bug reports and feature requests
- Search existing issues before creating new ones
- Include reproduction steps for bugs

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

### Code Style

- Use consistent formatting (Prettier for JS/TS, Black for Python)
- Add tests for new features
- Update documentation for API changes

### Areas Where We Need Help

- **Tool Coverage**: Help us index more AI agent tools
- **Scoring Algorithms**: Improve our AEO scoring methodology
- **MCP Integration**: Add new MCP tools or improve existing ones
- **Documentation**: Improve guides, examples, and API docs
- **Translations**: Help translate documentation
- **Testing**: Write tests, report edge cases

### Adding New Tool Sources

If you know of AI agent tool directories or registries we should index:

1. Open an issue with the source URL and description
2. Or submit a PR adding the scanner for that source

### Development Setup

```bash
# Clone the repo
git clone https://github.com/clarvia-project/scanner.git
cd scanner

# Backend (Python)
cd backend
pip install -r requirements.txt
python app.py

# MCP Server (Node.js)
npm install
npx clarvia-mcp-server
```

### Commit Messages

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance

## Code of Conduct

Be respectful, inclusive, and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open a [Discussion](https://github.com/clarvia-project/scanner/discussions)
- Check our [API Docs](https://clarvia-api.onrender.com/openapi.json)
