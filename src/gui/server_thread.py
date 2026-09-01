# SAPÉ f-MCP — controlled file system access with granular permissions for LLMs
# Copyright (C) 2026 Luciano Arrezze
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-only

"""Background thread for running MCP server with graceful cancellation."""

from PyQt6.QtCore import QThread, pyqtSignal
import logging
import anyio
import sys
import threading
import socket
import errno

logger = logging.getLogger(__name__)

# Default port for MCP server
DEFAULT_PORT = 8089


class ServerThread(QThread):
    """QThread to run MCP server with graceful cancellation.

    Uses anyio.CancelScope for clean shutdown that properly closes resources
    (like SQLite connections) instead of killing the thread mid-instruction.

    The stop() method signals cancellation via a thread-safe Event that the
    async server monitors, allowing graceful shutdown from any thread.
    """

    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)
    port_changed = pyqtSignal(int)  # Emitted when actual port differs from requested
    tool_executed = pyqtSignal(str, dict, str, str)  # tool_name, params, result, error

    def __init__(self, server, transport="streamable-http", host="127.0.0.1", port=DEFAULT_PORT):
        super().__init__()
        self.server = server
        self.transport = transport
        self.host = host
        self.port = port
        self.shutdown_event = threading.Event()  # Thread-safe shutdown signal
        self.cancel_scope = None

        # Register tool execution callback with the server
        if hasattr(self.server, 'set_tool_executed_callback'):
            self.server.set_tool_executed_callback(self._on_tool_executed)

    def _on_tool_executed(self, tool_name: str, params: dict, result: str = None, error: str = None):
        """Called by FileMCPServer when a tool is executed.

        Emits the tool_executed signal so SessionLogPage can log the call.
        """
        self.tool_executed.emit(tool_name, params, result or "", error or "")

    def _is_port_available(self, host, port):
        """Check if a port is available for binding.

        Returns True if the port can be bound, False if already in use.
        This is a best-effort check; the actual bind can still fail (TOCTOU race).
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Don't set SO_REUSEADDR on Windows — it creates a false positive
                s.bind((host, port))
                return True
        except OSError:
            return False

    def _find_available_port(self, start_port=DEFAULT_PORT, max_attempts=10):
        """Find an available port starting from start_port.

        Tries ports from start_port to start_port+max_attempts-1.
        Returns the first available port, or None if all are in use.

        Args:
            start_port: Starting port number (default: 8089)
            max_attempts: Number of ports to try (default: 10, so 8089-8098)

        Returns:
            int: Available port number, or None if none found
        """
        for port in range(start_port, start_port + max_attempts):
            if self._is_port_available(self.host, port):
                logger.info(f"Port {port} is available")
                return port
        logger.warning(f"No available ports in range {start_port}-{start_port + max_attempts - 1}")
        return None

    async def run_server_async(self):
        """Async wrapper to run the server with a cancellable scope.

        This is called inside anyio.run(). The CancelScope can be cancelled
        by the stop() method via the shutdown_event.

        We monitor the shutdown event in a background task that cancels the
        scope when signaled, allowing graceful shutdown from other threads.
        """
        async def monitor_shutdown():
            """Background task that monitors the shutdown event."""
            while not self.shutdown_event.is_set():
                await anyio.sleep(0.1)
            # Signal cancellation when shutdown is requested
            if self.cancel_scope:
                self.cancel_scope.cancel()

        # Create cancellation scope in async context
        self.cancel_scope = anyio.CancelScope()

        with self.cancel_scope:
            # Run server and shutdown monitor concurrently
            async with anyio.create_task_group() as tg:
                mcp_server = self.server.server

                # Emit started signal immediately (before server starts listening)
                # This ensures UI state is updated as soon as the server task begins
                self.started.emit()

                # Start shutdown monitor
                tg.start_soon(monitor_shutdown)

                # Run the server
                if self.transport == "streamable-http":
                    await mcp_server.run_streamable_http_async(
                        host=self.host,
                        port=self.port
                    )
                elif self.transport == "sse":
                    await mcp_server.run_sse_async(
                        host=self.host,
                        port=self.port
                    )
                else:  # stdio (CLI mode)
                    await mcp_server.run_stdio_async()

    def run(self):
        """Run the MCP server in an anyio event loop.

        This is called by QThread.start(). We run the async server inside
        anyio.run() so we have control over the CancelScope.

        First tries to use the requested port, then auto-falls back to an available
        port from the range 8089-8098 if needed.
        """
        try:
            # Try to find an available port starting from the requested one
            available_port = self._find_available_port(self.port, max_attempts=10)

            if available_port is None:
                error_msg = (
                    f"No available ports in range {self.port}-{self.port + 9}. "
                    f"Too many instances running?"
                )
                logger.error(error_msg)
                self.error.emit(error_msg)
                # Don't emit finished here; the finally block will handle it
                return

            # Use the available port (may differ from requested port)
            original_port = self.port
            self.port = available_port

            # Notify UI of the actual port being used (if different from requested)
            if self.port != original_port:
                logger.info(f"Port {original_port} busy, using port {self.port} instead")
                self.port_changed.emit(self.port)
            else:
                logger.info(f"Port {self.port} available, using it")

            logger.info(f"MCP server starting on {self.host}:{self.port} ({self.transport})...")

            # Run the async server handler
            anyio.run(self.run_server_async)

        except OSError as e:
            # Handle port binding errors (TOCTOU race or unexpected OS errors)
            # errno 10048 on Windows is WSAEADDRINUSE; Python maps it to EADDRINUSE
            port_conflict = getattr(e, 'errno', None) in (errno.EADDRINUSE, 10048)
            if port_conflict:
                error_msg = (
                    f"Port {self.port} is already in use (Claude Desktop running?). "
                    f"Stop other instances and try again."
                )
            else:
                error_msg = f"Failed to start server: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.error.emit(str(e))
        finally:
            logger.info("MCP server stopped")
            self.finished.emit()

    def stop(self):
        """Stop the server gracefully using a shutdown event.

        Sets an event that the server monitors, allowing graceful shutdown
        without force-terminating the thread. Only calls terminate() if the
        graceful shutdown times out.

        This method is thread-safe and can be called from any thread.
        """
        if not self.isRunning():
            return

        logger.info("Stopping MCP server...")

        # Signal shutdown to the server thread (thread-safe)
        self.shutdown_event.set()

        # Wait for thread to exit cleanly (5 second timeout)
        if self.wait(5000):  # QThread.wait() takes milliseconds as positional arg
            logger.info("MCP server stopped gracefully")
        else:
            # Force terminate only if graceful shutdown times out
            logger.warning("Graceful shutdown timeout, force terminating...")
            self.terminate()
            self.wait()
            logger.info("MCP server force terminated")
