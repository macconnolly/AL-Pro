# Migration Runbook: YAML → AL Layer Manager Integration

1. **Preparation**
   - Backup `implementation_1.yaml` and any helper entities.
   - Disable existing YAML automations to avoid double firing.
2. **Install Integration**
   - Copy `custom_components/al_layer_manager` into Home Assistant `config/custom_components`.
   - Restart Home Assistant.
3. **Configuration Flow**
   - Add integration from UI, select zones, bind helpers, and confirm defaults.
   - Review helper validation output; create missing helpers via UI or integration wizard.
4. **Import Defaults**
   - Run `al_layer_manager.import_defaults` service pointing to `tests/fixtures/v7.json` snapshot.
5. **Manual Override Services**
   - Update automations to call `al_layer_manager.start_manual_override` instead of YAML scripts.
6. **Verification**
   - Execute scenario tests (foggy morning, sunset warm boost) using `pytest` markers.
   - Confirm analytics sensors populate and health score ≥ 90.
7. **Rollback**
   - If issues arise, disable integration, re-enable YAML automations, restore helper defaults.
