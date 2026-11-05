# Biblioteca privacy changes

This fork maintains the privacy changes used by a personal library integration. Its maintained default branch is `fix/biblioteca-privacy`, based on upstream commit `abbbb1c4b9982d46c3da57d5dd25c553990519a2`. Treat this default branch as a stable integration branch, rather than an unmerged development branch.

## Changes

- Scope account cookies to the configured host. Before every request, including redirects, strip cookie and authorization headers when the host or port differs.
- Refuse non-HTTPS EAPI and download requests.
- Do not follow API redirects, so a login POST cannot silently forward credentials to another origin. HTTPS download redirects remain supported without account cookies on external hosts.
- Remove the vendored library's automatic debug file and default debug output; its stream handler emits errors on stderr.

These changes narrow credential handling; they do not establish that a third-party domain is trustworthy. Pin a verified EAPI host using `ZLIBRARY_EAPI_DOMAIN` to disable domain discovery. An API endpoint requiring redirects now fails instead of following them. A download endpoint that requires account cookies on a different host may fail and must be reviewed before adding an exception.

## Local integration boundary

No personal credentials, Keychain entries, local paths, downloaded books, or machine-specific configuration are included in this fork. A separate local launcher loads credentials from the macOS Keychain, supplies a minimal environment, pins the domain, and applies filesystem restrictions. Those deployment measures are independent of the changes in this repository.

## Validation

`__tests__/python/test_biblioteca_privacy.py` contains offline regressions for cookie isolation across initial download hosts, redirects, subdomains and ports, refusal of HTTP, refusal of login redirects, and removal of file logging. The local integration has also been tested against live metadata and three EPUB downloads; offline tests alone do not establish current upstream availability.

Do not automatically update the installed integration from this fork or upstream. Review upstream differences, preserve these guarantees, test changes, and deploy a specific reviewed commit.
