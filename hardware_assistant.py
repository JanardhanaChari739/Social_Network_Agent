"""
Problem 2: Local Linux Hardware Q&A Assistant - Safe Tool Execution & Grounding Engine
Asama.ai Engineering Assignment Reference Implementation
"""

import sys
import os
import json
import re
import shutil
import subprocess
from typing import Dict, Any, List, Optional


# ============================================================================
# 1. ALLOW-LISTED TOOL DEFINITIONS & SAFE EXECUTOR
# ============================================================================

ALLOW_LISTED_COMMANDS: Dict[str, List[str]] = {
    "get_cpu_info": ["lscpu", "-J"],
    "get_storage_topology": ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,ROTA,TRAN"],
    "get_memory_summary": ["free", "-b"],
    "get_pci_devices": ["lspci", "-mm"],
    "get_dmi_memory": ["sudo", "-n", "dmidecode", "-t", "memory"],
    "get_dmi_system": ["sudo", "-n", "dmidecode", "-t", "system"],
}


def safe_execute_command(tool_name: str, timeout_seconds: int = 5) -> Dict[str, Any]:
    """
    Executes pre-authorized system commands using strict execve (shell=False).
    Prevents shell injection, flag manipulation, and arbitrary binary execution.
    """
    if tool_name not in ALLOW_LISTED_COMMANDS:
        return {"error": f"Security Violation: Tool '{tool_name}' is not in the system allow-list."}

    cmd = ALLOW_LISTED_COMMANDS[tool_name]
    binary_name = cmd[0] if cmd[0] != "sudo" else cmd[2]

    if not shutil.which(binary_name):
        return {"error": f"Missing Tool: Binary '{binary_name}' is not installed on this host."}

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            shell=False
        )

        if proc.returncode != 0:
            stderr_msg = proc.stderr.strip()
            if "permission denied" in stderr_msg.lower() or "password is required" in stderr_msg.lower():
                return {
                    "error": "Privilege Required: This query requires root/sudo access. "
                             "Please configure /etc/sudoers.d/hw-assistant or run in unprivileged fallback mode."
                }
            return {"error": f"Command returned exit code {proc.returncode}: {stderr_msg}"}

        return parse_output(tool_name, proc.stdout)

    except subprocess.TimeoutExpired:
        return {"error": f"Timeout: Tool '{tool_name}' timed out after {timeout_seconds} seconds."}
    except Exception as exc:
        return {"error": f"Execution Failure: {str(exc)}"}


# ============================================================================
# 2. OUTPUT PARSERS & NORMALIZERS
# ============================================================================

def parse_output(tool_name: str, stdout: str) -> Dict[str, Any]:
    if tool_name == "get_storage_topology":
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw_output": stdout}

    elif tool_name == "get_cpu_info":
        try:
            data = json.loads(stdout)
            kv = {}
            for item in data.get("lscpu", []):
                kv[item["field"].rstrip(":")] = item["data"]
            return {
                "model_name": kv.get("Model name", "Unknown"),
                "architecture": kv.get("Architecture", "Unknown"),
                "total_cores": kv.get("CPU(s)", "Unknown"),
                "threads_per_core": kv.get("Thread(s) per core", "Unknown"),
                "l3_cache": kv.get("L3 cache", "Unknown"),
                "virtualization": kv.get("Virtualization", "None")
            }
        except Exception:
            return {"raw_output": stdout}

    elif tool_name == "get_memory_summary":
        lines = stdout.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 7:
                return {
                    "total_ram_bytes": int(parts[1]),
                    "used_ram_bytes": int(parts[2]),
                    "free_ram_bytes": int(parts[3]),
                    "available_ram_bytes": int(parts[6]),
                    "total_ram_gb": round(int(parts[1]) / (1024**3), 2),
                    "available_ram_gb": round(int(parts[6]) / (1024**3), 2)
                }
        return {"raw_output": stdout}

    elif tool_name == "get_dmi_memory":
        max_cap = re.search(r"Maximum Capacity:\s*(.+)", stdout)
        devices = stdout.split("Memory Device")
        slots = []
        used = 0

        for dev in devices[1:]:
            size_m = re.search(r"Size:\s*(.+)", dev)
            loc_m = re.search(r"Locator:\s*(.+)", dev)
            type_m = re.search(r"Type:\s*(.+)", dev)
            speed_m = re.search(r"Speed:\s*(.+)", dev)

            size_str = size_m.group(1).strip() if size_m else "Unknown"
            installed = "No Module" not in size_str and size_str != "Unknown"
            if installed:
                used += 1

            slots.append({
                "slot_name": loc_m.group(1).strip() if loc_m else "Unknown",
                "size": size_str,
                "type": type_m.group(1).strip() if type_m else "Unknown",
                "speed": speed_m.group(1).strip() if speed_m else "Unknown",
                "installed": installed
            })

        return {
            "max_supported_capacity": max_cap.group(1).strip() if max_cap else "Unknown",
            "total_physical_slots": len(slots),
            "used_slots": used,
            "free_slots": len(slots) - used,
            "slot_details": slots
        }

    return {"raw_output": stdout}


# ============================================================================
# 3. CONTEXTUAL ANSWER SYNTHESIS (GROUNDING ENGINE)
# ============================================================================

class HardwareAssistant:
    def query(self, user_question: str) -> str:
        q_lower = user_question.lower()

        if "ram" in q_lower or "memory" in q_lower:
            mem_summary = safe_execute_command("get_memory_summary")
            dmi_mem = safe_execute_command("get_dmi_memory")

            if "error" in dmi_mem and "Privilege Required" in dmi_mem["error"]:
                installed = mem_summary.get("total_ram_gb", "Unknown")
                avail = mem_summary.get("available_ram_gb", "Unknown")
                return (
                    f"Installed Memory: {installed} GB ({avail} GB available).\n"
                    f"Notice: Detailed motherboard upgrade capacity requires root privileges (dmidecode). "
                    f"Please enable scoped sudo rules to inspect physical empty slots."
                )

            max_cap = dmi_mem.get("max_supported_capacity", "Unknown")
            total_slots = dmi_mem.get("total_physical_slots", 0)
            used_slots = dmi_mem.get("used_slots", 0)
            free_slots = dmi_mem.get("free_slots", 0)

            return (
                f"Memory Topology:\n"
                f"- Maximum Supported Capacity: {max_cap}\n"
                f"- Total Motherboard Slots: {total_slots}\n"
                f"- Occupied Slots: {used_slots}\n"
                f"- Free Slots: {free_slots}\n"
                f"Conclusion: You have {free_slots} open slot(s) for expansion up to {max_cap}."
            )

        elif "cpu" in q_lower or "processor" in q_lower:
            cpu_info = safe_execute_command("get_cpu_info")
            if "error" in cpu_info:
                return f"Error retrieving CPU info: {cpu_info['error']}"
            return (
                f"CPU Specifications:\n"
                f"- Model: {cpu_info.get('model_name')}\n"
                f"- Architecture: {cpu_info.get('architecture')}\n"
                f"- Total Cores/Threads: {cpu_info.get('total_cores')}\n"
                f"- L3 Cache: {cpu_info.get('l3_cache')}\n"
                f"- Virtualization: {cpu_info.get('virtualization')}"
            )

        return "I can inspect Memory (RAM), CPU, and Storage. Please ask a specific hardware query."


if __name__ == "__main__":
    assistant = HardwareAssistant()
    print("Local Linux Hardware Q&A Assistant Initialized.")
    resp = assistant.query("Can I upgrade my RAM?")
    print("\nAssistant Output:\n" + resp)
