import pytest
from unittest.mock import patch, MagicMock
from modules.vm_manager import check_and_scale_compute, VMBootError

@patch('modules.vm_manager.psutil.virtual_memory')
@patch('modules.vm_manager.subprocess.run')
def test_vm_manager_dry_run(mock_run, mock_vm):
    mock_memory = MagicMock()
    mock_memory.percent = 90.0
    mock_vm.return_value = mock_memory

    result = check_and_scale_compute(dry_run=True, allow_vm_boot=False)

    mock_run.assert_not_called()
    assert result == "DRY_RUN: Would execute az vm start --name OracleV5"

@patch('modules.vm_manager.psutil.virtual_memory')
@patch('modules.vm_manager.subprocess.run')
def test_vm_manager_real_run_not_allowed(mock_run, mock_vm):
    mock_memory = MagicMock()
    mock_memory.percent = 90.0
    mock_vm.return_value = mock_memory

    with pytest.raises(VMBootError):
        check_and_scale_compute(dry_run=False, allow_vm_boot=False)

@patch('modules.vm_manager.psutil.virtual_memory')
@patch('modules.vm_manager.subprocess.run')
def test_vm_manager_real_run_allowed(mock_run, mock_vm):
    mock_memory = MagicMock()
    mock_memory.percent = 90.0
    mock_vm.return_value = mock_memory

    result = check_and_scale_compute(dry_run=False, allow_vm_boot=True)

    mock_run.assert_called_once()
    assert "az" in mock_run.call_args[0][0] and "vm" in mock_run.call_args[0][0]
    assert result == "EXECUTED: az vm start --name OracleV5"

@patch('modules.vm_manager.psutil.virtual_memory')
@patch('modules.vm_manager.subprocess.run')
def test_vm_manager_low_memory(mock_run, mock_vm):
    mock_memory = MagicMock()
    mock_memory.percent = 50.0
    mock_vm.return_value = mock_memory

    result = check_and_scale_compute(dry_run=False, allow_vm_boot=True)

    mock_run.assert_not_called()
    assert result == "Memory at 50.0%, no action needed."
