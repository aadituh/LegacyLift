**Author(s):** Spencer Peloquin

# Account and Authentication
LegacyLift can require sign-in so each account only sees its own projects. Local API accounts use email/password tokens; optional Neon Auth can be configured for hosted deployments.

## Notes
* Passwords are hashed; weak passwords are rejected.
* When login is off, unowned projects remain available for local demos.

> **Placeholder:** Add security threat notes and exact env var checklist when the Lab 3 security section is drafted.
