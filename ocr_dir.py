import os
import logging
import time
import yaml
import subprocess
from pathlib import Path
import argparse
from tqdm import tqdm  # For progress bars

# ---- LOAD CONFIG ----
def load_config(config_file="config.yaml"):
    '''
    Loads configuration from a YAML file.

    :param config_file: Path to the YAML configuration file, 
                        Defaults to "config.yaml"
    :type config_file: str, optional
    :return: A dictionary containing the configuration.
    :rtype: dict
    '''    
    try:
        # Check if the provided config_file exists
        if not os.path.isfile(config_file):
            # If not, try looking in the same folder as the program
            script_dir = os.path.dirname(os.path.realpath(__file__))
            config_file = os.path.join(script_dir, config_file)
            if not os.path.isfile(config_file):
                raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

        # Load the configuration file
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        return config

    except FileNotFoundError as e:
        print(f"Error: {e}")
        raise e
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration: {e}")
        raise e

# ---- INIT LOGGING ----
def setup_logging(config):
    '''
    Initializes logging with settings from config.

    :param config: The configuration dictionary.
    :type config: dict
    :return: Returns an initialized logger object.
    :rtype: logging.Logger
    '''    

    log_level = getattr(logging, config['logging']['level'].upper(), logging.INFO)
    log_file = config['logging']['log_file']
    log_format = '%(asctime)s - %(lineno)d - %(levelname)s - %(message)s'
    print_level = getattr(logging, config['logging']['print_level'].upper(), logging.INFO) #Get print level from config
    print_format = '%(levelname)s - %(message)s'

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the base logger level to DEBUG

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Stream handler (outputs to terminal)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(print_level)
    stream_formatter = logging.Formatter(print_format)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    logger.info("Logging initialized")
    return logger

# ---- ARG PARSER ----
def parse_args():
    '''
    Parses user command-line arguments.

    :return: An object containing the parsed arguments.
    :rtype: argparse.Namespace
    '''    

    parser = argparse.ArgumentParser(
        description="Batch OCR processing of PDF files."
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to the YAML configuration file.",
    )
    parser.add_argument(
        "-p",
        "--profile",
        default="default",
        help="Configuration profile to use.",
    )
    return parser.parse_args()

# ---- PDF Processing Functions ----
def search_dir(directory, logger):
    '''
    Recursively search a directory for PDFs, returning a dictionary 
    with the pdf names as keys and a dictionary of file information as values.

    :param directory: The top-level directory to search for PDF files.
    :type directory: str
    :param logger: The logger object for logging messages.
    :type logger: logging.Logger
    :return: A dictionary of dictionaries containing the keys: 
              'name', 'ocr_name', 'sidecar', 'path', and 'ocr_path'.
    :rtype: dict
    '''    
    logger.info(f"Begin searching directory: {directory}")
    pdf_files = {}

    # Check if the directory is empty
    if not any(Path(directory).iterdir()):
        logger.warning(f"Directory '{directory}' is empty.")
        return pdf_files  # Return an empty dictionary

    # Use Path to recursively glob PDFs
    for pdf_path in Path(directory).rglob('*.pdf'):
        logger.info(f"Found PDF: {pdf_path}")

        # Extract file name and create OCR path
        file_name = pdf_path.stem  # Name with no extension
        ocr_file_name = f"{file_name}_ocr"
        ocr_file_path = pdf_path.parent / f"{ocr_file_name}.pdf"
        sidecar_file = f"{file_name}.txt"

        # Add file to pdf_files dictionary
        pdf_files[file_name] = {
            "name": file_name,
            "ocr_name": ocr_file_name,
            "sidecar": sidecar_file,
            "path": pdf_path,
            "ocr_path": ocr_file_path,
        }

    return pdf_files

def confirm_pdf_list(pdf_list, logger):
    '''
    Asks the user to confirm the list of PDF files to be OCR'd
    This function prints the list of PDF files and waits for user input to continue or cancel the operation.

    :param pdf_list: A list containing the full paths of the PDFs
    :type pdf_list: list
    :param logger: The logger object for logging messages
    :type logger: logging.Logger
    :return: True if the user confirms the list, False if they do not
    :rtype: bool
    '''    
    print("The following PDF files will be OCR'd:")
    logger.info("Confirming PDF list")
    for i, pdf_path in enumerate(pdf_list):
        print(f"{i}: {pdf_path}")
    
    while True:
        response = input("Continue? (y/n): ")
        if response.lower() in ('yes', 'y'):
            logger.info(f"Received {response} from user to continue")
            return True
        elif response.lower() in ('no', 'n'):
            logger.info(f"Received {response} from user to cancel")
            return False
        else:
            print("Invalid response. Please enter 'yes' or 'no'.")
            logger.error("Received invalid user response to confirmation prompt")
            return False

