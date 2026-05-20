# Security Policy

## Supported Versions

Only the latest version on the `main` branch is actively maintained.

Previous releases and historical states of the repository may not receive
security updates or patches.

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public GitHub issue**.

Instead, report it responsibly using one of the following methods:

- GitHub Security Advisories
- Direct contact with the repository maintainer via GitHub

When submitting a report, please include:

- A clear description of the vulnerability
- Steps to reproduce (if applicable)
- Affected components or functions
- Potential impact and severity

Reports will be reviewed and handled through responsible disclosure.

## Security Scope

This repository provides a Python interface for working with
TimescaleDB and PostgreSQL, including:

- Database connection handling
- Schema and hypertable management
- Data ingestion and querying utilities
- Analytical helper functions

Security considerations primarily relate to:

- SQL execution safety
- Credential handling
- Dependency vulnerabilities

## Dependency Security

- Dependencies are explicitly version-pinned
- Supported Python versions are defined in `pyproject.toml`
- Security-related updates are prioritized

## Responsible Usage

Users are responsible for:

- Secure storage of database credentials
- Proper network and database access controls
- Reviewing SQL execution contexts

This project does not manage authentication, authorization, or infrastructure security.

## Disclosure Policy

Please allow reasonable time for investigation and remediation before any public
disclosure of reported vulnerabilities.
