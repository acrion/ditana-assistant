# Contributing to Ditana Assistant

We're thrilled that you're interested in contributing to Ditana Assistant! This document provides guidelines for contributing to the project.

## How to Contribute

There are many ways to contribute to Ditana Assistant:

1. **Reporting Bugs**: If you encounter any issues, please report them with as much detail as possible.
   If you can reproduce the bug, please enable `show_debug_messages` in `config.yaml` and provide the full output.
   Please note that Ditana Assistant uses the LLM API for its internal processes, which may lead to non-reproducible effects.
   Additionally, Ditana Assistant employs a request cache, which further complicates reproducibility:
   A previously reproducible issue may suddenly disappear due to the cache’s sophisticated strategy
   for managing the dynamic lifetime of cached requests, which depends on the persistence of the responses provided by the API.
   The cache files are located in the following directories:
   - Linux: `~/.local/share/ditana-assistant`
   - macOS: `~/Library/Application Support/ditana-assistant`
   - Windows: `C:\Users\<username>\AppData\Local\ditana-assistant`
2. **Suggesting Enhancements**: Have an idea for a new feature or an improvement? Open an issue and tag it as an enhancement. We love hearing new ideas!

3. **Writing Documentation**: Good documentation is crucial. If you see an area where our documentation could be improved or expanded, please let us know or submit a pull request with your changes.

4. **Contributing Code**: We welcome code contributions for various aspects of the project, including:
   - Bug fixes
   - Performance improvements
   - New features
   - Documentation enhancements
   
   Here’s the process for contributing code:
   - Fork the repository
   - Create a new branch for your feature or bug fix
   - Write your code, adding unit tests for new features
   - Ensure all tests pass
   - Submit a pull request with a clear description of your changes

5. **Testing**: With the wide variety of scenarios an AI assistant must handle, comprehensive testing is crucial. We particularly need:
   - More unit tests, especially those that uncover edge cases or potential issues
   - Cross-platform testing to ensure consistency across different operating systems
   - User experience testing to identify areas for improvement in the interface and interaction flow

6. **Providing Feedback**: Your experiences and observations are invaluable. Please share:
   - Feature requests: Let us know what functionalities you'd like to see added or improved.
   - Usage scenarios: Descriptions of how you use Ditana Assistant can help us optimize for real-world applications.

## Code Style

We strive to maintain a consistent and readable codebase. Please adhere to the following guidelines:

- Follow the existing code style in the project
- Use meaningful variable and function names
- Comment your code where necessary, especially for complex logic
- Use the pylint configuration provided in the `pyproject.toml` file at the root of the project. This customized configuration gives good indications of what to do and what to avoid.
- Use type hints in method and function definitions. This improves code readability and helps catch type-related errors early.

Example of a properly documented and type-hinted function:

```python
def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two integers.

    Args:
        a (int): The first integer.
        b (int): The second integer.

    Returns:
        int: The sum of a and b.
    """
    return a + b
```

## Commit Messages

Write clear, concise commit messages. Start with a short summary (50 characters or less), followed by a blank line and a more detailed explanation if necessary.

## Pull Requests

- Create a new branch for each feature or bug fix
- Keep pull requests focused on a single change
- Include a description of what your change does and why it’s needed
- Update documentation if your changes require it
- Ensure your code adheres to the style guidelines mentioned above

## Questions?

If you have any questions about contributing, feel free to open an issue or reach out to the maintainers.

Thank you for your interest in improving Ditana Assistant!