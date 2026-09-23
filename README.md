# RET-C2-607 — Retail CVS Personalized Product Recommendation Agent

> **Category**: Cat 2 (domain workflow)
> **Industry**: Retail

## Overview

This template answers a staff or kiosk query for a convenience-store product —
by name or by barcode — with a ranked list of products commonly bought
alongside it. A five-node inner workflow resolves the query against a product
catalog, retrieves aggregate frequently-bought-together pairing candidates,
filters them by store context (time of day, season, store cluster), applies
Japan's 28-item food-allergen labelling gate, and ranks what remains into a
top-5 result. Both the pairing signal and the allergen check operate on
aggregate, pre-approved catalog data only — the agent never ingests, stores,
or reasons over individual customer purchase history, and the pairing-KB and
output-formatting nodes actively strip any record or field shaped like an
individual identifier before it can propagate.

The agent makes no purchasing or stocking decision and issues no promotion. It
returns a ranked candidate list for a person to act on. Where a query cannot
be resolved to a catalog product, or no aggregate pairing data exists for it,
it reports that explicitly rather than returning an empty or fabricated list.
An LLM call is used once, after ranking, to produce a short non-sensitive
quality note on the response; the ranking itself is entirely deterministic and
the response is returned unchanged if that call fails or is unavailable.

This is an agent template built with the **AGENTIC STAR** development
platform and the **AgentCore Framework**. It is intended to be taken as a
starting point: fork it, adapt it to your own data and policies, and run it
inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | >=3.11 |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specifications
```

See `docs/` for the design specification and test specification.

## Customising

1. Point `PairingKbService._call_kb` at your own aggregate pairing-signal
   backend — no corpus ships with this template, and the service raises
   rather than returning a real result until one is wired.
2. Adjust `ProductResolveNode`'s catalog lookup for your own product master
   data; the bundled catalog is a small fixture used by the tests.
3. Adjust `config/config.yaml` for your own store-context tagging scheme and
   allergen policy.
4. Review the node implementations under `src/nodes/` for domain-specific
   logic, in particular the allergen fail-safe rule in `AllergenCheckNode`
   (a food product with missing allergen metadata is excluded, not passed
   through).
5. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
