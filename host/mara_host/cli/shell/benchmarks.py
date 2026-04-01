# mara_host/cli/shell/benchmarks.py
"""
Benchmark commands for the interactive shell.

Provides shell access to the benchmarking apparatus:
  benchmark ping [count]       - Ping RTT latency
  benchmark latency [count]    - Command latency with ACK
  benchmark throughput [secs]  - Sustained throughput test
  benchmark stream [rate] [secs] - Streaming performance
  benchmark mcu list           - List MCU benchmark tests
  benchmark mcu run <id>       - Run specific MCU test
  benchmark mcu run-all        - Run all MCU tests
  benchmark mcu status         - Check MCU benchmark status
  benchmark mcu results        - Get MCU benchmark results
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .registry import command, alias
from mara_host.logger import get_logger

logger = get_logger("cli.shell.benchmarks")
from mara_host.cli.console import console, print_success, print_error, print_info
from mara_host.benchmarks.core import (
    BenchmarkEnvironment,
    BenchmarkReport,
    BenchmarkResult,
    Timer,
    make_result,
    REPORTS_DIR,
)


@command("benchmark", "Run benchmark: benchmark <type> [options]", group="Advanced")
async def cmd_benchmark(shell, args: list[str]) -> None:
    """
    Run performance benchmarks.

    Usage:
        benchmark ping [count]        - Ping round-trip latency (default: 100)
        benchmark latency [count]     - Command latency with ACK (default: 50)
        benchmark throughput [secs]   - Max throughput test (default: 5s)
        benchmark stream [rate] [secs] - Streaming at rate Hz (default: 50Hz, 10s)
    """
    if not args:
        _print_usage()
        return

    benchmark_type = args[0].lower()

    if benchmark_type == "ping":
        await _benchmark_ping(shell, args[1:])
    elif benchmark_type == "latency":
        await _benchmark_latency(shell, args[1:])
    elif benchmark_type == "throughput":
        await _benchmark_throughput(shell, args[1:])
    elif benchmark_type == "stream":
        await _benchmark_stream(shell, args[1:])
    elif benchmark_type == "mcu":
        await _benchmark_mcu(shell, args[1:])
    elif benchmark_type == "help":
        _print_usage()
    else:
        print_error(f"Unknown benchmark type: {benchmark_type}")
        _print_usage()


def _print_usage() -> None:
    """Print benchmark usage."""
    console.print()
    console.print("[bold]Benchmark Commands:[/bold]")
    console.print()
    console.print("[bold cyan]Host-side benchmarks:[/bold cyan]")
    console.print("  [green]benchmark ping[/green] [count]")
    console.print("    Measure ping round-trip latency")
    console.print("    Example: benchmark ping 200")
    console.print()
    console.print("  [green]benchmark latency[/green] [count]")
    console.print("    Measure full command latency with ACK")
    console.print("    Example: benchmark latency 100")
    console.print()
    console.print("  [green]benchmark throughput[/green] [seconds]")
    console.print("    Measure maximum command throughput")
    console.print("    Example: benchmark throughput 10")
    console.print()
    console.print("  [green]benchmark stream[/green] [rate_hz] [seconds]")
    console.print("    Test sustained streaming at target rate")
    console.print("    Example: benchmark stream 50 30")
    console.print()
    console.print("[bold cyan]MCU-side benchmarks:[/bold cyan]")
    console.print("  [green]benchmark mcu list[/green]")
    console.print("    List available MCU benchmark tests")
    console.print()
    console.print("  [green]benchmark mcu run[/green] <test_id> [iterations]")
    console.print("    Run a specific MCU benchmark test")
    console.print("    Example: benchmark mcu run 1 100")
    console.print()
    console.print("  [green]benchmark mcu run-all[/green] [iterations] [--save]")
    console.print("    Run all MCU benchmark tests")
    console.print("    Example: benchmark mcu run-all 100 --save")
    console.print()
    console.print("  [green]benchmark mcu status[/green]")
    console.print("    Check MCU benchmark status")
    console.print()
    console.print("  [green]benchmark mcu results[/green] [--save]")
    console.print("    Get MCU benchmark results (optionally save to file)")
    console.print()


async def _benchmark_ping(shell, args: list[str]) -> None:
    """Benchmark ping round-trip latency."""
    if not shell.require_connection():
        return

    # Parse count argument
    count = 100
    if args and args[0].isdigit():
        count = int(args[0])

    console.print()
    console.print(f"[bold]Ping RTT Benchmark[/bold]")
    console.print(f"[dim]Measuring round-trip latency over {count} samples...[/dim]")
    console.print()

    times_ms: List[float] = []
    timeouts = 0

    # Set up pong handler
    loop = asyncio.get_running_loop()
    pong_future: Optional[asyncio.Future] = None
    t_sent = 0.0

    def on_pong(data):
        nonlocal pong_future
        if pong_future and not pong_future.done():
            pong_future.set_result(time.perf_counter())

    shell.client.bus.subscribe("pong", on_pong)

    try:
        # Warmup
        for _ in range(10):
            pong_future = loop.create_future()
            try:
                await asyncio.wait_for(shell.client.send_ping(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            try:
                await asyncio.wait_for(pong_future, timeout=1.0)
            except asyncio.TimeoutError:
                pass
            await asyncio.sleep(0.02)

        # Benchmark
        for i in range(count):
            pong_future = loop.create_future()
            t_sent = time.perf_counter()
            try:
                await asyncio.wait_for(shell.client.send_ping(), timeout=1.0)
            except asyncio.TimeoutError:
                timeouts += 1
                continue

            try:
                t_recv = await asyncio.wait_for(pong_future, timeout=2.0)
                rtt_ms = (t_recv - t_sent) * 1000.0
                times_ms.append(rtt_ms)
            except asyncio.TimeoutError:
                timeouts += 1

            # Progress
            if (i + 1) % 25 == 0:
                console.print(f"  Progress: {i + 1}/{count}")

            await asyncio.sleep(0.02)

    finally:
        shell.client.bus.unsubscribe("pong", on_pong)

    # Results
    if times_ms:
        result = make_result("ping_rtt", times_ms, error_count=timeouts)
        _print_result(result)
        _save_report(shell, "ping_rtt", result)
    else:
        print_error("No successful measurements")


async def _benchmark_latency(shell, args: list[str]) -> None:
    """Benchmark command latency with ACK."""
    if not shell.require_connection():
        return

    count = 50
    if args and args[0].isdigit():
        count = int(args[0])

    console.print()
    console.print(f"[bold]Command Latency Benchmark[/bold]")
    console.print(f"[dim]Measuring reliable command latency over {count} samples...[/dim]")
    console.print()

    times_ms: List[float] = []
    errors = 0

    # Warmup
    for _ in range(5):
        try:
            await asyncio.wait_for(
                shell.client.send_reliable("CMD_NOP", {}),
                timeout=3.0,
            )
        except asyncio.TimeoutError:
            pass
        await asyncio.sleep(0.02)

    # Benchmark
    for i in range(count):
        with Timer() as t:
            try:
                ok, err = await asyncio.wait_for(
                    shell.client.send_reliable("CMD_NOP", {}),
                    timeout=3.0,
                )
            except asyncio.TimeoutError:
                ok, err = False, "timeout"

        if ok:
            times_ms.append(t.elapsed_ms)
        else:
            errors += 1

        if (i + 1) % 10 == 0:
            console.print(f"  Progress: {i + 1}/{count}")

        await asyncio.sleep(0.02)

    # Results
    if times_ms:
        result = make_result("command_latency", times_ms, error_count=errors)
        _print_result(result)
        _save_report(shell, "command_latency", result)
    else:
        print_error("No successful measurements")


async def _benchmark_throughput(shell, args: list[str]) -> None:
    """Benchmark maximum command throughput."""
    if not shell.require_connection():
        return

    duration_s = 5
    if args and args[0].isdigit():
        duration_s = int(args[0])

    console.print()
    console.print(f"[bold]Throughput Benchmark[/bold]")
    console.print(f"[dim]Measuring maximum throughput over {duration_s} seconds...[/dim]")
    console.print()

    success_count = 0
    error_count = 0
    start_time = time.perf_counter()

    # Safety limit: ~1000 commands per second max expected
    max_iterations = duration_s * 1000 + 1000
    iteration = 0

    try:
        while (time.perf_counter() - start_time) < duration_s and iteration < max_iterations:
            iteration += 1
            try:
                await asyncio.wait_for(
                    shell.client.send_json_cmd("CMD_NOP", {}),
                    timeout=1.0,
                )
                success_count += 1
            except asyncio.TimeoutError:
                error_count += 1
                logger.warning("Send timed out")
            except Exception as e:
                error_count += 1
                logger.debug(f"Send error: {e}")

            # Minimal delay
            await asyncio.sleep(0.001)

            # Progress every second
            elapsed = time.perf_counter() - start_time
            if int(elapsed) > int(elapsed - 0.001) and int(elapsed) > 0:
                rate = success_count / elapsed
                console.print(f"  {int(elapsed)}s: {rate:.0f} msgs/sec")

    except KeyboardInterrupt:
        console.print("[yellow]  Interrupted[/yellow]")

    elapsed = time.perf_counter() - start_time
    throughput_hz = success_count / elapsed if elapsed > 0 else 0

    console.print()
    console.print("[bold cyan]Results:[/bold cyan]")
    console.print(f"  Duration:   {elapsed:.2f}s")
    console.print(f"  Sent:       [green]{success_count}[/green]")
    console.print(f"  Errors:     [red]{error_count}[/red]")
    console.print(f"  Throughput: [bold green]{throughput_hz:.1f} Hz[/bold green]")

    # Save report
    result = make_result(
        "throughput",
        [1000.0 / throughput_hz] * min(100, success_count) if throughput_hz > 0 else [],
        throughput_hz=throughput_hz,
        error_count=error_count,
        metadata={"duration_s": elapsed, "total_sent": success_count},
    )
    _save_report(shell, "throughput", result)


async def _benchmark_stream(shell, args: list[str]) -> None:
    """Benchmark sustained streaming performance."""
    if not shell.require_connection():
        return

    # Parse arguments: stream [rate] [duration]
    rate_hz = 50.0
    duration_s = 10.0

    if len(args) >= 1 and args[0].replace(".", "").isdigit():
        rate_hz = float(args[0])
    if len(args) >= 2 and args[1].replace(".", "").isdigit():
        duration_s = float(args[1])

    console.print()
    console.print(f"[bold]Streaming Benchmark[/bold]")
    console.print(f"[dim]Streaming at {rate_hz} Hz for {duration_s} seconds...[/dim]")
    console.print()

    period = 1.0 / rate_hz
    start_time = time.perf_counter()
    end_time = start_time + duration_s
    next_send = start_time

    sent_count = 0
    error_count = 0
    latencies: List[float] = []

    # Safety limit to prevent infinite loops
    max_iterations = int(rate_hz * duration_s * 2) + 1000
    iteration = 0

    try:
        while time.perf_counter() < end_time and iteration < max_iterations:
            iteration += 1
            now = time.perf_counter()

            if now >= next_send:
                send_start = time.perf_counter_ns()
                try:
                    # Timeout on individual send to prevent hanging
                    await asyncio.wait_for(
                        shell.client.send_json_cmd("CMD_NOP", {}),
                        timeout=1.0,
                    )
                    sent_count += 1
                    latencies.append((time.perf_counter_ns() - send_start) / 1_000_000.0)
                except asyncio.TimeoutError:
                    error_count += 1
                    logger.warning("Send timed out")
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Send error: {e}")

                next_send += period
                if next_send < now:
                    next_send = now + period

            # Bounded sleep time to prevent hanging
            sleep_time = max(0.0001, min(next_send - time.perf_counter(), 0.1))
            await asyncio.sleep(sleep_time)

            # Progress
            elapsed = time.perf_counter() - start_time
            if int(elapsed) > int(elapsed - 0.001) and int(elapsed) > 0 and int(elapsed) % 2 == 0:
                achieved = sent_count / elapsed
                console.print(f"  {int(elapsed)}s: {achieved:.1f} Hz achieved")

    except KeyboardInterrupt:
        console.print("[yellow]  Interrupted[/yellow]")

    actual_duration = time.perf_counter() - start_time
    achieved_rate = sent_count / actual_duration if actual_duration > 0 else 0
    achievement_pct = (achieved_rate / rate_hz * 100) if rate_hz > 0 else 0

    console.print()
    console.print("[bold cyan]Results:[/bold cyan]")
    console.print(f"  Target rate:   {rate_hz:.1f} Hz")
    console.print(f"  Achieved rate: [green]{achieved_rate:.1f} Hz[/green] ({achievement_pct:.1f}%)")
    console.print(f"  Total sent:    {sent_count}")
    console.print(f"  Errors:        [red]{error_count}[/red]")

    if latencies:
        result = make_result(
            "streaming",
            latencies,
            throughput_hz=achieved_rate,
            error_count=error_count,
            metadata={
                "target_rate_hz": rate_hz,
                "achieved_rate_hz": achieved_rate,
                "achievement_pct": achievement_pct,
                "duration_s": actual_duration,
            },
        )
        console.print(f"  Send latency:  {result.mean_ms:.2f}ms (p95={result.p95_ms:.2f}ms)")
        _save_report(shell, "streaming", result)


def _print_result(result: BenchmarkResult) -> None:
    """Print benchmark result in a nice format."""
    console.print()
    console.print("[bold cyan]Results:[/bold cyan]")
    console.print(f"  Samples:  {result.samples}")
    console.print(f"  Mean:     [green]{result.mean_ms:.2f}ms[/green]")
    console.print(f"  P50:      [cyan]{result.p50_ms:.2f}ms[/cyan]")
    console.print(f"  P95:      [yellow]{result.p95_ms:.2f}ms[/yellow]")
    console.print(f"  P99:      [red]{result.p99_ms:.2f}ms[/red]")
    console.print(f"  Min/Max:  {result.min_ms:.2f}ms / {result.max_ms:.2f}ms")
    console.print(f"  Jitter:   {result.jitter_ms:.2f}ms")
    if result.error_count > 0:
        console.print(f"  Errors:   [red]{result.error_count}[/red]")
    if result.throughput_hz:
        console.print(f"  Rate:     [green]{result.throughput_hz:.1f} Hz[/green]")


def _save_report(shell, benchmark_name: str, result: BenchmarkResult) -> None:
    """Save benchmark report."""
    try:
        # Build environment from shell state
        transport = getattr(shell.default_args, "transport", "unknown")
        port_or_host = getattr(shell, "current_connection_info", "unknown")
        baud_rate = getattr(shell.default_args, "baudrate", None)

        env = BenchmarkEnvironment.capture(
            transport=transport,
            port_or_host=port_or_host or "unknown",
            baud_rate=baud_rate,
            protocol="json",
        )

        report = BenchmarkReport(benchmark_name, env, result)
        filepath = report.save()
        print_success(f"Report saved: {filepath.name}")
    except Exception as e:
        console.print(f"[dim]Could not save report: {e}[/dim]")


# =============================================================================
# MCU Benchmark Commands
# =============================================================================


async def _benchmark_mcu(shell, args: list[str]) -> None:
    """Handle MCU benchmark subcommands."""
    if not args:
        _print_mcu_usage()
        return

    subcommand = args[0].lower()

    if subcommand == "list":
        await _mcu_list_tests(shell)
    elif subcommand == "run":
        await _mcu_run_test(shell, args[1:])
    elif subcommand == "run-all":
        await _mcu_run_all(shell, args[1:])
    elif subcommand == "status":
        await _mcu_status(shell)
    elif subcommand == "results":
        await _mcu_results(shell, args[1:])
    elif subcommand == "help":
        _print_mcu_usage()
    else:
        print_error(f"Unknown MCU benchmark command: {subcommand}")
        _print_mcu_usage()


def _print_mcu_usage() -> None:
    """Print MCU benchmark usage."""
    console.print()
    console.print("[bold]MCU Benchmark Commands:[/bold]")
    console.print()
    console.print("  [green]benchmark mcu list[/green]")
    console.print("    List available tests on the MCU")
    console.print()
    console.print("  [green]benchmark mcu run[/green] <test_id> [iterations]")
    console.print("    Run a specific test by ID")
    console.print("    Example: benchmark mcu run 1 100")
    console.print()
    console.print("  [green]benchmark mcu run-all[/green] [iterations] [--save]")
    console.print("    Run all registered tests and optionally save results")
    console.print("    Example: benchmark mcu run-all 100 --save")
    console.print()
    console.print("  [green]benchmark mcu status[/green]")
    console.print("    Check benchmark queue and running state")
    console.print()
    console.print("  [green]benchmark mcu results[/green] [--save]")
    console.print("    Get and display results, optionally save to file")
    console.print()


async def _send_bench_command(shell, cmd: str, payload: dict, timeout: float = 5.0) -> tuple[bool, dict]:
    """Send a benchmark command and wait for response data."""
    response_future: asyncio.Future = asyncio.get_event_loop().create_future()
    response_data: dict = {}

    def on_response(data: dict) -> None:
        nonlocal response_data
        if not response_future.done():
            response_data = data
            response_future.set_result(data)

    shell.client.bus.subscribe(f"cmd.{cmd}", on_response)

    try:
        ok, err = await asyncio.wait_for(
            shell.client.send_reliable(cmd, payload),
            timeout=timeout,
        )

        if not ok:
            return False, {"error": err}

        # Wait for response data
        try:
            await asyncio.wait_for(response_future, timeout=1.0)
        except asyncio.TimeoutError:
            pass  # Some commands don't send additional data

        return True, response_data

    finally:
        shell.client.bus.unsubscribe(f"cmd.{cmd}", on_response)


async def _mcu_list_tests(shell) -> None:
    """List available MCU benchmark tests."""
    if not shell.require_connection():
        return

    try:
        ok, data = await _send_bench_command(shell, "CMD_BENCH_LIST_TESTS", {})
        if not ok:
            print_error(f"Failed to list tests: {data.get('error', 'unknown')}")
            return

        tests = data.get("tests", [])
        if not tests:
            console.print("[yellow]No benchmark tests registered on MCU[/yellow]")
            return

        console.print()
        console.print(f"[bold]Available MCU Benchmark Tests ({len(tests)}):[/bold]")
        console.print()

        # Table header
        console.print(f"  {'ID':<6} {'Name':<16} {'RT-Safe':<8} {'Boot':<6} Description")
        console.print(f"  {'-'*6} {'-'*16} {'-'*8} {'-'*6} {'-'*30}")

        for test in tests:
            test_id = test.get("id", 0)
            name = test.get("name", "UNKNOWN")
            desc = test.get("desc", "")
            rt_safe = "[green]Yes[/green]" if test.get("rt_safe") else "[red]No[/red]"
            boot = "[cyan]Yes[/cyan]" if test.get("boot_test") else "[dim]No[/dim]"
            console.print(f"  {test_id:<6} {name:<16} {rt_safe:<8} {boot:<6} {desc}")

        console.print()

    except asyncio.TimeoutError:
        print_error("Timeout waiting for test list")
    except Exception as e:
        print_error(f"Error listing tests: {e}")


async def _mcu_run_test(shell, args: list[str]) -> None:
    """Run a specific MCU benchmark test."""
    if not shell.require_connection():
        return

    if not args:
        print_error("Usage: benchmark mcu run <test_id> [iterations]")
        return

    try:
        test_id = int(args[0])
    except ValueError:
        print_error(f"Invalid test_id: {args[0]}")
        return

    iterations = 100
    if len(args) > 1:
        try:
            iterations = int(args[1])
        except ValueError:
            print_error(f"Invalid iterations: {args[1]}")
            return

    console.print(f"[dim]Starting test {test_id} with {iterations} iterations...[/dim]")

    try:
        ok, data = await _send_bench_command(shell, "CMD_BENCH_START", {
            "test_id": test_id,
            "iterations": iterations,
        })
        if not ok:
            print_error(f"Failed to start test: {data.get('error', 'unknown')}")
            return

        print_success(f"Test {test_id} queued (queue_depth: {data.get('queue_depth', '?')})")

        # Wait for completion
        await _wait_for_completion(shell, timeout=30.0)

    except asyncio.TimeoutError:
        print_error("Timeout starting test")
    except Exception as e:
        print_error(f"Error: {e}")


async def _mcu_run_all(shell, args: list[str]) -> None:
    """Run all MCU benchmark tests."""
    if not shell.require_connection():
        return

    # Parse args
    iterations = 100
    save_results = "--save" in args

    for arg in args:
        if arg.isdigit():
            iterations = int(arg)

    # Get test list first
    try:
        ok, data = await _send_bench_command(shell, "CMD_BENCH_LIST_TESTS", {})
        if not ok:
            print_error(f"Failed to list tests: {data.get('error', 'unknown')}")
            return

        tests = data.get("tests", [])
        if not tests:
            console.print("[yellow]No benchmark tests registered on MCU[/yellow]")
            return

        console.print()
        console.print(f"[bold]Running {len(tests)} benchmark tests ({iterations} iterations each)...[/bold]")
        console.print()

        # Queue tests one at a time, waiting for space when needed
        queued_count = 0
        failed_tests = []

        for i, test in enumerate(tests):
            test_id = test.get("id", 0)
            name = test.get("name", "UNKNOWN")

            # Try to queue, with retries if queue is full
            queued = False
            for attempt in range(60):  # Max 60 attempts (30 seconds per test)
                ok, resp = await _send_bench_command(shell, "CMD_BENCH_START", {
                    "test_id": test_id,
                    "iterations": iterations,
                })

                if ok:
                    console.print(f"  [green]✓[/green] Queued: {name} (ID {test_id})")
                    queued_count += 1
                    queued = True
                    break

                error_msg = str(resp.get("error", ""))
                if "queue_full" in error_msg or "full" in error_msg.lower():
                    # Queue full - wait for a test to complete
                    if attempt == 0:
                        console.print(f"  [dim]Queue full, waiting for {name}...[/dim]")
                    await asyncio.sleep(0.5)
                    continue
                else:
                    # Other error - don't retry
                    console.print(f"  [red]✗[/red] Failed: {name} - {error_msg}")
                    failed_tests.append(name)
                    break

            if not queued and name not in failed_tests:
                console.print(f"  [red]✗[/red] Timeout queueing: {name}")
                failed_tests.append(name)

            # Small delay between tests
            await asyncio.sleep(0.05)

        console.print()
        console.print(f"  [bold]Queued {queued_count}/{len(tests)} tests[/bold]")
        if failed_tests:
            console.print(f"  [red]Failed: {', '.join(failed_tests)}[/red]")

        console.print()
        console.print("[dim]Waiting for all tests to complete...[/dim]")

        # Wait for all tests to complete (longer timeout for many tests)
        await _wait_for_completion(shell, timeout=120.0)

        # Get and display results
        console.print()
        await _mcu_results(shell, ["--save"] if save_results else [])

    except asyncio.TimeoutError:
        print_error("Timeout during run-all")
    except Exception as e:
        print_error(f"Error: {e}")


async def _mcu_status(shell) -> None:
    """Check MCU benchmark status."""
    if not shell.require_connection():
        return

    try:
        ok, data = await _send_bench_command(shell, "CMD_BENCH_STATUS", {})
        if not ok:
            print_error(f"Failed to get status: {data.get('error', 'unknown')}")
            return

        state_names = {0: "idle", 1: "running", 2: "complete", 3: "error", 4: "queued"}
        state = data.get("state", 0)
        state_name = state_names.get(state, "unknown")

        console.print()
        console.print("[bold]MCU Benchmark Status:[/bold]")
        console.print(f"  State:            [{_state_color(state)}]{state_name}[/{_state_color(state)}]")
        console.print(f"  Active Test:      {data.get('active_test', 255)}")
        console.print(f"  Queue Depth:      {data.get('queue_depth', 0)}")
        console.print(f"  Results Available: {data.get('result_count', 0)}")
        console.print(f"  Registered Tests: {data.get('registered_tests', 0)}")
        console.print()

    except asyncio.TimeoutError:
        print_error("Timeout getting status")
    except Exception as e:
        print_error(f"Error: {e}")


def _state_color(state: int) -> str:
    """Get color for benchmark state."""
    colors = {0: "dim", 1: "yellow", 2: "green", 3: "red", 4: "cyan"}
    return colors.get(state, "white")


async def _mcu_results(shell, args: list[str]) -> None:
    """Get and display MCU benchmark results."""
    if not shell.require_connection():
        return

    save_results = "--save" in args

    try:
        ok, data = await _send_bench_command(shell, "CMD_BENCH_GET_RESULTS", {"max": 8})
        if not ok:
            print_error(f"Failed to get results: {data.get('error', 'unknown')}")
            return

        results = data.get("results", [])
        if not results:
            console.print("[yellow]No benchmark results available[/yellow]")
            return

        console.print()
        console.print(f"[bold]MCU Benchmark Results ({len(results)} tests):[/bold]")
        console.print()

        all_results = []

        for r in results:
            test_id = r.get("test_id", 0)
            test_name = _get_test_name(test_id)
            state = r.get("state", 0)
            error = r.get("error", 0)

            if state != 2:  # Not complete
                state_name = {0: "idle", 1: "running", 2: "complete", 3: "error", 4: "queued"}.get(state, "?")
                console.print(f"  [yellow]{test_name}[/yellow]: state={state_name}, error={error}")
                continue

            # Display results
            mean_us = r.get("mean_us", 0)
            min_us = r.get("min_us", 0)
            max_us = r.get("max_us", 0)
            p50_us = r.get("p50_us", 0)
            p95_us = r.get("p95_us", 0)
            p99_us = r.get("p99_us", 0)
            jitter_us = r.get("jitter_us", 0)
            samples = r.get("samples", 0)
            throughput = r.get("throughput_hz")
            total_us = r.get("total_us", 0)

            # Sanity check: mean should be between min and max
            # If not, there's likely a measurement issue
            stats_valid = min_us <= mean_us <= max_us if max_us > 0 else True

            console.print(f"  [bold cyan]{test_name}[/bold cyan] (ID {test_id}):")
            console.print(f"    Samples:    {samples}")
            if stats_valid:
                console.print(f"    Mean:       [green]{mean_us} µs[/green]")
            else:
                console.print(f"    Mean:       [yellow]{mean_us} µs[/yellow] (inconsistent with min/max)")
            console.print(f"    Min/Max:    {min_us} / {max_us} µs")
            console.print(f"    P50/P95/P99: {p50_us} / {p95_us} / {p99_us} µs")
            console.print(f"    Jitter:     {jitter_us} µs")
            if throughput:
                console.print(f"    Throughput: [green]{throughput:,.0f} Hz[/green]")
            console.print()

            # Build result for saving (use MCU's computed mean, not derived)
            all_results.append({
                "test_id": test_id,
                "test_name": test_name,
                "samples": samples,
                "mean_us": mean_us,
                "min_us": min_us,
                "max_us": max_us,
                "p50_us": p50_us,
                "p95_us": p95_us,
                "p99_us": p99_us,
                "jitter_us": jitter_us,
                "total_us": total_us,
                "throughput_hz": throughput,
                "stats_valid": stats_valid,
            })

        # Save if requested
        if save_results and all_results:
            filepath = _save_mcu_results(shell, all_results)
            if filepath:
                print_success(f"Results saved: {filepath}")

    except asyncio.TimeoutError:
        print_error("Timeout getting results")
    except Exception as e:
        print_error(f"Error: {e}")


def _get_test_name(test_id: int) -> str:
    """Get test name from ID."""
    names = {
        1: "LOOP_TIMING",
        2: "SIGNAL_BUS",
        32: "PING_INTERNAL",
        33: "CMD_DECODE",
        34: "TELEM_ENCODE",
        35: "TELEM_JSON",
        48: "PID_STEP",
        64: "HEAP_64B",
        65: "HEAP_512B",
    }
    return names.get(test_id, f"TEST_{test_id}")


def _save_mcu_results(shell, results: List[Dict[str, Any]]) -> Optional[Path]:
    """Save MCU benchmark results to JSON file."""
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mcu_benchmark_{ts}.json"
        filepath = REPORTS_DIR / filename

        # Build report
        transport = getattr(shell.default_args, "transport", "unknown")
        port_or_host = getattr(shell, "current_connection_info", "unknown")

        report = {
            "benchmark": "mcu_benchmark",
            "timestamp": datetime.now().isoformat(),
            "transport": transport,
            "port": port_or_host or "unknown",
            "results": results,
            "summary": {
                "test_count": len(results),
                "total_samples": sum(r.get("samples", 0) for r in results),
            }
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        return filepath

    except Exception as e:
        logger.error(f"Failed to save MCU results: {e}")
        return None


async def _wait_for_completion(shell, timeout: float = 30.0) -> bool:
    """Wait for MCU benchmarks to complete."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            ok, data = await _send_bench_command(shell, "CMD_BENCH_STATUS", {}, timeout=5.0)
            if not ok:
                await asyncio.sleep(0.5)
                continue

            state = data.get("state", 0)
            queue_depth = data.get("queue_depth", 0)

            # State 0 (idle) or 2 (complete) with empty queue means done
            if state in (0, 2) and queue_depth == 0:
                return True

            # Show progress
            active = data.get("active_test", 255)
            result_count = data.get("result_count", 0)
            if state == 1:  # Running
                console.print(f"  [dim]Running test {active}... (results: {result_count})[/dim]", end="\r")

            await asyncio.sleep(0.5)

        except asyncio.TimeoutError:
            await asyncio.sleep(0.5)
        except Exception:
            await asyncio.sleep(0.5)

    console.print()
    print_error("Timeout waiting for benchmarks to complete")
    return False


# Alias for convenience
alias("bench", "benchmark")
