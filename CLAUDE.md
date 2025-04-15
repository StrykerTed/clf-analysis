# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup & Commands
- Setup venv: `python3.11 -m venv venv && source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Install package: `python setup.py install`
- Run tool: `python src/tools/get_platform_paths_shapes_shapely.py`
- Run example: `python examples/example_clf.py`
- Run tests: `python -m unittest discover src/tools/tests`

## Code Style
- Imports: Standard library first, then third-party, then local modules
- Module-level logger: `logger = logging.getLogger(__name__)`
- Error handling: Use try/except with specific exceptions, log errors
- Naming: snake_case for functions/variables, CamelCase for classes
- Function docstrings: Use triple quotes with description and params
- Avoid print statements in modules; use logging instead
- Type hints encouraged but not required
- Always convert numpy booleans to Python booleans before JSON serialization:
  ```python
  # Convert numpy bool to Python bool if needed
  if hasattr(value, 'item'):
      value = value.item()
  ```

## Project Structure
- Tools in `src/tools/` - standalone scripts
- Core utilities in `src/utils/` with submodules:
  - `myfuncs/` - General utility functions
  - `platform_analysis/` - Analysis modules for platforms
  - `pyarcam/` - CLF and Arcam EBM machine data handling
- Examples in `examples/` - Sample usage scripts

## Performance Optimization
- Use multiprocessing for CPU-bound tasks:
  ```python
  from multiprocessing import Pool
  
  num_processes = min(os.cpu_count(), len(tasks))
  
  with Pool(processes=num_processes) as pool:
      results = pool.map(process_item, items)
  # For multiple arguments: 
  # results = pool.starmap(process_item, [(arg1, arg2) for item in items])
  ```