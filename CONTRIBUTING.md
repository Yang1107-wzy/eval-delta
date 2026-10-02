# Contributing

Small, reproducible improvements are welcome. Open an issue with synthetic input, expected behavior and the actual result. Never post real credentials or private datasets.

```sh
python -m pip install -e .
python -m pip install ruff build
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python -m build
```

Add a regression test for behavior changes. Keep the runtime dependency-free and support Python 3.10+. Test failures, CLI exit codes and output-file protection as well as successful inputs. Keep the English and Chinese READMEs consistent. Please keep patches focused; discuss larger features first.
