# Development Templates for Adaptive Lighting Pro

This document provides **strong prompt templates** that enforce architectural discipline and prevent common violations of the Single Responsibility Principle.

## Why These Templates Matter

When prompting Claude Code, weak prompts allow lazy shortcuts. Strong prompts **force systematic, architecture-first development** that prevents technical debt.

---

## Template 1: Adding a New Feature

### ❌ WEAK PROMPT (allows violations):
> "Add number entities for brightness increment and color temp increment"

**Problem**: Doesn't specify architectural requirements, allows direct data mutation.

### ✅ STRONG PROMPT (enforces architecture):
```
Add number entities for brightness increment and color temp increment.

MANDATORY PROCESS (use sequential thinking):
1. Pattern Analysis: Read existing brightness_adjustment number entity in platforms/number.py and document its pattern
2. Verify it calls coordinator.set_brightness_adjustment() method
3. Check if coordinator.set_brightness_increment() and set_color_temp_increment() exist
4. If not, implement those coordinator methods FIRST with:
   - Validation (clamp to valid ranges)
   - Logging (info level for changes)
   - async_update_listeners() call (config changes don't need full refresh)
5. Then implement number entities that call these coordinator methods
6. Run ./scripts/lint_architecture.sh to verify no violations
7. Compare new entities side-by-side with brightness_adjustment entity to verify pattern match
```

---

## Template 2: Adding a Service Handler

### ❌ WEAK PROMPT (allows violations):
> "Add a service to manually set wake alarms"

**Problem**: Doesn't prevent direct access to coordinator internals.

### ✅ STRONG PROMPT (enforces architecture):
```
Add a service to manually set wake alarms.

ARCHITECTURE-FIRST APPROACH:
1. Before implementing the service handler, design the coordinator API:
   - Method: coordinator.set_wake_alarm(alarm_time: datetime) -> None
   - Validation: Timezone handling, past-alarm rejection
   - Side effects: Triggers coordinator refresh to calculate wake boost
   - Error handling: Raise ValueError for invalid alarms

2. Implement coordinator.set_wake_alarm() method FIRST in coordinator.py
   - Add comprehensive docstring with Args/Returns/Raises
   - Handle naive datetime conversion to timezone-aware
   - Validate alarm is not in past
   - Call internal _wake_sequence.set_next_alarm()
   - Trigger async_request_refresh()
   - Log at INFO level

3. Then implement service handler in services.py that:
   - Calls coordinator.set_wake_alarm() (not coordinator._wake_sequence directly)
   - Catches ValueError for user-friendly error messages
   - Uses coordinator.get_wake_start_time() to log confirmation

4. Run architectural lint to verify no private attribute access

NEVER access coordinator._wake_sequence from services - always use coordinator public methods.
```

---

## Template 3: Adding an Integration

### ❌ WEAK PROMPT (allows violations):
> "Add Zen32 scene controller integration with brighter/dimmer buttons"

**Problem**: Integration might read coordinator.data directly for configuration.

### ✅ STRONG PROMPT (enforces architecture):
```
Add Zen32 scene controller integration with brighter/dimmer buttons.

COORDINATOR API REQUIREMENTS:
Before implementing button actions, verify coordinator has:
- coordinator.get_brightness_adjustment() -> int (current adjustment)
- coordinator.set_brightness_adjustment(value: int) -> None (set new value)
- coordinator.get_brightness_increment() -> int (increment amount)

If get_brightness_increment() doesn't exist, ADD IT FIRST:
```python
def get_brightness_increment(self) -> int:
    """Get configured brightness increment for button actions."""
    return self._brightness_increment
```

THEN implement Zen32 button actions:
- _action_brighter(): Use coordinator.get_brightness_increment(), not coordinator.data
- _action_dimmer(): Use coordinator.get_brightness_increment(), not coordinator.data

Run architectural lint to verify:
- No coordinator.data[...] access in integrations/zen32.py
- No coordinator._private access in integrations/zen32.py
```

---

## Template 4: Refactoring Existing Code

### ❌ WEAK PROMPT (incomplete scope):
> "Fix the architectural violations in number.py"

**Problem**: Doesn't specify the full scope of related changes.

