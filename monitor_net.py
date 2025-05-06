import time
import os
import subprocess
import re
import plotext as pltx # For plotting in the terminal
import sys
import argparse
import termios # POSIX-specific module for terminal I/O control

# --- Configuration Constants ---
MAX_DATA_POINTS = 200       # Max data points on the graph before old ones are removed
CONSECUTIVE_FAILURES_ALERT_THRESHOLD = 3 # Ping failures to trigger a "connection lost" alert
STATUS_MESSAGE_RESERVED_LINES = 3    # Lines reserved at the top for status messages

# --- Global Configuration Variables (defaults, can be overridden by command-line arguments) ---
DEFAULT_HOST = '8.8.8.8'
DEFAULT_PING_INTERVAL_SECONDS = 3.0
DEFAULT_GRAPH_Y_MAX = 200.0   # Default reference maximum Y-axis value for the graph (ms)
DEFAULT_Y_TICKS = 6           # Desired number of Y-axis ticks (e.g., 6 ticks = 5 intervals)

# --- Global State Variables ---
latency_plot_values = []          # Y-values for the main graph line (0 for failures)
latency_history_real_values = []  # History of actual latency values (includes None for failures)
consecutive_ping_failures = 0
connection_status_message = ""
total_monitoring_time_seconds = 0

def measure_latency(host_to_ping: str) -> float | None:
    """
    Measures latency to a specific host using the Linux 'ping' command.
    Returns latency in milliseconds (ms) or None if ping fails or output cannot be parsed.
    """
    # Ping timeout (-W) is in seconds. Ensure it's at least 1 second.
    ping_timeout_seconds = str(max(1, int(DEFAULT_PING_INTERVAL_SECONDS)))
    # subprocess.run timeout should be slightly larger than the ping command's timeout.
    subprocess_timeout = max(2.0, DEFAULT_PING_INTERVAL_SECONDS + 1.0)

    try:
        # Linux specific ping command:
        # -c 1: Send only one packet
        # -W <timeout>: Wait <timeout> seconds for a response
        command = ['ping', '-c', '1', '-W', ping_timeout_seconds, host_to_ping]
        
        proc = subprocess.run(command, capture_output=True, text=True, timeout=subprocess_timeout, check=False)
        
        if proc.returncode == 0: # Ping successful
            output = proc.stdout
            match = re.search(r"time=([0-9\.]+)\s*ms", output, re.IGNORECASE) # Standard Linux ping output
            if match:
                return float(match.group(1))
            return None # Successful response but no time found (unlikely for Linux ping)
        else:
            return None # Ping failed (e.g. host unknown, network unreachable, or -W timeout)
    except subprocess.TimeoutExpired: # subprocess.run() itself timed out
        return None
    except FileNotFoundError:
        # This critical error will be caught by the main loop's exception handler
        sys.stdout.write(f"CRITICAL ERROR: 'ping' command not found. Please ensure it is installed and in your PATH.\n")
        raise
    except Exception: # Other unexpected errors during ping execution
        return None

