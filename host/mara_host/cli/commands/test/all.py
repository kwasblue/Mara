# mara_host/cli/commands/test/all.py
"""Run all self-tests."""

import argparse
import asyncio
import time

from mara_host.cli.console import console
from ._common import TestResult, print_results, create_client_from_args


def cmd_all(args: argparse.Namespace) -> int:
    """Run all self-tests."""
    console.print()
    console.print("[bold cyan]Robot Self-Test Suite[/bold cyan]")
    console.print()

    return asyncio.run(_run_all_tests(args))


async def _run_all_tests(args: argparse.Namespace) -> int:
    """Run all tests."""
    client = create_client_from_args(args)
    results: list[TestResult] = []

    try:
        # Test 1: Connection
        start = time.time()
        try:
            await client.start()
            results.append(TestResult(
                "Connection",
                True,
                "Connected successfully",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("Connection", False, str(e)))
            print_results(results)
            return 1

        # Test 2: Ping/Pong
        start = time.time()
        pong_received = asyncio.Event()

        def on_pong(data):
            pong_received.set()

        client.bus.subscribe("pong", on_pong)
        await client.send_ping()

        try:
            await asyncio.wait_for(pong_received.wait(), timeout=2.0)
            results.append(TestResult(
                "Ping/Pong",
                True,
                "Response received",
                (time.time() - start) * 1000
            ))
        except asyncio.TimeoutError:
            results.append(TestResult("Ping/Pong", False, "Timeout - no response"))

        # Test 3: Arm/Disarm
        start = time.time()
        try:
            await client.cmd_arm()
            await asyncio.sleep(0.1)
            await client.cmd_disarm()
            results.append(TestResult(
                "Arm/Disarm",
                True,
                "State transitions OK",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("Arm/Disarm", False, str(e)))

        # Test 4: Mode switching
        start = time.time()
        try:
            await client.cmd_set_mode("IDLE")
            await asyncio.sleep(0.1)
            await client.cmd_set_mode("ACTIVE")
            await asyncio.sleep(0.1)
            await client.cmd_set_mode("IDLE")
            results.append(TestResult(
                "Mode Switch",
                True,
                "IDLE -> ACTIVE -> IDLE OK",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("Mode Switch", False, str(e)))

        # Test 5: LED
        start = time.time()
        try:
            await client.cmd_led_on()
            await asyncio.sleep(0.2)
            await client.cmd_led_off()
            results.append(TestResult(
                "LED Control",
                True,
                "On/Off commands sent",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("LED Control", False, str(e)))

        # Test 6: Heartbeat reception
        start = time.time()
        heartbeat_received = asyncio.Event()

        def on_heartbeat(data):
            heartbeat_received.set()

        client.bus.subscribe("heartbeat", on_heartbeat)

        try:
            await asyncio.wait_for(heartbeat_received.wait(), timeout=3.0)
            results.append(TestResult(
                "Heartbeat",
                True,
                "Receiving heartbeats",
                (time.time() - start) * 1000
            ))
        except asyncio.TimeoutError:
            results.append(TestResult("Heartbeat", False, "No heartbeat received"))

    finally:
        await client.stop()

    print_results(results)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    return 0 if failed == 0 else 1
