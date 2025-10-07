#!/usr/bin/env python3
"""
Comprehensive upload script for Adaptive Lighting Pro integration.
Uploads ALL integration files, YAML configs, and packages to Home Assistant.
"""
import paramiko
import os
import sys
from pathlib import Path

def upload_file(sftp, local_path, remote_path):
    """Upload a single file via SFTP with directory creation."""
    try:
        # Create remote directory structure if needed
        remote_dir = os.path.dirname(remote_path)
        if remote_dir:
            parts = remote_dir.split('/')
            current = ''
            for part in parts:
                if not part:
                    continue
                current += '/' + part
                try:
                    sftp.stat(current)
                except FileNotFoundError:
                    sftp.mkdir(current)
        
        # Upload file
        sftp.put(local_path, remote_path)
        
        # Show relative path for cleaner output
        filename = os.path.basename(local_path)
        print(f"  ✓ {filename}")
        return True
    except Exception as e:
        print(f"  ✗ {local_path}: {e}")
        return False

def main():
    # SSH connection details
    hostname = "10.0.0.21"
    username = "root"
    password = "password"
    
    # Base paths
    base_local = "/home/mac/dev/HA/custom_components/adaptive_lighting_pro"
    base_remote = "/homeassistant/custom_components/adaptive_lighting_pro"
    
    # Integration files (all Python modules and manifest)
    integration_files = [
        # Root level
        "__init__.py",
        "adjustment_engine.py",
        "button.py",
        "config_flow.py",
        "const.py",
        "coordinator.py",
        "entity.py",
        "number.py",
        "select.py",
        "sensor.py",
        "services.py",
        "switch.py",
        "manifest.json",
        # Features subdirectory
        "features/__init__.py",
        "features/environmental.py",
        "features/manual_control.py",
        "features/sunset_boost.py",
        "features/wake_sequence.py",
        "features/zone_manager.py",
        # Integrations subdirectory
        "integrations/__init__.py",
        "integrations/sonos.py",
        "integrations/zen32.py",
    ]
    
    # YAML configuration files
    yaml_files = [
        (
            "/home/mac/dev/HA/implementation_2.yaml",
            "/homeassistant/packages/implementation_2.yaml"
        ),
        (
            "/home/mac/dev/HA/adaptive_lighting_pro_zones.yaml",
            "/homeassistant/adaptive_lighting_pro_zones.yaml"
        ),
    ]
    
    print("="*70)
    print("ADAPTIVE LIGHTING PRO - COMPREHENSIVE UPLOAD")
    print("="*70)
    print(f"\nConnecting to {hostname}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("✓ Connected successfully\n")
        
        sftp = ssh.open_sftp()
        
        success_count = 0
        total_count = 0
        
        # Upload integration files
        print(f"{'Integration Files':<50} ({len(integration_files)} files)")
        print("-" * 70)
        for rel_path in integration_files:
            local_path = os.path.join(base_local, rel_path)
            remote_path = os.path.join(base_remote, rel_path)
            total_count += 1
            if upload_file(sftp, local_path, remote_path):
                success_count += 1
        
        # Upload YAML configs
        print(f"\n{'YAML Configuration Files':<50} ({len(yaml_files)} files)")
        print("-" * 70)
        for local_path, remote_path in yaml_files:
            total_count += 1
            if upload_file(sftp, local_path, remote_path):
                success_count += 1

        # Note: NOT closing SFTP/SSH to avoid killing SSH daemon

        print("\n" + "="*70)
        print(f"UPLOAD COMPLETE: {success_count}/{total_count} files uploaded")
        print("="*70)
        
        # Clean Python cache
        print("\nCleaning Python cache...")
        stdin, stdout, stderr = ssh.exec_command(
            "rm -rf /homeassistant/custom_components/adaptive_lighting_pro/__pycache__ "
            "/homeassistant/custom_components/adaptive_lighting_pro/features/__pycache__ "
            "/homeassistant/custom_components/adaptive_lighting_pro/integrations/__pycache__"
        )
        stdout.channel.recv_exit_status()
        print("✓ Cache cleaned")
        
        print("\n" + "="*70)
        print("CRITICAL FIXES APPLIED")
        print("="*70)
        print("\n1. Timer State Restoration (zone_manager.py)")
        print("   ✓ Restore zone state from active timer entities on startup")
        print("   ✓ Handle case where hass.data lost but timers restored")
        print("\n2. Coordinator Key Mismatches (coordinator.py)")
        print("   ✓ Fixed timer_remaining_seconds → timer_remaining")
        print("   ✓ Added timer_finishes_at to zone state")
        print("\n3. Zen32 Config Import (config_flow.py)")
        print("   ✓ Import zen32_button_entities from YAML")
        print("   ✓ Import zen32_button_actions from YAML")
        print("\n4. Sonos Integration")
        print("   ✓ Already handles earliest_alarm_timestamp attribute")
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print("\n1. Restart Home Assistant")
        print("2. Verify timer sensors show correct remaining time")
        print("3. Test Zen32 button presses (if configured)")
        print("4. Test Sonos alarm detection (if configured)")
        print("5. Verify environmental boost calculates correctly")
        print("6. Test all scenes work")
        print("\n" + "="*70)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Connection Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
