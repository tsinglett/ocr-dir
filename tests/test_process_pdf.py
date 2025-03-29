import pytest
import os
from pathlib import Path
import yaml
from unittest.mock import patch, MagicMock, mock_open
from ocr_dir import process_pdf, load_config  # Import the function
import subprocess  # Import the real subprocess (for the exception)

# --- Helper Functions for Testing ---
def create_test_config(tmp_path, profile="default", config_data=None):
    """Creates a temporary config file for testing."""
    if config_data is None:
        config_data = {
            "profiles": {
                "default": {
                    "output_type": "pdf",
                }
            }
        }
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(yaml.dump(config_data))
    return str(config_path)

def create_test_pdf(tmp_path, filename="test.pdf", content=b"Dummy PDF Content"):
    """Creates a temporary PDF file for testing."""
    pdf_path = tmp_path / filename
    pdf_path.write_bytes(content)
    return str(pdf_path)

# --- Tests for process_pdf ---
def test_process_pdf_profile_not_found(tmp_path, caplog):
    """Tests that process_pdf handles the case where the profile is not found in the config."""
    config_path = create_test_config(tmp_path)
    config = load_config(config_path)
    pdf_dict = {"path": "dummy.pdf", "ocr_path": "dummy_ocr.pdf"}
    mock_logger = MagicMock()

    process_pdf(pdf_dict, config, "nonexistent_profile", mock_logger)
    mock_logger.error.assert_called_once_with(
        "Configuration profile 'nonexistent_profile' not found."
    )

@patch("ocr_dir.subprocess.run")  # Corrected patch target
def test_process_pdf_successful_ocr(mock_subprocess_run, tmp_path, caplog):
    """Tests that process_pdf runs OCRmyPDF successfully."""
    config_path = create_test_config(tmp_path)
    config = load_config(config_path)
    input_pdf_path = create_test_pdf(tmp_path, "input.pdf")
    output_pdf_path = str(tmp_path / "output_ocr.pdf")
    pdf_dict = {"path": input_pdf_path, "ocr_path": output_pdf_path}
    mock_logger = MagicMock()

    # Mock subprocess.run
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout=b"OCR Success", stderr=b""
    )

    process_pdf(pdf_dict, config, "default", mock_logger)

    # Assert subprocess.run was called with the correct arguments
    expected_command = [
        'docker', 'run', '--rm', '-i', '--user', '1000:1000', '--workdir', '/data',
        '-v', f'{Path("data").parent.resolve()}:/data', 'jbarlow83/ocrmypdf-alpine',
        '--output-type', 'pdf', '-', '-'
    ]
    mock_subprocess_run.assert_called_once()
    actual_command = mock_subprocess_run.call_args[0][0]  # Get the first argument
    assert actual_command == expected_command

    # Assert logging
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count >= 1  # Should be called at least once

@patch("ocr_dir.subprocess.run")  # Corrected patch target
def test_process_pdf_file_not_found_error(mock_subprocess_run, tmp_path, caplog):
    """Tests that process_pdf handles FileNotFoundError."""
    config_path = create_test_config(tmp_path)
    config = load_config(config_path)
    pdf_dict = {"path": "nonexistent.pdf", "ocr_path": "output.pdf"}
    mock_logger = MagicMock()

    process_pdf(pdf_dict, config, "default", mock_logger)

    mock_logger.error.assert_called_once_with("Input file not found: nonexistent.pdf")

@patch("ocr_dir.subprocess.run")  # Corrected patch target
def test_process_pdf_called_process_error(mock_subprocess_run, tmp_path, caplog):
    """Tests that process_pdf handles CalledProcessError."""
    config_path = create_test_config(tmp_path)
    config = load_config(config_path)
    input_pdf_path = create_test_pdf(tmp_path, "input.pdf")
    output_pdf_path = str(tmp_path / "output_ocr.pdf")
    pdf_dict = {"path": input_pdf_path, "ocr_path": output_pdf_path}
    mock_logger = MagicMock()

    # Mock subprocess.run to raise CalledProcessError
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="ocr_cmd", stderr="OCR failed"
    )

    process_pdf(pdf_dict, config, "default", mock_logger)

    mock_logger.error.assert_called_once()
    assert "OCR process failed for" in mock_logger.error.call_args[0][0]