import re

with open('modules/vm_manager.py', 'r') as f:
    content = f.read()

# Add the function check_and_scale_compute to __all__ if __all__ exists or document it at top
if "__all__" in content:
    # Too complex, not doing for now
    pass
