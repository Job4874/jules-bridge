import psutil
import subprocess

class VMBootError(Exception):
    pass

def check_and_scale_compute(dry_run: bool = True, allow_vm_boot: bool = False) -> str:
    """Checks system memory and starts Azure VM if memory is > 85%."""
    mem = psutil.virtual_memory()
    
    if mem.percent > 85.0:
        if dry_run:
            return "DRY_RUN: Would execute az vm start --name OracleV5"
            
        if not allow_vm_boot:
            raise VMBootError("VM Boot attempted but allow_vm_boot=False")
            
        subprocess.run(["az", "vm", "start", "--name", "OracleV5", "--resource-group", "QuantowerGroup"], check=True)
        return "EXECUTED: az vm start --name OracleV5"
        
    return f"Memory at {mem.percent}%, no action needed."
