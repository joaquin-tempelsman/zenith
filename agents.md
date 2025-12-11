# AI Agent Instructions

## General Guidelines

### 1. Documentation Files
- **DO NOT** write `.md` files with summaries of work done unless explicitly instructed by the user
- Keep responses concise and focused on the task at hand

### 2. Output File Locations
- All test files must be located in `/chat_outs/tests` folder
- All `.md` files (when requested) must be located in `/chat_outs/refs` folder

### 3. Testing Requirements
- After finishing adding a new feature, **always validate that all tests pass**
- Run the full test suite to ensure no regressions were introduced
- Fix any failing tests before considering the work complete

### 4. Code Quality - Docstrings
- After finishing code work, **validate that all functions have updated docstrings**
- Ensure docstrings match all function arguments (parameters)
- Verify that:
  - All parameters are documented
  - Return types are documented
  - Exceptions/errors are documented if applicable
  - Docstrings follow the project's style guide (Google/NumPy/Sphinx format)

### 5. Code Simplicity - Input Validation
- **DO NOT** add unnecessary if/else structures to validate function inputs
- Avoid defensive programming patterns unless explicitly required
- Trust that callers will provide correct inputs
- Let Python's natural error handling catch issues (e.g., TypeErrors, AttributeErrors)
- Only add input validation when:
  - It's a public API boundary
  - Invalid inputs could cause data corruption or security issues
  - The user explicitly requests it

### 6. code execution and environments
- When installing and running code use UV generated environment and UV as a package manager and package handler.
- do not use pip.

## Workflow Checklist

When completing a feature or code change:

- [ ] Implement the requested functionality
- [ ] Update/add docstrings for all modified/new functions
- [ ] Verify docstrings match function signatures
- [ ] Avoid unnecessary input validation checks
- [ ] Run all tests and ensure they pass
- [ ] Place any test files in `/chat_outs`
- [ ] Only create summary `.md` files if explicitly requested
- [ ] Place any requested `.md` files in `/chat_outs`
