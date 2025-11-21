"""
Sigma Rule Loader

Loads Sigma detection rules from the SigmaHQ repository.
Focuses on Linux/auditd rules for bash command detection.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
import sys


class SigmaRule:
    """Represents a single Sigma detection rule"""

    def __init__(self, rule_data: dict, filepath: str):
        self.filepath = filepath
        self.title = rule_data.get('title', 'Untitled Rule')
        self.id = rule_data.get('id', 'no-id')
        self.status = rule_data.get('status', 'experimental')
        self.description = rule_data.get('description', '')
        self.references = rule_data.get('references', [])
        self.author = rule_data.get('author', 'Unknown')
        self.date = rule_data.get('date', '')
        self.tags = rule_data.get('tags', [])
        self.level = rule_data.get('level', 'medium')
        self.logsource = rule_data.get('logsource', {})
        self.detection = rule_data.get('detection', {})
        self.falsepositives = rule_data.get('falsepositives', [])

    def __repr__(self):
        return f"<SigmaRule: {self.title} ({self.level})>"

    def is_linux_rule(self) -> bool:
        """Check if this rule applies to Linux systems"""
        product = self.logsource.get('product', '').lower()
        category = self.logsource.get('category', '').lower()
        service = self.logsource.get('service', '').lower()

        return (
            product == 'linux' or
            service in ['auditd', 'syslog', 'cron'] or
            category in ['process_creation', 'file_event']
        )

    def get_mitre_tags(self) -> List[str]:
        """Extract MITRE ATT&CK tags from rule"""
        return [tag for tag in self.tags if tag.startswith('attack.')]


class SigmaRuleLoader:
    """Loads and manages Sigma rules from repository"""

    def __init__(self, sigma_repo_path: str = './sigma_repo'):
        self.sigma_repo_path = Path(sigma_repo_path)
        self.rules: List[SigmaRule] = []

    def load_all_linux_rules(self) -> int:
        """
        Load all Linux-relevant Sigma rules from the repository.

        Returns:
            Number of rules loaded
        """
        rules_dir = self.sigma_repo_path / 'rules' / 'linux'

        if not rules_dir.exists():
            print(f"Warning: Sigma rules directory not found: {rules_dir}", file=sys.stderr)
            print(f"Please ensure Sigma repository is cloned to {self.sigma_repo_path}", file=sys.stderr)
            return 0

        # Load rules from all subdirectories
        rule_files = list(rules_dir.rglob('*.yml')) + list(rules_dir.rglob('*.yaml'))

        loaded_count = 0
        for rule_file in rule_files:
            try:
                rule = self._load_rule_file(rule_file)
                if rule and rule.is_linux_rule():
                    self.rules.append(rule)
                    loaded_count += 1
            except Exception as e:
                print(f"Warning: Failed to load rule {rule_file}: {e}", file=sys.stderr)
                continue

        return loaded_count

    def _load_rule_file(self, filepath: Path) -> SigmaRule:
        """Load a single Sigma rule from YAML file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                rule_data = yaml.safe_load(f)

            if not rule_data:
                return None

            return SigmaRule(rule_data, str(filepath))

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in rule file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading rule file: {e}")

    def get_rules_by_level(self, level: str) -> List[SigmaRule]:
        """Get all rules of a specific severity level"""
        return [rule for rule in self.rules if rule.level == level]

    def get_rules_by_category(self, category: str) -> List[SigmaRule]:
        """Get all rules for a specific logsource category"""
        return [rule for rule in self.rules if rule.logsource.get('category') == category]

    def get_auditd_rules(self) -> List[SigmaRule]:
        """Get all auditd-specific rules"""
        return [rule for rule in self.rules if rule.logsource.get('service') == 'auditd']

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        return {
            'total_rules': len(self.rules),
            'by_level': {
                'critical': len(self.get_rules_by_level('critical')),
                'high': len(self.get_rules_by_level('high')),
                'medium': len(self.get_rules_by_level('medium')),
                'low': len(self.get_rules_by_level('low')),
                'informational': len(self.get_rules_by_level('informational')),
            },
            'auditd_rules': len(self.get_auditd_rules()),
            'process_creation_rules': len(self.get_rules_by_category('process_creation')),
            'file_event_rules': len(self.get_rules_by_category('file_event')),
        }


if __name__ == '__main__':
    # Test the loader
    loader = SigmaRuleLoader()
    count = loader.load_all_linux_rules()

    print(f"Loaded {count} Linux Sigma rules")
    print("\nStatistics:")
    stats = loader.get_statistics()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")

    if loader.rules:
        print(f"\nExample rule:")
        rule = loader.rules[0]
        print(f"  Title: {rule.title}")
        print(f"  Level: {rule.level}")
        print(f"  Description: {rule.description}")
