# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-06-21

### Fixed

- Fix `ComdabInternalError` raised when generating migrations updating some
  model `extra`; `MigrationGeneratorPort.alter_*_extra` methods are now
  correctly called in these cases (fixes [#1](https://github.com/loic-simon/comdab/issues/1))
- Fix `ComdabForeignKeyConstraint.columns_mapping` not treated as an opaque
  value in comparisons (generated `.left_only` / `.right_only` paths)
- Fix `ComdabType` not exported in `comdab.models`

## [0.4.0] - 2026-05-31

### Added

- New migration generation mechanism, based on new `generate_migrations`
  and `generate_migrations_from_reports` top-level functions, and new
  `MigrationGeneratorPort` / `PartialMigrationGeneratorPort` classes

### Changed

- Bump minimal Python version to 3.13, test with Python 3.15
- Improve documentation style and API Reference page
- Bump package versions in uv.lock, other maintenance upgrades

### Fixed

- Fix `ComdabConstraint` annotations, using a new `ComdabConstraintType` alias
  for more precise tagged union typing
- Various documentation fixes

## [0.3.1] - 2026-04-07

### Added

- PostgreSQL: detect & compare procedures, in addition of regular functions

## [0.3.0] - 2025-08-12

### Added

- PostgreSQL: detect & compare enum types, even if they are unused
  (new model `ComdabCustomType`, in `ROOT.custom_types`)

## [0.2.1] - 2025-08-06

### Fixed

- Fix crash when reflecting tables without a primary key

## [0.2.0] - 2025-07-23

### Changed

- Ignore rules aimed at specific dictionary key(s) now also apply to matching keys that are only in the left
  or only in the right dictionaries, in addition to `.left_only` / `.right_only` rules

### Fixed

- PostgreSQL exclude constraints attributes and operators were sometime mixed

## [0.1.1] - 2025-06-22

- Fixed PyPI metadata and other non-code changes

## [0.1.0] - 2025-06-22

Initial version
