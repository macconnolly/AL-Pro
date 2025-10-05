#!/usr/bin/env python3
"""Test script to verify implementation_2.yaml compatibility with current integration.

This validates that all services and entities referenced in implementation_2.yaml
exist in the current Adaptive Lighting Pro integration.
"""

import yaml
import re
import sys
from pathlib import Path


def load_yaml_file(filepath: str) -> dict:
    """Load and parse a YAML file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def extract_service_calls(yaml_content: str) -> set[str]:
    """Extract all service calls from YAML content."""
    # Pattern to match service calls
    pattern = r'service:\s+([a-z_]+\.[a-z_]+)'
    matches = re.findall(pattern, yaml_content, re.MULTILINE)
    return set(matches)


def extract_entity_references(yaml_content: str) -> set[str]:
    """Extract all entity references from YAML content."""
    # Pattern to match entity IDs
    pattern = r'entity_id:\s+([a-z_]+\.[a-z_0-9_]+)'
    matches = re.findall(pattern, yaml_content, re.MULTILINE)
    return set(matches)


def check_integration_services() -> dict[str, bool]:
    """Check if required services exist in the integration."""
    services_yaml_path = Path("custom_components/adaptive_lighting_pro/services.yaml")

    if not services_yaml_path.exists():
        return {}

    services_def = load_yaml_file(services_yaml_path)
    available_services = set()

    for service_name in services_def.keys():
        available_services.add(f"adaptive_lighting_pro.{service_name}")

    return available_services


def main():
    """Main test function."""
    print("Testing implementation_2.yaml compatibility...")
    print("=" * 60)

    # Load implementation_2.yaml content
    impl2_path = Path("implementation_2.yaml")
    if not impl2_path.exists():
        print("ERROR: implementation_2.yaml not found!")
        sys.exit(1)

    with open(impl2_path, 'r') as f:
        impl2_content = f.read()

    # Extract service calls
    service_calls = extract_service_calls(impl2_content)
    alp_services = {s for s in service_calls if s.startswith('adaptive_lighting_pro.')}

    print(f"\nServices used in implementation_2.yaml:")
    for service in sorted(alp_services):
        print(f"  - {service}")

    # Check if services exist
    available_services = check_integration_services()

    print(f"\nServices available in integration:")
    for service in sorted(available_services):
        print(f"  - {service}")

    # Check compatibility
    print(f"\nCompatibility Check:")
    all_compatible = True

    for service in alp_services:
        if service in available_services:
            print(f"  ✅ {service} - EXISTS")
        else:
            print(f"  ❌ {service} - MISSING")
            all_compatible = False

    # Extract entity references
    entity_refs = extract_entity_references(impl2_content)
    alp_entities = {e for e in entity_refs if e.startswith('button.alp_')}

    print(f"\nButton entities used in implementation_2.yaml:")
    for entity in sorted(alp_entities):
        print(f"  - {entity}")

    # Check button entities
    button_py_path = Path("custom_components/adaptive_lighting_pro/button.py")
    if button_py_path.exists():
        with open(button_py_path, 'r') as f:
            button_content = f.read()

        expected_buttons = [
            'button.alp_brighter',
            'button.alp_dimmer',
            'button.alp_warmer',
            'button.alp_cooler',
            'button.alp_reset'
        ]

        print(f"\nButton entity compatibility:")
        for button in expected_buttons:
            button_id = button.split('.')[-1].replace('alp_', '')
            if f'"{button_id}"' in button_content or f"'{button_id}'" in button_content:
                print(f"  ✅ {button} - EXISTS")
            else:
                print(f"  ❌ {button} - MISSING")
                all_compatible = False

    # Summary
    print("\n" + "=" * 60)
    if all_compatible:
        print("✅ SUCCESS: implementation_2.yaml is compatible with current integration!")
        print("\nNext steps:")
        print("1. Test the scene scripts manually")
        print("2. Verify light group entities match your actual lights")
        print("3. Enable time-based automations as needed")
    else:
        print("❌ FAILURE: Some services or entities are missing!")
        print("\nRequired fixes:")
        print("1. Implement missing services in services.py")
        print("2. Add missing button entities in button.py")
        print("3. Update services.yaml with service definitions")

    return 0 if all_compatible else 1


if __name__ == "__main__":
    sys.exit(main())