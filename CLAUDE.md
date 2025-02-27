# CLF Analysis Clean - Dev Guide

## Environment Setup & Commands
- Setup venv: `python3.11 -m venv venv && source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Install package: `python setup.py install`
- Update requirements: `pip freeze > requirements.txt`
- Run example: `python examples/example_clf.py`
- Run specific tool: `python src/tools/get_platform_paths_shapes_shapely.py`

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
- Core utilities in `src/utils/`
- Use relative imports within the package
- Examples in `examples/` directory

## Performance Optimization
- Use multiprocessing for CPU-bound tasks:
  ```python
  from multiprocessing import Pool
  
  # Use min of CPU count and number of tasks to avoid creating too many processes
  num_processes = min(os.cpu_count(), len(tasks))
  
  # Create a helper function for processing a single item
  def process_item(item):
      # Process the item
      return result
      
  # Process all items in parallel
  with Pool(processes=num_processes) as pool:
      results = pool.map(process_item, items)
  ```
- For more complex parallel tasks with multiple arguments, use `starmap`:
  ```python
  results = pool.starmap(process_item, [(arg1, arg2, ...) for item in items])
  ```