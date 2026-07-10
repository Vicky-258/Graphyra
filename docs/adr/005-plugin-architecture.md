# ADR 005: Decoupled Plugin Registry Architecture

## Status
Accepted

## Context
Orchestrating crawl jobs required Graphyra Core to import and load domain-specific adapter modules directly (e.g. `import graphyra_adapter_genshin`). This created a circular import chain and violated domain agnosticism.

## Decision
Introduce a global `PluginRegistry` (`graphyra/plugins/registry.py`) that acts as a Strategy/Registry container. Core components and JobManager check this registry for registered adapters, ranking strategies, and expansion policies. Sibling packages (or wrappers) load and register adapters at runtime.

## Consequences
- Core has no compile-time dependencies on adapters.
- Runtime loader fallbacks are implemented to preserve backward compatibility for standalone wrappers.
- Strategy pattern enables clean framework extensions.
