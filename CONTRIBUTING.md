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

Keep blueprint validation separate from host-state checks. Inventory shape,
allowed values, cross-record consistency, and impossible combinations belong
in the preflight validation. Checks that depend on the current host,
installed packages, services, files, or database state remain in the
state-specific tasks.

All role states run inventory validation before their state-specific work. The
validation-only state can be used for fast checks without applying PostgreSQL
changes:

```yaml
- role: ansible-iac-role-postgresql
  state: validate
```

## Tests

Run the validation scenario while working on blueprint validation:

```bash
molecule test -s validation
```

Run the TimescaleDB package-source scenario when changing TimescaleDB package,
repository, or preload behavior:

```bash
molecule test -s timescaledb
```

Run the default scenario after changes that affect normal installation or
configuration behavior:

```bash
molecule test -s default
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
