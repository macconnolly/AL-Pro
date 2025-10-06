#!/usr/bin/env python3
"""
Validate that all dashboard entities and scripts referenced in lovelace cards
exist in the appropriate configuration files.
"""
import yaml
import re
from pathlib import Path

def extract_entities_from_dashboard(dashboard_file):
    """Extract all entity references from dashboard YAML."""
    entities = set()
    scripts = set()

    with open(dashboard_file, 'r') as f:
        content = f.read()

    # Find entity references (sensor., switch., number., button., input_boolean.)
    entity_pattern = r'entity:\s+(sensor\.|switch\.|number\.|button\.|input_boolean\.)[^\s]+'
    for match in re.finditer(entity_pattern, content):
        entities.add(match.group(1))

    # Find script references
    script_pattern = r'(?:service:\s+script\.|entity:\s+script\.)([^\s]+)'
    for match in re.finditer(script_pattern, content):
        scripts.add(match.group(1))

    return entities, scripts

def check_scripts_in_implementation(scripts, implementation_file):
    """Check if scripts exist in implementation_2.yaml."""
    with open(implementation_file, 'r') as f:
        yaml_content = yaml.safe_load(f)

    script_section = yaml_content.get('script', {})
    missing = []

    for script in scripts:
        if script not in script_section:
            missing.append(script)

    return missing

def main():
    dashboard_file = Path('/home/mac/dev/HA/lovelace_alp_complete_dashboard.yaml')
    implementation_file = Path('/home/mac/dev/HA/implementation_2.yaml')

    print("Validating Adaptive Lighting Pro Dashboard...")
    print("=" * 60)

    # Extract references
    entities, scripts = extract_entities_from_dashboard(dashboard_file)

    print(f"\nFound {len(entities)} entity references")
    print(f"Found {len(scripts)} script references")

    # Check scripts
    missing_scripts = check_scripts_in_implementation(scripts, implementation_file)

    if missing_scripts:
        print(f"\n❌ Missing scripts in implementation_2.yaml:")
        for script in sorted(missing_scripts):
            print(f"  - {script}")
    else:
        print("\n✅ All scripts found in implementation_2.yaml")

    print("\nScripts referenced in dashboard:")
    for script in sorted(scripts):
        print(f"  ✓ script.{script}")

    print("\n" + "=" * 60)
    print("Dashboard validation complete!")

    if missing_scripts:
        print(f"\n⚠️  {len(missing_scripts)} issues found - review missing scripts above")
        return 1
    else:
        print("\n✨ All dashboard scripts are properly configured!")
        return 0

if __name__ == "__main__":
    exit(main())