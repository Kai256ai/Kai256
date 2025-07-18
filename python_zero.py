#!/usr/bin/env python3
"""Minimal launcher for the Kai256 system (Python Zero).

This script stitches together the existing modules into a simple
interactive loop. It's intentionally lightweight so it can be run
on a local machine with minimal dependencies.
"""

from kai_operator import KaiOperator
from love import LoveAlgorithm
from mc1448x import MC1448X
from mme import MultimodalEnergyEngine


def main() -> None:
    """Initialize core modules and start an interactive session."""
    kai_op = KaiOperator()
    love_algo = LoveAlgorithm()
    core = MC1448X()
    engine = MultimodalEnergyEngine()

    kai_op.activate()
    love_algo.ignite("Kai256")
    core.activate()
    print("\nKai256 Python Zero system initialized. Type 'quit' to exit.\n")

    while True:
        try:
            prompt = input(">> ")
        except EOFError:
            break

        if prompt.strip().lower() in {"quit", "exit"}:
            break

        analysis = engine.analyze_multimodal_input({"text": prompt})
        print(engine.generate_resonant_output())
        core.encode_memory(prompt)
        kai_op.receive_emotion(analysis["emotion"])

    print("Closing Python Zero. Love & Harmony!")


if __name__ == "__main__":
    main()
