# eval-delta implementation plan

Goal: ship a usable independent command-line tool and GitHub v1.0.0 release.
Architecture: `src/eval_delta/core.py` handles analysis; `cli.py` validates arguments and formats output. `tests/test_core.py` verifies semantics and `test_cli.py` exercises process exit codes and installation. Standard library runtime, setuptools build, unittest tests, Ruff checks.

- [x] Write behavior tests and verify missing implementation fails with `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [x] Implement the core and CLI to pass those contracts.
- [x] Add synthetic examples, bilingual usage, limitations, MIT license and contribution guidance.
- [x] Run tests, lint and build wheel/source distributions; install wheel in a clean environment and run documented examples.
- [x] Review report correctness, failure paths, filesystem effects, packaging and accidental credential exposure.
- [ ] Create public repository, push verified sources, check multi-platform CI and publish v1.0.0 assets.
