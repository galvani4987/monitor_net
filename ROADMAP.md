# Improvement Roadmap for the Real-time Network Latency Monitor

This document outlines the implementation plan for the suggested improvements to the `monitor_net` project. Each section represents an area of improvement with its respective steps.

## Phase 1: Foundations and Style

### 1.1. Code Style Consistency
* **Objective:** Ensure clean, readable, and standardized code.
* **Tools:** `flake8` for linting, `black` for formatting.
* **Steps:**
    * [ ] Install `flake8` and `black` in the development environment (`pip install flake8 black`).
    * [ ] Run `flake8 monitor_net.py` and fix all reported warnings and errors.
    * [ ] Run `black monitor_net.py` to format the code automatically.
    * [ ] Add a configuration file for `flake8` (e.g., `.flake8`) if customizations are needed.
    * [ ] Consider adding a pre-commit hook (e.g., with `pre-commit`) to automate style checking before each commit.

### 1.2. Constants for ANSI Codes and "Magic Numbers"
* **Objective:** Improve readability and maintainability by replacing hardcoded values with named constants.
* **Main File:** `monitor_net.py`
* **Steps:**
    * [ ] Identify all ANSI escape codes (e.g., `\033[H`, `\033[J`, `\033[?25l`, `\033[?25h`) in `monitor_net.py`.
    * [ ] Define named constants for each ANSI code at the beginning of the script (e.g., `ANSI_CURSOR_HOME = "\033[H"`).
    * [ ] Identify "magic numbers" (e.g., `15` for `overhead_lines`, `MAX_DATA_POINTS = 200`, `CONSECUTIVE_FAILURES_ALERT_THRESHOLD = 3`, `STATUS_MESSAGE_RESERVED_LINES = 3`). Some are already constants; check if all relevant ones are covered.
    * [ ] Replace all occurrences of hardcoded values with the defined constants.

## Phase 2: Major Refactoring

### 2.1. Encapsulation with Classes
* **Objective:** Improve code organization, reduce the use of global variables, and facilitate future testing and extensions.
* **Main File:** `monitor_net.py`
* **Steps:**
    * [ ] Define a new class, for example, `NetworkMonitor`, in `monitor_net.py`.
    * [ ] Move global state variables (e.g., `latency_plot_values`, `latency_history_real_values`, `consecutive_ping_failures`, `connection_status_message`, `total_monitoring_time_seconds`) to become instance attributes of the class (initialized in `__init__`).
    * [ ] Move default configuration variables (e.g., `DEFAULT_HOST`, `DEFAULT_PING_INTERVAL_SECONDS`) to become class or instance attributes, as appropriate. CLI arguments can update instance attributes.
    * [ ] Convert main functions (`measure_latency`, `update_display_and_status`, and the `while True` loop logic within `main`) into methods of the `NetworkMonitor` class.
    * [ ] The class's `__init__` method can receive parsed CLI arguments to configure the instance.
    * [ ] The original `main` function will be simplified to:
        * Parse CLI arguments.
        * Instantiate `NetworkMonitor` with these arguments.
        * Call a main method of the instance (e.g., `monitor.run()`) that contains the monitoring loop.
    * [ ] Ensure that `KeyboardInterrupt` handling and cursor/terminal restoration (`termios`) are managed correctly within the class or by the `run` method.

### 2.2. Refactoring Long Functions
* **Objective:** Increase clarity and modularity of the `update_display_and_status` function (which will become a class method).
* **Target Method:** `NetworkMonitor.update_display_and_status` (after refactoring 2.1).
* **Steps:**
    * [ ] Analyze the `update_display_and_status` method and identify distinct logical blocks.
    * [ ] For each block, create a new private method (prefixed with an underscore) within the `NetworkMonitor` class. Suggestions:
        * `_display_status_message(self)`
        * `_prepare_plot_area(self)` (to get terminal size, calculate `plot_height`, `plot_width`)
        * `_configure_plot_axes_and_labels(self)`
        * `_plot_latency_series(self)` (for `pltx.plot` and `pltx.scatter`)
        * `_render_plot(self)` (for `pltx.show()`)
        * `_display_statistics(self)`
    * [ ] The original `update_display_and_status` method will call these new private methods in sequence.

