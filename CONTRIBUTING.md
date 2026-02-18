# Contributing

Thank you for your interest in contributing to Timescale Access!

This project aims to provide a deterministic, reproducible, and production-ready
interface for working with TimescaleDB and PostgreSQL. Contributions should
prioritize correctness, explicit behavior, and long-term maintainability.

---

## Design Philosophy

All changes should align with the following principles:

- Deterministic execution and predictable outcomes  
- Explicit schema and state handling  
- No hidden side effects or implicit mutations  
- Reliability over convenience  
- Clear separation between read, write, and analysis layers  

Avoid introducing non-deterministic logic, magic defaults, or tightly coupled behavior.

---

## Contribution Workflow

1. Fork the repository  
2. Create a focused feature or fix branch  
3. Keep commits small and logically scoped  
4. Open a Pull Request with a clear technical description  

Describe the motivation, approach, and any relevant design considerations.

---

## Commit Conventions

Use concise, descriptive messages:

feat: add hypertable conflict handling  
fix: correct transaction rollback behavior  
docs: clarify devcontainer setup  

---

## Development Setup

Recommended environment:

- Python 3.11.x  
- VS Code Devcontainer (included)

Manual setup:

```bash
pip install -e .[dev]
```

---

## Testing Requirements

Before submitting a pull request:

* All tests must pass using `pytest`
* New functionality should include relevant test coverage

Contributions without tests may be requested to add coverage before review.
