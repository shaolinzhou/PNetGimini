import logging
from typing import List, Dict, Tuple, Optional
from .adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

class ConfigDiffEngine:
    """
    Intelligent Configuration Diff & Reversion Engine.
    Computes precise, minimal rollback patches rather than blindly blasting full running-config.
    """

    @classmethod
    def parse_hierarchy(cls, lines: List[str], adapter: BaseAdapter) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Parses configuration lines into global commands and hierarchical block commands.
        Returns (globals_list, blocks_dict).
        """
        globals_list = []
        blocks_dict = {}
        current_block = None

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this line starts a block
            if adapter.is_block_header(stripped):
                current_block = stripped
                if current_block not in blocks_dict:
                    blocks_dict[current_block] = []
                continue

            # Check if exiting block
            if current_block and stripped.lower() in ("exit", "quit", "end"):
                current_block = None
                continue

            # Line is indented or inside block context
            if current_block is not None:
                # If the line is indented or we are actively tracking a block
                if raw_line.startswith(" ") or raw_line.startswith("\t") or not adapter.is_block_header(stripped):
                    blocks_dict[current_block].append(stripped)
                else:
                    # New top level command encountered without explicit exit
                    current_block = None
                    globals_list.append(stripped)
            else:
                globals_list.append(stripped)

        return globals_list, blocks_dict

    @classmethod
    def compute_reversion_plan(
        cls,
        baseline_raw: str,
        deployed_commands: List[str],
        adapter: BaseAdapter
    ) -> List[str]:
        """
        Computes the minimal, accurate reversal sequence to restore the device to its baseline.
        
        :param baseline_raw: The raw snapshot captured before changes
        :param deployed_commands: The list of commands actually executed during deployment
        :param adapter: The vendor adapter for syntax normalization
        :return: List of CLI commands that rollback the deployed changes
        """
        if not deployed_commands:
            logger.info("No deployed commands to reverse.")
            return []

        # 1. Clean and parse the baseline configuration
        clean_baseline_lines = adapter.clean_raw_config(baseline_raw)
        base_globals, base_blocks = cls.parse_hierarchy(clean_baseline_lines, adapter)
        base_globals_set = set(base_globals)

        # 2. Parse the deployed commands
        dep_globals, dep_blocks = cls.parse_hierarchy(deployed_commands, adapter)

        reversal_plan: List[str] = []
        prefix = adapter.get_reversal_prefix()

        # 3. Handle deployed block commands in reverse order
        for block_header, dep_children in reversed(list(dep_blocks.items())):
            base_children = base_blocks.get(block_header)
            block_reversals = adapter.generate_block_reversal(
                block_header=block_header,
                deployed_children=dep_children,
                baseline_children=base_children
            )
            reversal_plan.extend(block_reversals)

        # 4. Handle deployed global commands in reverse order
        for g_cmd in reversed(dep_globals):
            g_str = g_cmd.strip()
            if not g_str or g_str.lower() in ("exit", "quit", "end"):
                continue

            if g_str in base_globals_set:
                # Command was already in baseline; nothing to undo
                continue

            # Check if this modified an existing global parameter (e.g. hostname)
            cmd_root = g_str.split()[0].lower() if g_str.split() else ""
            replaced_base_cmd = None
            if cmd_root in ("hostname", "sysname"):
                for bg in base_globals:
                    if bg.lower().startswith(cmd_root):
                        replaced_base_cmd = bg
                        break

            if replaced_base_cmd:
                reversal_plan.append(replaced_base_cmd)
            elif g_str.lower().startswith(prefix):
                # Deployed command was a negation (e.g. "no ip routing"), reverse it by removing prefix
                reversal_plan.append(g_str[len(prefix):].strip())
            else:
                reversal_plan.append(f"{prefix}{g_str}")

        logger.info(f"Generated diff-based reversal plan with {len(reversal_plan)} commands.")
        return reversal_plan

    @classmethod
    def get_clean_baseline_commands(cls, baseline_raw: str, adapter: BaseAdapter) -> List[str]:
        """
        Returns a cleaned, executable list of baseline commands as a fallback for disaster recovery.
        Strips all commentary, timestamps, and syntax-breaking banners.
        """
        return adapter.clean_raw_config(baseline_raw)
