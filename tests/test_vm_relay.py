from unittest.mock import patch, MagicMock
from modules.vm_relay import send_task_to_vm

def test_send_task_to_vm_success():
    with patch('requests.post') as mock_post:
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "task": "echo 1", "status": "queued"}
        mock_post.return_value = mock_response

        # Act
        result = send_task_to_vm("echo 1", "shell", "test_context")

        # Assert
        assert result == {"ok": True, "task": "echo 1", "status": "queued"}
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json']['task'] == "echo 1"
        assert kwargs['json']['task_type'] == "shell"
        assert kwargs['json']['context'] == "test_context"
        assert 'timestamp' in kwargs['json']

def test_send_task_to_vm_exception():
    with patch('requests.post') as mock_post:
        # Arrange
        mock_post.side_effect = Exception("Connection error")

        # Act
        result = send_task_to_vm("echo 1")

        # Assert
        assert result == {"ok": False, "error": "Connection error"}
        mock_post.assert_called_once()
