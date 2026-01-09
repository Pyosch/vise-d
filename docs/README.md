# VISE-D Documentation

**Last Updated:** January 2026

Welcome to the VISE-D documentation! This guide helps you navigate our comprehensive documentation for users, developers, and contributors.

## 📚 Documentation Structure

```
docs/
├── getting-started/     # Installation, quickstart, configuration
├── user-guide/          # Using VISE-D features
├── developer-guide/     # Architecture, testing, contributing
├── reference/           # API reference (future)
└── project/             # Project management, phase reports
```

## 🚀 Getting Started

**New to VISE-D? Start here:**

1. **[Installation Guide](getting-started/installation.md)** (10 minutes)
   - System requirements
   - Step-by-step installation
   - Troubleshooting common issues
   - Platform-specific notes

2. **[Quickstart Guide](getting-started/quickstart.md)** (5 minutes)
   - 5-minute setup walkthrough
   - First steps in dashboard
   - Key features overview
   - Common workflows

3. **[Configuration Guide](getting-started/configuration.md)** (15 minutes)
   - MaStR database setup
   - Weather data configuration
   - Environment variables
   - Advanced settings

## 👥 User Guide

**Learn how to use VISE-D features:**

### Energy Forecasting
- **[Forecasting Guide](user-guide/forecasting.md)** - OpenSTEF integration, model training, predictions

### Technology Components
- PV Configuration - Solar system design
- Wind Configuration - Wind turbine setup
- BEV Settings - Electric vehicle modeling
- Heat Pump Configuration - Thermal load analysis
- Storage Systems - Battery and thermal storage

### Data Analysis
- MaStR Data Analysis - Exploring 26,000+ installations
- Energy Generation - Solar and wind analysis
- Network Calculations - Grid power flow

### Planning Tools
- FFPV & WEA Planning - Site planning for solar/wind
- Obstacle Detection - OpenStreetMap integration
- Energy Simulation - Generation forecasting

## 🛠️ Developer Guide

**Contributing to VISE-D:**

### Architecture
- **[Architecture Documentation](developer-guide/architecture.md)** - System design, module structure, data flow

### Development Workflow
- **[Testing Guide](developer-guide/testing.md)** - Running tests, writing tests, coverage
- **[Caching Guide](developer-guide/caching.md)** - Performance optimization, cache strategy

### Contributing
- Code standards (PEP 8, Black formatter)
- Git workflow (conventional commits)
- Pull request process
- Documentation guidelines

## 📖 Reference

**Technical reference materials:**

### API Documentation (Future)
- Module APIs
- Function references
- Class hierarchies

### Data Schemas
- MaStR database schema
- vpplib component interfaces
- Configuration file formats

## 📋 Project Management

**Project status and planning:**

### Current Status
- **[Roadmap](../roadmap.md)** - Development phases, future plans, technical debt

### Phase Reports
- **[Phase 0: Foundation](project/phase-reports/phase-0-foundation.md)** - Directory structure, configuration
- **[Phase 1: Core Migration](project/phase-reports/phase-1-core-migration.md)** - Utils, MaStR, forecasting
- **[Phase 2: Planning & Visualization](project/phase-reports/phase-2-planning-visualization.md)** - Solar/wind planning
- **[Phase 3: UI Components](project/phase-reports/phase-3-ui-components.md)** - Technology forms
- **[Phase 4: Data Layer](project/phase-reports/phase-4-data-layer.md)** - Caching, loaders
- **[Phase 5: Page Extraction](project/phase-reports/phase-5-page-extraction.md)** - Dashboard modularization

## 🔍 Quick Links by Topic

### Installation & Setup
- [Installation](getting-started/installation.md) | [Quickstart](getting-started/quickstart.md) | [Configuration](getting-started/configuration.md)

### Using VISE-D
- [Forecasting](user-guide/forecasting.md) | Technology Configuration | MaStR Analysis | Planning Tools