## Phase 3: Features and Robustness

### 3.1. Enhanced Error Handling and Logging
* **Objective:** Implement a more flexible and structured logging system.
* **Main File:** `monitor_net.py`
* **Steps:**
    * [ ] Import Python's `logging` module.
    * [ ] Configure a basic logger at the beginning of the script or in the `NetworkMonitor` class's `__init__` (e.g., `logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')`).
    * [ ] Replace `print()` and `sys.stdout.write()` calls used for status messages, warnings, and errors with logger calls (e.g., `logger.info()`, `logger.warning()`, `logger.error()`, `logger.critical()`, `logger.debug()`).
    * [ ] Review the `FileNotFoundError` exception handling for the `ping` command to ensure the message is clear and logged appropriately via the logger, avoiding duplication.

### 3.2. Clarity in Failure Plotting Logic (Review)
* **Objective:** Ensure that the logic for representing failures on the graph is clear and well-documented.
* **Main File:** `monitor_net.py`
* **Steps:**
    * [ ] Review and add detailed comments explaining why `latency_plot_values` uses `0` for failures and `latency_history_real_values` uses `None`, and how both are used in plotting.
    * [ ] (Optional) Consider if a unified data structure for each history point (e.g., a `collections.namedtuple` or a small `DataPoint` class with attributes like `real_value` and `plot_value`) would simplify logic or improve readability. If there's no clear benefit, maintain the current structure with good comments.

### 3.3. Review of Docstrings and Comments
* **Objective:** Ensure all code is well-documented.
* **Main File:** `monitor_net.py`
* **Steps:**
    * [ ] Go through all classes and methods/functions.
    * [ ] Write or update docstrings for each, explaining its purpose, arguments (types and description), what it returns, and any exceptions it might raise. Use a standard format (e.g., reStructuredText or Google style).
    * [ ] Add/review inline comments for complex code sections or non-obvious logic.

## Phase 4: Testing and Maintenance

### 4.1. Implementation of Automated Tests
* **Objective:** Create a test suite to ensure code correctness and facilitate future refactorings.
* **Tools:** `unittest` (standard) or `pytest`.
* **Steps:**
    * [ ] Choose a testing framework (`pytest` is generally recommended for its simplicity).
    * [ ] Create a test directory (e.g., `tests/`).
    * [ ] Set up the environment to run tests.
    * [ ] Write unit tests for:
        * The `ping` output parsing method (within `measure_latency`), covering different valid output formats, failure cases, and timeouts. (This may require mocking `subprocess.run`).
        * Functions/methods that perform statistical calculations.
        * CLI argument validation.
        * (If a class is implemented) Test class initialization and the logic of its main methods.
    * [ ] Consider simple integration tests that simulate running the monitor for a few cycles (can be more complex).
    * [ ] Integrate test execution into a script or Makefile.

### 4.2. Improvements to `run_monitor.sh` Script (Minor)
* **Objective:** Small adjustments for robustness.
* **Main File:** `run_monitor.sh`
* **Steps:**
    * [ ] (Optional) Add a check if the `REQUIREMENTS_FILE` (`requirements.txt`) is empty before calling `pip install -r`. If empty, perhaps skip the installation step or issue a message. `pip` usually handles this well, so it's low priority.

## Additional Considerations
* **Version Control:** Use Git and make small, descriptive commits for each step or logical group of changes.
* **Branches:** Consider using feature branches for major improvements (e.g., refactoring to a class, implementing tests).
* **Code Review:** If possible, have someone else review the changes.

This roadmap is a suggestion and can be adjusted as needed. It is recommended to first focus on improvements that will have the greatest impact on code organization and maintainability.
