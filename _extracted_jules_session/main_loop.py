import time
from modules.vm_manager import check_and_scale_compute
from modules.router import dispatch

def read_inbox():
    """Mock reading the inbox."""
    return None

def daemon_loop_iteration():
    """Single iteration of the daemon loop."""
    # 1. Call detect_resource_pressure() -> maps to our VM manager
    check_and_scale_compute(dry_run=False, allow_vm_boot=True)
    
    # 2. Check /inbox/read
    task = read_inbox()
    
    # 3. If new task found: Call router.dispatch()
    if task:
        dispatch(task)

def start_daemon():
    """Run the daemon loop every 30 seconds."""
    while True:
        daemon_loop_iteration()
        time.sleep(30)
