#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for AI Energy Orchestrator simulation.

Demonstrates baseline vs optimization scenarios with full KPI reporting.
"""

import argparse
import sys
import logging
from simulation.estate_simulator import EstateSimulator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)

logger = logging.getLogger(__name__)


def main(
    num_homes: int = 50,
    num_days: int = 30,
    transformer_capacity_kw: float = 100.0,
    transformer_upgrade_cost_gbp: float = 250000.0,
    export: bool = True,
    seed: int = 42,
):
    """Run full estate simulation."""
    
    logger.info(f"Initializing simulation:")
    logger.info(f"  Homes: {num_homes}")
    logger.info(f"  Days: {num_days}")
    logger.info(f"  Transformer: {transformer_capacity_kw} kW")
    logger.info(f"  Upgrade cost: GBP {transformer_upgrade_cost_gbp}")
    logger.info("")
    
    # Create and run simulator
    simulator = EstateSimulator(
        num_homes=num_homes,
        num_days=num_days,
        transformer_capacity_kw=transformer_capacity_kw,
        transformer_upgrade_cost_gbp=transformer_upgrade_cost_gbp,
        seed=seed,
    )
    
    # Run full simulation
    report = simulator.run_full_simulation()
    
    # Export results
    if export:
        simulator.export_results()
    
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Energy Orchestrator estate simulation"
    )
    parser.add_argument(
        "--homes",
        type=int,
        default=50,
        help="Number of households (default: 50)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of simulation days (default: 30)",
    )
    parser.add_argument(
        "--transformer-kw",
        type=float,
        default=100.0,
        help="Transformer capacity [kW] (default: 100)",
    )
    parser.add_argument(
        "--upgrade-cost",
        type=float,
        default=250000.0,
        help="Transformer upgrade cost [£] (default: 250000)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip CSV export",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    
    args = parser.parse_args()
    
    try:
        report = main(
            num_homes=args.homes,
            num_days=args.days,
            transformer_capacity_kw=args.transformer_kw,
            transformer_upgrade_cost_gbp=args.upgrade_cost,
            export=not args.no_export,
            seed=args.seed,
        )
        
        logger.info("Simulation completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        sys.exit(1)
