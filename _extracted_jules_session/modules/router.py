def dispatch(task_packet: dict) -> str:
    """Intelligent Task Router to classify and route a task packet."""
    task_type = task_packet.get("type")
    
    if task_type == "Code/Dev":
        return "Cursor/Jules"
    elif task_type == "Compute/Scale":
        return "Azure/Local VM"
    elif task_type == "Routine/UI":
        return "human_mimic_driver"
        
    return "UNROUTED"
