# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
