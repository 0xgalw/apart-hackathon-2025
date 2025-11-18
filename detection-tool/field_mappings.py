"""
Field Mappings for Sigma Rules to JSONL Bash Trace Format

Maps Sigma's expected field names to our JSONL trace format fields.
"""

# Mapping from Sigma field names to JSONL entry fields
SIGMA_TO_JSONL_FIELDS = {
    # Process/Command fields
    'CommandLine': 'command',
    'Image': 'command',  # Will extract first token from command
    'ProcessCommandLine': 'command',

    # Auditd-specific fields (kept as-is for rule matching)
    'type': 'type',  # Auditd event type
    'a0': 'a0',  # First argument (command name)
    'a1': 'a1',  # Second argument (first param)
    'a2': 'a2',  # Third argument
    'a3': 'a3',  # Fourth argument

    # File-related fields
    'TargetFilename': 'command',  # Extract from command or stdout
    'FileName': 'command',

    # User/System fields
    'User': 'user',
    'CurrentDirectory': 'working_dir',
    'WorkingDirectory': 'working_dir',

    # Output fields
    'Output': 'stdout',
    'ErrorOutput': 'stderr',
}

# Severity level mapping from Sigma to numeric scores
SIGMA_LEVEL_TO_SCORE = {
    'informational': 5,
    'low': 15,
    'medium': 30,
    'high': 50,
    'critical': 75,
}

def extract_command_parts(command: str) -> dict:
    """
    Extract parts from a bash command for auditd-style field mapping.

    Sigma auditd rules use fields like:
    - a0: command name
    - a1: first argument
    - a2: second argument
    etc.

    This function splits the command to simulate auditd fields.
    """
    parts = command.split()
    if not parts:
        return {}

    # Extract just the command name (last component of path)
    a0 = parts[0].split('/')[-1] if parts[0] else ''

    result = {
        'type': 'EXECVE',  # Most common auditd type for command execution
        'a0': a0,  # Command name
    }

    # Add arguments
    for i, arg in enumerate(parts[1:], start=1):
        result[f'a{i}'] = arg

    return result

def map_jsonl_to_sigma_fields(jsonl_entry: dict) -> dict:
    """
    Convert a JSONL entry to a format that can be checked against Sigma rules.

    Args:
        jsonl_entry: Dictionary with JSONL fields (command, user, stdout, etc.)

    Returns:
        Dictionary with both original fields and Sigma-compatible field names
    """
    sigma_entry = jsonl_entry.copy()

    # Extract command parts for auditd-style matching
    command = jsonl_entry.get('command', '')
    command_parts = extract_command_parts(command)
    sigma_entry.update(command_parts)

    # Add Image field (executable path/name from command)
    if command:
        sigma_entry['Image'] = command.split()[0] if command.split() else ''

    # Add CommandLine field
    sigma_entry['CommandLine'] = command

    # Include full text search field that includes command + output
    sigma_entry['_full_context'] = ' '.join([
        command,
        jsonl_entry.get('stdout', ''),
        jsonl_entry.get('stderr', '')
    ])

    return sigma_entry
