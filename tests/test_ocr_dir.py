# tests/test_ocr_dir.py
import pytest
import os
import yaml
import logging
from unittest.mock import MagicMock
from ocr_dir import load_config, search_dir, parse_args, confirm_pdf_list  # Import your functions

# --- Test load_config ---
def test_load_config_valid(tmp_path):
    """Tests that load_config loads a valid config file."""
    test_config_path = tmp_path / "test_config.yaml"
    test_config_path.write_text(yaml.dump({"test": "value"}))  # Write valid YAML

    config = load_config(str(test_config_path))
    assert config == {"test": "value"}  # Check if the content is as expected

def test_load_config_not_found():
    """Tests that load_config raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")

def test_load_config_invalid_yaml(tmp_path):
    """Tests that load_config handles invalid YAML."""
    test_config_path = tmp_path / "invalid_config.yaml"
    test_config_path.write_text("invalid: yaml: content")  # Invalid YAML syntax

    with pytest.raises(yaml.YAMLError):
        load_config(str(test_config_path))

# --- Test search_dir ---
def test_search_dir_empty(tmp_path, caplog):
    """Tests search_dir with an empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    mock_logger = MagicMock()
    result = search_dir(str(empty_dir), mock_logger)
    assert result == {}  # Ensure the result is an empty dictionary
    mock_logger.info.assert_called_with(f"Begin searching directory: {empty_dir}")
    mock_logger.warning.assert_called_with(f"Directory '{empty_dir}' is empty.")

def test_search_dir_with_pdfs(tmp_path, caplog):
    """Tests search_dir with a directory containing PDF files."""
    test_dir = tmp_path / "test_pdfs"
    test_dir.mkdir()
    (test_dir / "test1.pdf").touch()
    (test_dir / "test2.pdf").touch()
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "test3.pdf").touch()

    class MockLogger:
        def info(self, message):
            logging.info(message)

        def error(self, message):
            logging.error(message)

    mock_logger = MockLogger()

    result = search_dir(str(test_dir), mock_logger)
    assert len(result) == 3
    assert "test1" in result
    assert "test2" in result
    assert "test3" in result
    assert result["test1"]["name"] == "test1"
    assert result["test1"]["ocr_name"] == "test1_ocr"
    assert result["test1"]["sidecar"] == "test1.txt"

# --- Test parse_args ---
def test_parse_args_no_args():
    """Tests parse_args with no command-line arguments."""
    import sys
    original_argv = sys.argv  # Save the original argv
    sys.argv = ["ocr_dir.py"]  # Simulate running the script
    try:
        args = parse_args()
        assert args.config == "config.yaml"
        assert args.profile == "default"
    finally:
        sys.argv = original_argv  # Restore the original argv

def test_parse_args_with_args():
    """Tests parse_args with command-line arguments."""
    import sys
    original_argv = sys.argv  # Save the original argv
    sys.argv = ["ocr_dir.py", "-c", "myconfig.yaml", "-p", "testprofile"]
    try:
        args = parse_args()
        assert args.config == "myconfig.yaml"
        assert args.profile == "testprofile"
    finally:
        sys.argv = original_argv  # Restore the original argv

# --- Test confirm_pdf_list ---
def test_confirm_pdf_list_yes(monkeypatch, caplog):
    """Test confirm_pdf_list when user confirms with 'y'."""
    monkeypatch.setattr('builtins.input', lambda _: 'y')  # Mock input 'y'
    pdf_list = ["file1.pdf", "file2.pdf"]

    logger = logging.getLogger("test_logger")  # Use a real logger
    logger.setLevel(logging.INFO)  # Ensure the logger level is set to capture INFO messages

    result = confirm_pdf_list(pdf_list, logger)

    # Print captured logs for debugging (optional)
    print(caplog.text)

    assert result is True
    assert "Received y from user to continue" in caplog.text


def test_confirm_pdf_list_no(monkeypatch, caplog):
    """Test confirm_pdf_list when user declines with 'n'."""
    monkeypatch.setattr('builtins.input', lambda _: 'n')  # Mock input 'n'
    pdf_list = ["file1.pdf", "file2.pdf"]

    logger = logging.getLogger("test_logger")  # Use a real logger
    logger.setLevel(logging.INFO)  # Ensure the logger level is set to capture INFO messages

    result = confirm_pdf_list(pdf_list, logger)

    # Print captured logs for debugging (optional)
    print(caplog.text)

    assert result is False
    assert "Received n from user to cancel" in caplog.text


def test_confirm_pdf_list_invalid(monkeypatch, caplog):
    """Test confirm_pdf_list when user provides invalid input."""
    monkeypatch.setattr('builtins.input', lambda _: 'invalid')  # Mock invalid input
    pdf_list = ["file1.pdf", "file2.pdf"]

    logger = logging.getLogger("test_logger")  # Use a real logger
    result = confirm_pdf_list(pdf_list, logger)

    assert result is False
    assert "Received invalid user response" in caplog.text