def process_pdf(pdf_dict, config, profile, logger):
    '''
    Processes a single PDF file using OCRmyPDF.

    :param pdf_dict: A dictionary containing information about the PDF file.
    :type pdf_dict: dict
    :param config: The configuration dictionary.
    :type config: dict
    :param profile: The configuration profile to use.
    :type profile: str
    :param logger: The logger object for logging messages.
    :type logger: logging.Logger
    '''
    try:
        ocr_config = config['profiles'][profile]
    except KeyError:
        logger.error(f"Configuration profile '{profile}' not found.")
        return
    
    uid = 1000  # TODO - Make UID/GID configurable
    gid = 1000

    working_dir = Path('data').parent.resolve()
    logger.info(f"Working directory: {working_dir}")

    # Base Docker command
    docker_cmd = [
        'docker',
        'run',
        '--rm',
        '-i',
        '--user',
        f'{uid}:{gid}',
        '--workdir',
        '/data',
        '-v',
        f'{working_dir}:/data',  # Fixed volume mapping
        'jbarlow83/ocrmypdf-alpine',
    ]

    # Map config keys to OCRmyPDF arguments
    ocrmypdf_args = {
        'language': lambda value: ['-l', value],
        'output_type': lambda value: ['--output-type', value],
        'force_ocr': lambda value: ['--force-ocr'] if value else [],
        'deskew': lambda value: ['--deskew'] if value else [],
        'clean': lambda value: ['--clean'] if value else [],
        'clean_final': lambda value: ['--clean-final'] if value else [],
        'rotate_pages': lambda value: ['--rotate-pages'] if value else [],
        'rotate_pages_threshold': lambda value: ['--rotate-pages-threshold', str(value)],
        'remove_background': lambda value: ['--remove-background'] if value else [],
        'oversample': lambda value: ['--oversample', str(value)],
        'remove_vectors': lambda value: ['--remove-vectors'] if value else [],
        'jobs': lambda value: ['-j', str(value)] if value > 0 else [],
        'pdf_renderer': lambda value: ['--pdf-renderer', value],
    }

    # Add arguments based on the config
    for key, value in ocr_config.items():
        if key in ocrmypdf_args and value is not None:
            docker_cmd.extend(ocrmypdf_args[key](value))

    # Add input and output file arguments
    docker_cmd.extend(['-', '-'])  # Input and output are passed via stdin and stdout

    logger.info(f"Docker command: {docker_cmd}")
    file_path = str(pdf_dict['path'])
    ocr_path = str(pdf_dict['ocr_path'])

    try:
        with (
            open(file_path, 'rb') as input_file,
            open(ocr_path, 'wb') as output_file,
        ):
            proc = subprocess.run(
                docker_cmd,
                stdin=input_file,
                stdout=output_file,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                errors='ignore',
            )
        logger.info(proc.stderr)
        os.chmod(file_path, 0o664)
        os.chmod(ocr_path, 0o664)

    except FileNotFoundError:
        logger.error(f"Input file not found: {file_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"OCR process failed for {file_path}: {e.stderr}")

# ---- Main Function ----
def main():
    # Parse command-line arguments
    args = parse_args()

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    logger = setup_logging(config)

    # Search for all PDFs under the top level directory
    start_path = os.path.join(os.path.dirname(__file__), config['input_dir'])
    logger.info(f"Searching directory: {start_path}")

    pdf_list = search_dir(start_path, logger)
    logger.info(yaml.dump(pdf_list))

    # Confirm the list of PDFs   
    if confirm_pdf_list(pdf_list, logger):
        logger.info("User confirmed PDF list")

        # Process each PDF with progress bar
        for pdf in tqdm(pdf_list.values(), desc="Processing PDFs"):
            logger.info(f"Processing PDF: {pdf['name']}")
            process_pdf(pdf, config, args.profile, logger)
    else:
        logger.info("User did not confirm PDF list")
   
if __name__ == '__main__':
    main()