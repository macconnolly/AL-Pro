# Helper Parity Matrix

| YAML Helper | Integration Entity | Notes |
| --- | --- | --- |
| `input_boolean.office_manual` | `sensor.al_layer_manager_office_manual_active` | Managed via manual intent manager |
| `input_number.office_brightness` | `number.al_layer_manager_office_target_brightness` | Created automatically when missing |
| `input_datetime.office_override_expires` | `sensor.al_layer_manager_office_override_expires` | Mirrors override expiration |
| `input_boolean.sonos_wake_enabled` | `switch.al_layer_manager_sonos_wake` | Covered via Implementation_2 YAML |
| `input_boolean.cloudy_day_boost` | `switch.al_layer_manager_cloudy_day` | Environment manager fallback |