def update_display_and_status():
    """Repositions cursor to top, and redraws the graph and status information."""
    global connection_status_message, latency_plot_values, latency_history_real_values, consecutive_ping_failures
    global total_monitoring_time_seconds, DEFAULT_HOST, DEFAULT_PING_INTERVAL_SECONDS, DEFAULT_GRAPH_Y_MAX, DEFAULT_Y_TICKS

    sys.stdout.write("\033[H") # ANSI escape code: Move cursor to Home (top-left)

    # Print status message, occupying a fixed number of lines for stable layout
    status_lines_printed = 0
    if connection_status_message:
        message_to_display = [connection_status_message]
        if connection_status_message.startswith("!!!") or connection_status_message.startswith("INFO:"):
            message_to_display.append("-" * len(connection_status_message))
        
        for line in message_to_display:
            if status_lines_printed < STATUS_MESSAGE_RESERVED_LINES:
                sys.stdout.write(line + "\n")
                status_lines_printed += 1
            else:
                break 
    
    for _ in range(STATUS_MESSAGE_RESERVED_LINES - status_lines_printed):
        sys.stdout.write("\n") # Fill remaining reserved lines
    
    sys.stdout.write("\n") # Blank line between status area and graph/message
    
    x_axis_plot_indices = list(range(len(latency_plot_values)))

    if not latency_plot_values: 
        sys.stdout.write("Waiting for first ping data...\n")
    else:
        pltx.clt() # Clear plotext terminal (canvas settings)
        pltx.cld() # Clear previous plotext plot data
        try:
            terminal_cols, terminal_lines = os.get_terminal_size()
            # Estimate overhead lines for status, graph title/axes, stats, etc.
            # Adjust '15' based on observed layout needs.
            overhead_lines = STATUS_MESSAGE_RESERVED_LINES + 15 
            plot_height = max(5, terminal_lines - overhead_lines) 
            plot_width = max(20, terminal_cols - 2)    

            if plot_height < 5 or plot_width < 20: # If calculated plot area is too small
                 sys.stdout.write(f"WARNING: Calculated plot area is too small (w:{plot_width}, h:{plot_height}). Graph might not display well.\n")
            
            pltx.plot_size(plot_width, plot_height)
            pltx.title("Real-time Internet Latency")
            pltx.ylabel("(ms)")
            
            # Set Y-axis limits: 0 to a calculated upper bound
            max_y_data_current = 0
            if latency_plot_values: # Check if there are plot values
                valid_latencies = [l for l in latency_plot_values if l is not None and l > 0] 
                if valid_latencies:
                    max_y_data_current = max(valid_latencies)
            
            # Y-axis upper limit is the greater of the configured max or current max data (plus some padding)
            y_lim_upper = max(DEFAULT_GRAPH_Y_MAX, max_y_data_current * 1.1 if max_y_data_current > 0 else DEFAULT_GRAPH_Y_MAX)
            if y_lim_upper < 10: y_lim_upper = 10 # Ensure a minimum sensible Y range
            pltx.ylim(0, y_lim_upper)

            # Attempt to set a specific number of Y-ticks
            if DEFAULT_Y_TICKS > 1:
                try:
                    pltx.yticks(DEFAULT_Y_TICKS)
                except TypeError: 
                    # Fallback: if yticks(int) causes TypeError, calculate a list of ticks
                    if y_lim_upper > 0:
                        step = y_lim_upper / (DEFAULT_Y_TICKS - 1)
                        ticks_list = sorted(list(set([round(i * step) for i in range(DEFAULT_Y_TICKS)])))
                        if ticks_list: pltx.yticks(ticks_list)
                    elif DEFAULT_Y_TICKS > 1 : # y_lim_upper is 0
                         pltx.yticks([0,1]) 
                except Exception as e_ytick: # Other potential errors with yticks
                    sys.stdout.write(f"WARNING: Could not set custom y-axis ticks: {e_ytick}\n")

            pltx.canvas_color("black")
            pltx.axes_color("gray")
            pltx.ticks_color("dark_gray")
            
            # Plot main latency line (where 0 indicates a failure for scaling purposes)
            pltx.plot(x_axis_plot_indices, latency_plot_values, marker="braille", color="cyan")

            # Identify and plot 'X' markers for actual failures (where history shows None)
            x_failure_indices = []
            y_base_for_failure_marker = 0 
            for i, real_latency in enumerate(latency_history_real_values): 
                if real_latency is None: 
                    if i < len(x_axis_plot_indices): 
                        x_failure_indices.append(x_axis_plot_indices[i])
            
            if x_failure_indices:
                y_values_for_failures = [y_base_for_failure_marker] * len(x_failure_indices)
                pltx.scatter(x_failure_indices, y_values_for_failures, marker="x", color="red")
            
            # If no data was plotted at all, draw an empty frame to show title/axes
            if not latency_plot_values or all(l == 0 for l in latency_plot_values): 
                if not x_failure_indices: 
                     pltx.plot([], []) 

            pltx.xticks([], []) # Hide X-axis numeric ticks and labels
            pltx.xlabel("(Press Ctrl+C to Exit)")
            pltx.show() # Display the constructed plot
        except Exception as e_plot:
            # Clear potentially garbled plot area on error
            sys.stdout.write("\033[J") 
            sys.stdout.write(f"ERROR during plotext rendering: {e_plot}\n")

    # --- Statistics Section ---
    stats_lines = [
        "\n--- Statistics ---",
        f"Monitoring Host: {DEFAULT_HOST}",
        f"Ping Interval: {DEFAULT_PING_INTERVAL_SECONDS:.1f}s",
        f"Graph Y-Max Ref: {DEFAULT_GRAPH_Y_MAX:.0f}ms" # Display configured Y-max reference
    ]
    if latency_history_real_values:
        last_real_ping_value = latency_history_real_values[-1]
        if last_real_ping_value is not None:
            stats_lines.append(f"Current Latency: {last_real_ping_value:.2f} ms")
        else:
            stats_lines.append("Current Latency: PING FAILED")

        valid_latencies_for_stats = [l for l in latency_history_real_values if l is not None]
        if valid_latencies_for_stats:
            stats_lines.append(f"Average (valid pings): {sum(valid_latencies_for_stats) / len(valid_latencies_for_stats):.2f} ms")
            stats_lines.append(f"Minimum (valid pings): {min(valid_latencies_for_stats):.2f} ms")
            stats_lines.append(f"Maximum (valid pings): {max(valid_latencies_for_stats):.2f} ms")
        else: # If all pings in history were failures
            stats_lines.append("Average (valid pings): N/A")
            stats_lines.append("Minimum (valid pings): N/A")
            stats_lines.append("Maximum (valid pings): N/A")
    
    # Format and add total monitoring time
    hours = int(total_monitoring_time_seconds // 3600)
    minutes = int((total_monitoring_time_seconds % 3600) // 60)
    seconds = int(total_monitoring_time_seconds % 60)
    time_fmt = ""
    if hours > 0: time_fmt += f"{hours}h "
    if minutes > 0 or hours > 0: time_fmt += f"{minutes}m "
    time_fmt += f"{seconds}s"
    stats_lines.append(f"Monitoring Time: {time_fmt.strip()}")
    
    stats_lines.append(f"Consecutive Failures: {consecutive_ping_failures}")
    stats_lines.append("--------------------")
    sys.stdout.write("\n".join(stats_lines) + "\n")

    sys.stdout.write("\033[J") # ANSI: Clear from current cursor to end of screen
    sys.stdout.flush()

def main():
    """Parses arguments, and runs the main monitoring loop."""
    # Declare globals that will be modified in this function
    global DEFAULT_HOST, DEFAULT_PING_INTERVAL_SECONDS, DEFAULT_GRAPH_Y_MAX, DEFAULT_Y_TICKS
    # These state variables are modified within the main loop inside this function
    global latency_plot_values, latency_history_real_values, consecutive_ping_failures
    global connection_status_message, total_monitoring_time_seconds

    parser = argparse.ArgumentParser(
        description="Monitors internet latency to a specified host and displays a real-time graph (Linux only).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows default values in help output
    )
    parser.add_argument(
        'host',
        type=str,
        nargs='?', # Makes host argument optional
        default=DEFAULT_HOST, 
        help='The host or IP address to ping.'
    )
    parser.add_argument(
        '-i', '--interval',
        type=float,
        default=DEFAULT_PING_INTERVAL_SECONDS, 
        help='Interval between pings in seconds (e.g., 0.5, 1, 10).'
    )
    parser.add_argument(
        '--ymax',
        type=float,
        default=DEFAULT_GRAPH_Y_MAX, 
        help='Reference maximum value for the graph Y-axis (in ms).'
    )
    parser.add_argument(
        '--yticks',
        type=int,
        default=DEFAULT_Y_TICKS, 
        help='Desired approximate number of Y-axis ticks.'
    )
    args = parser.parse_args()

    # Update global configuration variables with parsed arguments
    DEFAULT_HOST = args.host
    DEFAULT_PING_INTERVAL_SECONDS = args.interval
    DEFAULT_GRAPH_Y_MAX = args.ymax
    DEFAULT_Y_TICKS = args.yticks

    # Validate arguments
    if DEFAULT_PING_INTERVAL_SECONDS <= 0:
        print(f"Error: Ping interval ({DEFAULT_PING_INTERVAL_SECONDS}s) must be greater than zero.")
        sys.exit(1)
    if DEFAULT_GRAPH_Y_MAX <= 0:
        print(f"Error: Graph Y-max ({DEFAULT_GRAPH_Y_MAX}ms) must be greater than zero.")
        sys.exit(1)
    if DEFAULT_Y_TICKS < 2: # Need at least 2 ticks for a range (e.g., min and max)
        print(f"Error: Number of Y-axis ticks ({DEFAULT_Y_TICKS}) must be at least 2.")
        sys.exit(1)

    sys.stdout.write("\033[?25l") # ANSI: Hide cursor
    sys.stdout.flush()
    original_terminal_settings = None
    # Save terminal settings on POSIX systems (Linux) to restore them on exit
    try:
        original_terminal_settings = termios.tcgetattr(sys.stdin.fileno())
    except Exception: # pylint: disable=broad-except
        # This can happen if not run in a real terminal (e.g., output piped to a file)
        pass 

    try:
        while True:
            current_latency_real = measure_latency(DEFAULT_HOST) # Can be None if ping fails
            total_monitoring_time_seconds += DEFAULT_PING_INTERVAL_SECONDS

            # Update connection status message and failure counter
            if current_latency_real is None: 
                consecutive_ping_failures += 1
                if consecutive_ping_failures >= CONSECUTIVE_FAILURES_ALERT_THRESHOLD and \
                   not connection_status_message.startswith("!!!"): # Avoid re-printing alert
                    connection_status_message = f"!!! ALERT: Connection to {DEFAULT_HOST} LOST ({consecutive_ping_failures} failures) !!!"
                elif 0 < consecutive_ping_failures < CONSECUTIVE_FAILURES_ALERT_THRESHOLD and \
                     not connection_status_message.startswith("!!!"): # Softer warning for initial failures
                     connection_status_message = f"Warning: Ping to {DEFAULT_HOST} failed ({consecutive_ping_failures}x)"
            else: # Ping successful
                if consecutive_ping_failures >= CONSECUTIVE_FAILURES_ALERT_THRESHOLD: # If was in alert state
                    connection_status_message = f"INFO: Connection to {DEFAULT_HOST} RESTORED after {consecutive_ping_failures} failure(s)!"
                elif consecutive_ping_failures > 0: # If there were some failures before recovery
                    connection_status_message = f"INFO: Ping to {DEFAULT_HOST} normalized after {consecutive_ping_failures} failure(s)."
                elif connection_status_message.startswith("INFO:"): # Clear "INFO" message after one display cycle
                    connection_status_message = "" 
                consecutive_ping_failures = 0
            
            # Update data lists for plotting and history
            if len(latency_history_real_values) >= MAX_DATA_POINTS:
                latency_history_real_values.pop(0)
            latency_history_real_values.append(current_latency_real)

            if len(latency_plot_values) >= MAX_DATA_POINTS:
                latency_plot_values.pop(0)
            # For the plot line, use 0 for failures to help plotext auto-scale Y-axis to include 0
            latency_plot_values.append(current_latency_real if current_latency_real is not None else 0)
            
            update_display_and_status() # Redraw the screen
            time.sleep(DEFAULT_PING_INTERVAL_SECONDS)

    except KeyboardInterrupt: # User pressed Ctrl+C
        print("\nMonitoring stopped by user.")
    except Exception as e: # Catch other unexpected errors
        print(f"\nAn unexpected or critical error occurred: {e}")
        # Avoid duplicate FileNotFoundError message if already printed by measure_latency
        if not isinstance(e, FileNotFoundError):
            import traceback
            traceback.print_exc()
    finally:
        sys.stdout.write("\033[?25h") # ANSI: Restore cursor
        sys.stdout.flush()
        # Restore terminal settings on POSIX systems if they were saved
        if original_terminal_settings: 
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_terminal_settings)
            except Exception: # pylint: disable=broad-except
                pass
        
        # Determine exit code
        exit_code = 0
        current_exception = sys.exc_info()[1] 
        if isinstance(current_exception, KeyboardInterrupt):
            pass # Normal exit (0) on Ctrl+C if handled gracefully
        elif current_exception is not None: # Any other unhandled exception that reached finally
            exit_code = 1
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
