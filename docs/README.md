# VISE-D Documentation

Welcome to the VISE-D documentation. This index helps you navigate the guides for users,
developers, and contributors.

## Documentation Structure

```
docs/
├── getting-started/     # Installation, quickstart, configuration
├── developer-guide/     # Architecture, testing, caching
└── project/             # Dashboard documentation and phase reports
```

## Getting Started

1. **[Installation Guide](getting-started/installation.md)** - System requirements and setup
2. **[Quickstart Guide](getting-started/quickstart.md)** - Short setup walkthrough
3. **[Configuration Guide](getting-started/configuration.md)** - MaStR database, weather data,
   environment variables

## Using VISE-D

- **[Dashboard Documentation](project/dashboard-dokumentation.md)** - Page-by-page guide to the
  dashboard and its analyses (German). This is the primary user-facing reference.

## Developer Guide

- **[Architecture](developer-guide/architecture.md)** - System design, module structure, data flow
- **[Testing Guide](developer-guide/testing.md)** - Running and writing tests, coverage
- **[Caching Guide](developer-guide/caching.md)** - Performance and cache strategy

## Project

- **[Project Overview](../roadmap.md)** - Project status, architecture summary, known limitations
- **Phase Reports** - History of the refactoring from a monolithic dashboard to the modular
  `src/` structure:
  - [Phase 0: Foundation](project/phase-reports/phase-0-foundation.md)
  - [Phase 1: Core Migration](project/phase-reports/phase-1-core-migration.md)
  - [Phase 2: Planning & Visualization](project/phase-reports/phase-2-planning-visualization.md)
  - [Phase 3: UI Components](project/phase-reports/phase-3-ui-components.md)
  - [Phase 4: Data Layer](project/phase-reports/phase-4-data-layer.md)
  - [Phase 5: Page Extraction](project/phase-reports/phase-5-page-extraction.md)

## Contributing

- **Code Style:** PEP 8, Black formatter (line length 88)
- **Language Policy:** English code/comments, German UI text
- **Testing:** pytest (markers `unit`, `integration`, `ui`, `slow`)
- **Commits:** Conventional commits (feat:, fix:, docs:, test:, refactor:, chore:)
- **Attribution:** `__author__ = "Pyosch"`, `__credits__ = ["Claude Code (Claude Opus 4.8)"]`

See the [Developer Guide](developer-guide/) for details.

---

**Author:** Pyosch  
**AI Assistance:** Claude Code (Claude Opus 4.8)
