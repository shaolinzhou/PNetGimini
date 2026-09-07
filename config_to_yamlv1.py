import os
import sys
import yaml
import logging
from pathlib import Path

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_config_file(file_path: Path) -> list:
    """
    Parses a Cisco configuration file to extract a list of clean command strings.
    
    Args:
        file_path (Path): The path to the configuration file.
    
    Returns:
        list: A list of clean, runnable command strings.
    """
    commands_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Filter out non-command lines and comments
        for line in lines:
            stripped_line = line.strip()
            # Ignore comments, empty lines, and specific header/footer lines from Packet Tracer
            if stripped_line and not stripped_line.startswith('!') and not stripped_line.startswith('Building') and not stripped_line.startswith('Current'):
                commands_list.append(stripped_line)
            
    except FileNotFoundError:
        logging.error(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        logging.error(f"An error occurred while parsing '{file_path}': {e}")
        
    return commands_list

def main():
    """
    Main function to convert .config files to a single YAML file.
    """
    logging.info("Starting configuration to YAML conversion tool.")
    
    # Define default directories
    BASE_DIR = Path(__file__).resolve().parent
    CONFIGS_DIR = BASE_DIR / "configs"
    
    # Check for user-specified input files or use the default directory
    input_files = sys.argv[1:]
    
    if not input_files:
        logging.info(f"No files specified. Looking for .config files in '{CONFIGS_DIR}'.")
        try:
            input_files = [f for f in CONFIGS_DIR.glob('*.config') if f.is_file()]
        except FileNotFoundError:
            logging.error(f"Error: The default directory '{CONFIGS_DIR}' does not exist.")
            sys.exit(1)
        
        if not input_files:
            logging.warning("No .config files found. Exiting.")
            sys.exit(0)
    else:
        # Resolve user-specified paths relative to the current directory
        # This also correctly handles the case where the user provides the output file name as an argument
        # It's a bit clunky, but necessary for the current design. We check for a .yaml extension and filter it out.
        valid_input_files = []
        for f in input_files:
            if not f.endswith('.yaml'):
                valid_input_files.append(Path(f))
            else:
                logging.warning(f"Ignoring output filename argument: '{f}'. Please enter the output filename when prompted.")
        input_files = valid_input_files
        
    output_filename = input("Enter the desired output YAML filename (e.g., devices.yaml), or press Enter to use 'devices.yaml': ")
    if not output_filename:
        output_filename = "devices.yaml"
    if not output_filename.endswith('.yaml'):
        output_filename += '.yaml'
        
    output_yaml_path = CONFIGS_DIR / output_filename
    
    all_devices = []
    
    for file_path in input_files:
        if not file_path.is_file():
            logging.warning(f"Skipping non-existent file: {file_path}")
            continue
            
        logging.info(f"Processing configuration file: {file_path}")
        config_commands = parse_config_file(file_path)
        
        # Create the device entry with the correct structure and placeholders
        device_entry = {
            'ip': '1.1.1.1',
            'port': 23,
            'username': 'admin',
            'password': 'admin',
            'device_type': 'cisco_ios_telnet',
            'commands': {
                'config': config_commands,
                'show': []  # Explicitly adding the empty show list
            }
        }
        
        all_devices.append(device_entry)
        
    if all_devices:
        final_yaml_data = {'devices': all_devices}

        # We use a custom dumper to ensure proper indentation and quotes.
        class MyDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(MyDumper, self).increase_indent(flow, False)
        
        def represent_str_with_quotes(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
        
        yaml.add_representer(str, represent_str_with_quotes)

        # Dump the data to the file
        with open(output_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(final_yaml_data, f, Dumper=MyDumper, sort_keys=False, indent=2)

        logging.info(f"Successfully created a single YAML file: {output_yaml_path}")
    else:
        logging.warning("No valid configuration files were processed. YAML file was not created.")

if __name__ == "__main__":
    main()
