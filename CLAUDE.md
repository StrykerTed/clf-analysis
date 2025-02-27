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

## Project Structure
- Tools in `src/tools/` - standalone scripts
- Core utilities in `src/utils/`
- Use relative imports within the package
- Examples in `examples/` directory