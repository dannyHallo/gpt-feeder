# feeder.py

Concatenate multiple source files into one text blob and (optionally) copy
it straight to your clipboard — perfect for pasting entire projects into
ChatGPT or similar tools.

* **Clipboard support**  
  * Windows → `powershell Set-Clipboard`  
  * macOS  → `pbcopy`
* **Extension handlers**  
  Built-in `.ipynb` handler extracts code cells; you can register your own
  via a tiny decorator.
* **Filters**  
  * `--ignore`  ➜ negative filter (“never include”)  
  * `--match`   ➜ positive filter (“only include if”) – new!
* **Zero dependencies** – pure standard-library Python, single file.

## Usage

```bash
python feeder.py \
  --root <DIR> \
  [--match <PATTERN> ...]  \
  [--ignore <PATTERN> ...] \
  [--no-clipboard]