### Development
- [Architecture](developer-guide/architecture.md) | [Testing](developer-guide/testing.md) | [Caching](developer-guide/caching.md)

### Project Info
- [Roadmap](../roadmap.md) | [Phase Reports](project/phase-reports/) | [README](../README.md)

## 🎯 Documentation by Role

### I'm a New User
1. [Installation Guide](getting-started/installation.md) - Get VISE-D running
2. [Quickstart Guide](getting-started/quickstart.md) - First 5 minutes
3. [User Guide](user-guide/) - Learn features

### I'm an Energy Analyst
1. [MaStR Analysis](user-guide/) - Explore installations
2. [Forecasting Guide](user-guide/forecasting.md) - Energy predictions
3. [Network Analysis](user-guide/) - Grid impact

### I'm a Researcher
1. Research Results - Published studies
2. [Forecasting Guide](user-guide/forecasting.md) - ML models
3. Network Analysis - DSO interventions

### I'm a Developer
1. [Architecture](developer-guide/architecture.md) - System design
2. [Testing Guide](developer-guide/testing.md) - Development workflow
3. [Roadmap](../roadmap.md) - Contribution opportunities

### I'm a System Administrator
1. [Installation Guide](getting-started/installation.md) - Deployment
2. [Configuration Guide](getting-started/configuration.md) - System setup
3. [Caching Guide](developer-guide/caching.md) - Performance tuning

## 📊 Project Status (January 2026)

✅ **Phase 0-5:** Complete (refactoring from monolithic to modular architecture)  
🔄 **Phase 6:** In progress (test coverage expansion 30% → 70%)  
📋 **Phase 7-8:** Future (tariff design, multi-scenario planning)

**Dashboard:** 913 lines → 89 lines (90.2% reduction)  
**Test Coverage:** 30% (target 70% → 90%)  
**Documentation:** Comprehensive guides for all features

## 🤝 Contributing

VISE-D is an open-source project. Contributions welcome!

### Ways to Contribute
- **Report bugs** - GitHub Issues
- **Suggest features** - GitHub Discussions
- **Improve documentation** - Submit pull requests
- **Write tests** - Expand test coverage
- **Add features** - Check [Roadmap](../roadmap.md) for ideas

### Development Guidelines
- **Code Style:** PEP 8, Black formatter (line length 88)
- **Language Policy:** English code/comments, German UI text
- **Testing:** pytest, >70% coverage target
- **Commits:** Conventional commits (feat:, fix:, docs:, test:)
- **Attribution:** `__author__ = "Pyosch"`, `__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]`

See [Developer Guide](developer-guide/) for details.

## 📞 Getting Help

### Documentation Issues
- **Missing info?** Open issue with "documentation" label
- **Unclear guide?** Suggest improvements in discussions
- **Found error?** Submit pull request with fix

### Technical Support
- **Installation problems:** See [Installation Troubleshooting](getting-started/installation.md#troubleshooting)
- **Usage questions:** Check [User Guide](user-guide/) or ask in discussions
- **Bugs:** Report on GitHub Issues with reproduction steps

### Community
- **GitHub Discussions** - Questions, ideas, showcases
- **GitHub Issues** - Bug reports, feature requests
- **Pull Requests** - Code contributions

## 🗺️ Documentation Roadmap

### Planned Documentation (Phase 6)
- [ ] Complete API reference documentation
- [ ] Video tutorials for key workflows
- [ ] FAQ section
- [ ] Performance tuning guide
- [ ] Deployment guide (Docker, cloud)

### Planned Examples (Phase 7-8)
- [ ] Tariff design examples
- [ ] Multi-scenario planning tutorials
- [ ] Advanced forecasting techniques
- [ ] Custom component development

## 📄 License

Documentation is licensed under [insert license]. Code under [insert license].

---

**Need something not covered here?** Open an issue or discussion on GitHub!

**Author:** Pyosch  
**AI Assistance:** GitHub Copilot (Claude Sonnet 4.5)
