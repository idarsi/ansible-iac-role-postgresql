# Contributing

## Blueprint changes

Every new or changed `iac_blueprint.postgresql` field must be handled in all
of the following places:

- Add or update preflight validation in the relevant `tasks/validate/validate_*.yml`
  file.
- Add a valid inventory example when the inventory shape is user-visible.
- Add at least one validation test for an invalid value or combination.
- Update `README.md` when the inventory structure or supported state surface
  changes.

Cluster records are version-scoped and are intentionally passed unchanged to
all member hosts. The role derives the host-local Patroni member from
`inventory_hostname` and the referenced instance name. Do not duplicate or
partially rewrite the cluster definition per host.

Keep blueprint validation separate from host-state checks. Inventory shape,
allowed values, cross-record consistency, and impossible combinations belong
in the preflight validation. Checks that depend on the current host,
installed packages, services, files, or database state remain in the
state-specific tasks.

Inventory validation is intended before state-specific work; the known uninstall
cleanup bypass is an out-of-scope limitation documented in
[the evidence note](docs/maturity-evidence.md). The
validation-only state can be used for fast checks without applying PostgreSQL
changes:

```yaml
- role: ansible-iac-role-postgresql
  state: validate
```

## Tests

Use the existing approved controller and prerequisites in [TESTING.md](TESTING.md).
The runtime commands below are tester/operator checks. Developers run cheap
targeted parsing, contract/unit, syntax and diff checks unless explicitly assigned
runtime verification; they must not install or upgrade shared tooling.

Run the validation scenario while working on blueprint validation:

```bash
molecule test -s podman-validation
```

Run the TimescaleDB package-source scenario when changing TimescaleDB package,
repository, or preload behavior:

```bash
molecule test -s kvm-timescaledb
```

Run the `kvm-full` scenario after changes that affect normal installation or
configuration behavior:

```bash
molecule test -s kvm-full
```

New validation scenarios should cover both successful input and the expected
failure message for invalid input. Prefer `state: validate` so validation
tests do not require package installation or service setup.

Before submitting changes, run the relevant Molecule scenarios and a syntax
check from the role directory:

```bash
ansible-playbook --syntax-check \
  -i docs/inventory-example.yml \
  docs/playbook-example.yml
```
