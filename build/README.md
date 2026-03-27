# build/

PyInstaller configuration for creating a standalone executable.

Build from the project root:

```bash
pip install pyinstaller
pyinstaller build/main.spec
```

The bundled application lands in `dist/BodyLocaliser/`. Copy the entire folder to the target machine -- no Python installation required on that machine.
