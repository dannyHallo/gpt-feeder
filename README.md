# feeder.py

A tiny zero-dependency helper that gathers source files, concatenates them,
and (optionally) copies the result to your system clipboard.  
Great for feeding large language models like GPT with multi-file projects.

- **Platforms**
  - Clipboard: Windows (`powershell Set-Clipboard`) and macOS (`pbcopy`)
  - Other OSes: content is printed only
- **Extension handlers** – plug-in style pre-processing based on file suffix  
  (comes with a `.ipynb` handler that extracts code cells)
- **Single file** – easy to drop into any repository

## Usage

```bash
python feeder.py --root <DIR> --include <PATTERN1> <PATTERN2> ...
```
