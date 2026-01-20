# Contributing to ASoc

Thank you for your interest in contributing to ASoc! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

Open an issue on GitHub with:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Any error messages

### Suggesting Features

Open a discussion on GitHub to:
- Describe the use case
- Explain why it's valuable
- Propose implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly (`python test_setup.py`)
5. Run benchmarks to check for regressions
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

## Development Setup

```bash
git clone https://github.com/yourusername/asoc-protocol.git
cd asoc-protocol
python test_setup.py  # Verify setup
python benchmark_ready.py  # Run benchmarks
```

No dependencies to install!

## Code Style

- Follow PEP 8
- Use type hints where appropriate
- Add docstrings to public functions
- Keep functions focused and small
- Prefer clarity over cleverness

## Testing

Before submitting a PR:

```bash
# Test basic functionality
python test_setup.py

# Run full benchmark suite
python benchmark_ready.py

# Test static configuration
python -c "from asoc import NodeReady; print('OK')"
```

## Areas We Need Help

### High Priority
- PyTorch DDP backend integration
- JAX integration
- Comprehensive test suite
- Documentation improvements

### Medium Priority
- RDMA transport layer
- GPU-Direct support
- mDNS/Avahi discovery
- Compression strategies

### Advanced
- Rust implementation for performance
- QUIC transport variant
- Cross-language bindings (Go, C++)

## Protocol Changes

Changes to the wire protocol require:
- RFC-style document explaining the change
- Backward compatibility plan
- Performance impact analysis
- Community discussion

## Documentation

Help us improve docs:
- Fix typos
- Add examples
- Clarify confusing sections
- Write tutorials
- Create diagrams

## Community

- Be respectful and inclusive
- Help newcomers
- Share your use cases
- Give constructive feedback

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Open a discussion on GitHub or reach out to the maintainers.

Thank you for helping make ASoc better! 🚀
