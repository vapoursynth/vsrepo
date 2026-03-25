# Contributing to VSRepo

This guide outlines how to set up the development environment, build, and publish the package.

## Development Setup

The use of a virtual environment (`venv`) is recommended:

1.  **Create a virtual environment:**

    ```powershell
    python -m venv .venv
    ```

2.  **Activate the environment:**
    - **Windows:** `.venv\Scripts\activate`
    - **Linux/macOS:** `source .venv/bin/activate`

3.  **Install in editable mode with development dependencies:**
    ```powershell
    pip install -e .[tqdm] --group dev
    ```

## Building and Publishing

This project uses [Flit](https://flit.pypa.io/) for packaging and distribution.

- **Versioning:**
  Ensure the `__version__` string is correctly updated in `src/vsrepo/__init__.py` before building or publishing.

- **To build the package:**
  ```powershell
  flit build
  ```
- **To publish to PyPI:**
  ```powershell
  flit publish
  ```
