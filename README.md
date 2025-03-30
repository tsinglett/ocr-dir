# OCR Directory Processor

This Python script (`ocr_dir.py`) provides a command-line tool for batch OCR processing of PDF files within a specified directory. It uses the OCRmyPDF Docker image to perform the OCR and is configured using a YAML file (`config.yaml`).

## Features

* **Batch Processing:** Recursively searches a directory for PDF files and processes them.
* **Configuration Profiles:** Supports different OCR processing profiles defined in the configuration file.

## Requirements

* Python 3.x
* Docker
* OCRmyPDF Docker image (`jbarlow83/ocrmypdf-alpine`)
* `pdftotext` (optional, for testing output)
* PyYAML (`pip install PyYAML`)
* tqdm (`pip install tqdm`)

## Installation

1.  Clone the repository:

    ```bash
    git clone <your_repository_url>
    cd <your_repository_directory>
    ```

2.  Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

```bash
python ocr_dir.py [-c CONFIG] [-p PROFILE]
    -c CONFIG, --config CONFIG:  Path to the YAML configuration file (default: config.yaml).

    -p PROFILE, --profile PROFILE:  Configuration profile to use (default: default).
```

## Configuration

The script uses a YAML file (config.yaml) to manage its settings.  Below is an overview of the available configuration options:
## config.yaml Overview

### Logging

- **level:** The base logging level for the application. Possible values: `debug`, `info`, `warning`, `error`, `critical`.
- **log_file:** The path to the file where logs should be written. If left empty, logs are not written to a file.
- **print_level:** The logging level for output to the console. Uses the same possible values as `level`.

### Input Directory

- **input_dir:** The directory that the script will recursively search for PDF files to process.

### Profiles

This section defines different OCR processing profiles. Each profile is a dictionary of OCRmyPDF options.

- **default:** A basic profile that outputs a standard PDF.
  - **output_type:** The output type for OCRmyPDF (`pdf`, `pdfa`, etc.).

- **detailed:** A profile with all options listed, not for normal use.
  - **language:** The language used for OCR (e.g., `eng` for English).
  - **output_type:** The output type for OCRmyPDF.
  - **force_ocr:** Force OCR even if the file is already an OCR PDF.
  - **deskew:** Deskew the document (may increase file size).
  - **clean:** Clean the document (doesn't apply edits to the final PDF).
  - **clean_final:** Clean the document and apply edits to the final PDF.
  - **rotate_pages:** Automatically rotate pages based on detected orientation.
  - **rotate_pages_threshold:** Confidence threshold for page rotation.
  - **remove_background:** Remove background from the document.
  - **oversample:** Oversample the image for better OCR.
  - **remove_vectors:** Remove vector graphics from the output.
  - **jobs:** Number of CPU cores to use for processing (`0` for all).
  - **pdf_renderer:** PDF renderer to use (`auto`, `hocr`, `sandwich`, `hocrdebug`).

    - **archival:** A profile designed for creating PDF/A compliant documents for archiving.
      - Uses settings optimized for long-term preservation.
    
    - **fast_processing:** A profile that prioritizes speed over quality.
      - Disables some processing steps to improve performance.
    
    - **multilingual:** A profile for processing documents with multiple languages.
      - Specifies multiple languages in the language setting (e.g., `eng+fra+deu`).

### Example config.yaml:
```bash
# Logging configuration
logging:
  level: info
  log_file: 'ocr_dir.log'
  print_level: info

# Input directory for PDF files
input_dir: 'targets'

# Profiles for OCR processing
profiles:
  default:
    output_type: 'pdf'
  detailed:
    language: 'eng'
    output_type: 'pdfa'
    force_ocr: false
    deskew: true
    clean: true
    clean_final: false
    rotate_pages: true
    rotate_pages_threshold: 10.0
    remove_background: false
    oversample: 300
    remove_vectors: false
    jobs: 0
    pdf_renderer: 'auto'
  archival:
    language: 'eng'
    output_type: 'pdfa-3'
    force_ocr: false
    deskew: true
    clean_final: false
    rotate_pages: true
    oversample: 400
    remove_background: false
  fast_processing:
    language: 'eng'
    output_type: 'pdf'
    force_ocr: false
    deskew: false
    clean_final: false
    rotate_pages: false
    jobs: 0
  multilingual:
    language: 'eng+fra+deu'
    output_type: 'pdfa'
    force_ocr: false
    deskew: true
    clean_final: false
```

## Notes

    Ensure that Docker is installed and running, and that the jbarlow83/ocrmypdf-alpine image is available. The script will attempt to pull the image when the Docker container starts.

    The script creates a data directory (if it doesn't exist) in the parent directory of the script and uses it as the working directory for Docker. It is a temporary directory.

    The output OCR'd PDF files are placed in the same directory as the original PDF files, with `_ocr