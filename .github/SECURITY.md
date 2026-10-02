# Security policy

Security fixes target the current `main` branch. Older snapshots are not
maintained separately; update before investigating a suspected issue.

## Reporting a vulnerability

If GitHub's private vulnerability reporting is available for this repository,
use **Security → Advisories → Report a vulnerability**. Otherwise, contact the
maintainer through a private method listed on their
[GitHub profile](https://github.com/adhamahmedyousef). If no private channel is
available, open an issue requesting private contact without exploit details.

Include the affected version, expected and observed behavior, and a minimal
reproduction using placeholder credentials and synthetic learner records.
Never publish real API keys, private learner data or an unpatched exploit in a
public issue. There is no guaranteed response time.

## Scope and credentials

This repository contains the skill, its archive client and its local progress
store. VoidHub hosting and API operations are maintained separately. Reproduce
client issues with a mock server whenever possible; access to the public service
does not authorize load testing or exploitation.

If an API key is exposed, revoke its registered hash in the service configuration
and provision a replacement. Deleting the key from a public message or commit
does not revoke access. Keep private credentials and learner memory outside the
repository.