### ✅ STRONG PROMPT (comprehensive):
```
Fix architectural violations where number entities directly mutate coordinator.data.

COMPLETE SCOPE (find all violations first):
1. Grep for violations: grep -rn "coordinator\.data\[" custom_components/adaptive_lighting_pro/platforms/
2. For each violation found, identify:
   - Which entity is violating (e.g., ALPBrightnessIncrementNumber)
   - What value it's setting (e.g., brightness_increment)
   - What the correct coordinator method should be (e.g., set_brightness_increment)

3. For each missing coordinator method:
   - Add getter: coordinator.get_X() -> type
   - Add setter: coordinator.set_X(value: type) -> None with validation
   - Determine if config (use async_update_listeners) or state (use async_request_refresh)
   - Add comprehensive docstrings

4. Update all violating entities to use coordinator methods

5. Update tests to mock coordinator methods, not data:
   - Change: coordinator.data["global"]["x"] = value
   - To: coordinator.get_x.return_value = value (for reads)
   - To: coordinator.set_x.assert_called_once_with(value) (for writes)

6. Run architectural lint to verify all violations fixed

7. Run tests to verify functionality unchanged
```

---

## Template 5: Writing Tests

### ❌ WEAK TEST (behavioral only):
```python
async def test_brightness_increment_entity():
    coordinator.data["global"]["brightness_increment"] = 20
    entity = ALPBrightnessIncrementNumber(coordinator)
    await entity.async_set_native_value(25)
    assert coordinator.data["global"]["brightness_increment"] == 25
```

**Problem**: Tests the outcome (value changed) but not the architecture (method called).

### ✅ STRONG TEST (architectural):
```python
async def test_brightness_increment_uses_coordinator_setter():
    """Number entity MUST use coordinator.set_brightness_increment(), not direct mutation.

    This is an ARCHITECTURAL test - it enforces the coordinator API contract.
    If this test fails, it means the entity is violating encapsulation.
    """
    coordinator = Mock()
    coordinator.get_brightness_increment.return_value = 20
    entity = ALPBrightnessIncrementNumber(coordinator)

    await entity.async_set_native_value(25)

    # Architectural assertion - FORCES proper implementation
    coordinator.set_brightness_increment.assert_called_once_with(25)

    # This would FAIL if entity directly mutates coordinator.data,
    # forcing the developer to implement the coordinator method.
```

**Why this works**: If the entity violates architecture by directly mutating `coordinator.data`, this test will **fail** because `set_brightness_increment` was never called. This forces correct implementation.

---

## Default Template for Any Feature

Use this generic template when adding ANY new feature:

```
[Feature description]

MANDATORY ARCHITECTURE-FIRST PROCESS:

PRE-IMPLEMENTATION:
□ Identify similar existing code and document its pattern
□ Check if required coordinator methods exist
□ If not, design coordinator API signatures

IMPLEMENTATION ORDER (DO NOT REVERSE):
1. Coordinator methods (API layer) - FIRST
   - Add method signatures with comprehensive docstrings
   - Implement validation (clamp for config, raise for logic errors)
   - Add logging at appropriate level
   - Use async_update_listeners() for config, async_request_refresh() for state
   - Write unit tests for coordinator methods

2. Consumer code (platforms/services/integrations) - SECOND
   - Call coordinator methods, NEVER access internals
   - Mock coordinator methods in tests
   - Match pattern of similar existing code

POST-IMPLEMENTATION VERIFICATION:
□ Run ./scripts/lint_architecture.sh → MUST pass
□ Compare new code side-by-side with similar existing code → patterns MUST match
□ Run tests → MUST pass
□ Grep for "coordinator.data[" in new files → MUST return 0 matches
□ Grep for "coordinator._" in new files → MUST return 0 matches (except documented OK cases)

If ANY verification fails, refactor BEFORE proceeding.
```

---

## Anti-Patterns to Explicitly Forbid

When prompting Claude Code, explicitly forbid these patterns:

```
DO NOT:
- Access coordinator.data directly from platforms/services/integrations
- Access coordinator._private_attributes from consumers
- Implement consumers before coordinator API exists
- Write only behavioral tests (must include architectural tests)
- Skip pattern analysis of existing similar code
- Assume tests passing means architecture is correct
- Take shortcuts because "it's faster" - it's NEVER faster in the long run
```

---

## Checklist for Claude Code Sessions

Before starting ANY development session, remind Claude Code:

```
MANDATORY ARCHITECTURAL CHECKLIST:

Before writing code:
□ Read similar existing code FIRST
□ Verify coordinator methods exist
□ Design API before implementation

During implementation:
□ API layer before consumer layer
□ Validate and log in coordinator methods
□ Use correct refresh pattern (listeners vs request_refresh)

After implementation:
□ Run architectural lint
□ Compare to similar existing code
□ Verify tests mock methods, not data
□ Check all TODOs completed

This checklist is NOT optional. Skipping steps creates technical debt.
```

---

## Maturity Levels

**Current State** (after SRP fixes): Reactive - Violations fixed when discovered

**Target State** (with these templates): Preventive - Violations cannot be introduced

Use these templates to reach the preventive state where architectural violations are impossible, not just unlikely.
