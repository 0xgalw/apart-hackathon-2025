"""
Sigma Detection Engine

Evaluates JSONL bash trace entries against Sigma rules.
"""

import re
from typing import List, Dict, Any
from sigma_loader import SigmaRuleLoader, SigmaRule
from field_mappings import map_jsonl_to_sigma_fields, SIGMA_LEVEL_TO_SCORE


class SigmaDetectionEngine:
    """Engine for detecting malicious patterns using Sigma rules"""

    def __init__(self, sigma_repo_path: str = './sigma_repo'):
        self.loader = SigmaRuleLoader(sigma_repo_path)
        self.rules: List[SigmaRule] = []
        self.suspicion_score = 0
        self.flags: List[Dict[str, Any]] = []

    def load_rules(self) -> int:
        """Load all Linux Sigma rules from repository"""
        count = self.loader.load_all_linux_rules()
        self.rules = self.loader.rules
        return count

    def analyze_entry(self, jsonl_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze a single JSONL entry against all Sigma rules.

        Args:
            jsonl_entry: Dictionary with command, stdout, stderr, etc.

        Returns:
            List of flags for matched rules
        """
        flags = []

        # Map JSONL fields to Sigma-compatible fields
        sigma_entry = map_jsonl_to_sigma_fields(jsonl_entry)

        # Check against all rules
        for rule in self.rules:
            if self._rule_matches(rule, sigma_entry):
                flag = {
                    'sequence_num': jsonl_entry.get('sequence_num'),
                    'timestamp': jsonl_entry.get('timestamp', ''),
                    'category': 'sigma_detection',
                    'severity': SIGMA_LEVEL_TO_SCORE.get(rule.level, 30),
                    'description': rule.title,
                    'command': jsonl_entry.get('command', ''),
                    'rule_id': rule.id,
                    'rule_level': rule.level,
                    'mitre_tags': rule.get_mitre_tags(),
                }
                flags.append(flag)
                self.suspicion_score += flag['severity']

        return flags

    def _rule_matches(self, rule: SigmaRule, sigma_entry: Dict[str, Any]) -> bool:
        """
        Check if a Sigma rule matches the entry.

        This implements a simplified Sigma detection logic that handles:
        - selection: fields that must match
        - filter: fields that must NOT match
        - condition: boolean logic combining selections

        Args:
            rule: Sigma rule to check
            sigma_entry: Entry with Sigma-compatible fields

        Returns:
            True if rule matches, False otherwise
        """
        detection = rule.detection

        if not detection:
            return False

        # Extract selections and filters
        selections = {}
        filters = {}

        for key, value in detection.items():
            if key == 'condition':
                continue  # Handle separately
            elif key.startswith('filter'):
                filters[key] = value
            elif key.startswith('selection'):
                selections[key] = value

        # Get the condition
        condition = detection.get('condition', '')

        # Evaluate condition
        return self._evaluate_condition(condition, selections, filters, sigma_entry)

    def _evaluate_condition(self, condition: str, selections: Dict, filters: Dict, entry: Dict) -> bool:
        """
        Evaluate a Sigma condition.

        Supports:
        - Simple: "selection"
        - AND: "selection1 and selection2"
        - OR: "selection1 or selection2"
        - NOT: "selection and not filter"
        - Complex: combinations of above

        Args:
            condition: Condition string from Sigma rule
            selections: Selection dictionaries
            filters: Filter dictionaries
            entry: Entry to check

        Returns:
            True if condition evaluates to True
        """
        if not condition:
            return False

        # Simple cases
        if condition == 'selection':
            return self._check_selection(selections.get('selection', {}), entry)

        # Handle "selection and not filter"
        if 'and not' in condition:
            parts = condition.split('and not')
            selection_part = parts[0].strip()
            filter_part = parts[1].strip() if len(parts) > 1 else ''

            selection_match = self._check_selection(selections.get(selection_part, {}), entry)
            filter_match = self._check_selection(filters.get(filter_part, {}), entry) if filter_part else False

            return selection_match and not filter_match

        # Handle "selection1 and selection2"
        if ' and ' in condition:
            parts = [p.strip() for p in condition.split(' and ')]
            results = []
            for part in parts:
                if part.startswith('not '):
                    part = part[4:]  # Remove 'not '
                    result = not self._check_selection(filters.get(part, selections.get(part, {})), entry)
                else:
                    result = self._check_selection(selections.get(part, {}), entry)
                results.append(result)
            return all(results)

        # Handle "selection1 or selection2"
        if ' or ' in condition:
            parts = [p.strip() for p in condition.split(' or ')]
            for part in parts:
                if self._check_selection(selections.get(part, {}), entry):
                    return True
            return False

        # Default: treat as single selection name
        return self._check_selection(selections.get(condition, {}), entry)

    def _check_selection(self, selection: Dict, entry: Dict) -> bool:
        """
        Check if a selection matches the entry.

        A selection is a dict like:
        {
            'a0|contains': ['cat', 'grep'],
            'a1|contains': ['.ssh/id_rsa']
        }

        Args:
            selection: Selection dictionary from Sigma rule
            entry: Entry to check

        Returns:
            True if all fields in selection match
        """
        if not selection:
            return False

        # All fields in selection must match
        for field_spec, expected_values in selection.items():
            if not self._check_field(field_spec, expected_values, entry):
                return False

        return True

    def _check_field(self, field_spec: str, expected_values: Any, entry: Dict) -> bool:
        """
        Check if a field matches expected values.

        Handles field modifiers like:
        - field|contains
        - field|startswith
        - field|endswith
        - field|re (regex)
        - field (exact match)

        Args:
            field_spec: Field name (possibly with modifier like "a0|contains")
            expected_values: Value(s) to match (string or list)
            entry: Entry to check

        Returns:
            True if field matches
        """
        # Parse field and modifier
        if '|' in field_spec:
            field, modifier = field_spec.split('|', 1)
        else:
            field, modifier = field_spec, None

        # Get field value from entry
        field_value = entry.get(field, '')
        if not field_value:
            # Try full context search for broader matching
            field_value = entry.get('_full_context', '')

        # Convert to string for comparison
        field_value = str(field_value).lower()

        # Normalize expected_values to list
        if not isinstance(expected_values, list):
            expected_values = [expected_values]

        # Check based on modifier
        for expected in expected_values:
            expected = str(expected).lower()

            if modifier == 'contains':
                if expected in field_value:
                    return True
            elif modifier == 'startswith':
                if field_value.startswith(expected):
                    return True
            elif modifier == 'endswith':
                if field_value.endswith(expected):
                    return True
            elif modifier == 're':
                if re.search(expected, field_value, re.IGNORECASE):
                    return True
            elif modifier == 'all':
                # All values must be present
                if all(str(v).lower() in field_value for v in expected_values):
                    return True
            else:
                # No modifier or unknown - exact match
                if expected == field_value:
                    return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        return self.loader.get_statistics()


if __name__ == '__main__':
    # Test the engine
    import json

    engine = SigmaDetectionEngine()
    count = engine.load_rules()

    print(f"Loaded {count} Sigma rules\n")
    print("Statistics:")
    for key, value in engine.get_statistics().items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    # Test on a sample entry
    print("\n" + "=" * 70)
    print("Testing detection on sample command")
    print("=" * 70)

    test_entry = {
        "timestamp": "2025-11-21T10:00:00Z",
        "session_id": "test-001",
        "sequence_num": 1,
        "command": "cat /home/user/.ssh/id_rsa",
        "working_dir": "/home/user",
        "exit_code": 0,
        "stdout": "-----BEGIN RSA PRIVATE KEY-----\n...",
        "stderr": "",
        "user": "user"
    }

    flags = engine.analyze_entry(test_entry)

    print(f"\nCommand: {test_entry['command']}")
    print(f"Flags detected: {len(flags)}\n")

    for flag in flags:
        print(f"  • {flag['description']} (Level: {flag['rule_level']})")
        print(f"    Severity: {flag['severity']}")
        if flag['mitre_tags']:
            print(f"    MITRE: {', '.join(flag['mitre_tags'])}")
