# feeder.py

Concatenate multiple source files into a single text blob and (optionally)
copy it to your clipboard.  
Perfect for pasting entire projects into ChatGPT or similar tools.

- **Clipboard support**: Windows (`powershell Set-Clipboard`) and macOS (`pbcopy`)
- **Extension handlers**: pre-process files by suffix (comes with a Jupyter
  `.ipynb` handler that extracts code cells)
- **Zero dependencies**: pure standard-library Python, single script

## Usage

```bash
python feeder.py --root <DIR> [--ignore <PATTERN> ...] [--no-clipboard]
```

## Examples

### Ignore temporary and compiled files

```shell
python feeder.py --root ./project --ignore *.tmp *.pyc
```

### Just print; do not touch the clipboard

```shell
python feeder.py --root ./project --no-clipboard
```
