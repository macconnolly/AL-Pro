# Testing Patterns: Behavioral vs Architectural

## The Problem: Why Did Tests Pass Despite Violations?

Our tests were **behaviorally correct but architecturally wrong**. They verified that features worked (outcome) without verifying that they followed our design patterns (contract).

This gave **false confidence** - green checkmarks despite architectural debt accumulating.

---

## Behavioral Testing (What We Had)

**Philosophy**: "Does it work?"

**Example**:
```python
async def test_set_brightness_increment():
    """Test that brightness increment can be set."""
    coordinator.data["global"]["brightness_increment"] = 10
    entity = ALPBrightnessIncrementNumber(coordinator)

    await entity.async_set_native_value(25)

    assert coordinator.data["global"]["brightness_increment"] == 25  # ✅ PASSES
```

**Why this passed despite architectural violation**:
- The value DID change from 10 to 25
- The test verified the OUTCOME (value changed)
- But it didn't verify the HOW (proper method called)
- Entity could be directly mutating data, and test wouldn't know

**False Security**: This test would still pass even if:
- Entity bypassed all validation
- Entity skipped logging
- Entity violated encapsulation
- Entity created coupling to coordinator internals

---

## Architectural Testing (What We Need)

**Philosophy**: "Does it follow our design?"

**Example**:
```python
async def test_brightness_increment_uses_coordinator_setter():
    """Number entity MUST use coordinator.set_brightness_increment(), not direct mutation.

    This is an ARCHITECTURAL test - it enforces the coordinator API contract.
    If this test fails, it means the entity is violating encapsulation.

    WHY THIS MATTERS:
    - Ensures validation happens in coordinator (centralized)
    - Ensures logging happens (debugging)
    - Prevents coupling to coordinator internals
    - Makes refactoring safe (change coordinator, consumers unaffected)
    """
    coordinator = Mock()
    coordinator.get_brightness_increment.return_value = 20
    entity = ALPBrightnessIncrementNumber(coordinator)

    await entity.async_set_native_value(25)

    # Architectural assertion - FORCES proper implementation
    coordinator.set_brightness_increment.assert_called_once_with(25)
```

**Why this catches violations**:
- If entity directly mutates `coordinator.data`, this method is NEVER called
- Test FAILS immediately
- Developer is forced to implement coordinator method
- Can't take shortcuts and still pass tests

---

## Side-by-Side Comparison

| Aspect | Behavioral Test | Architectural Test |
|--------|-----------------|-------------------|
| **What it tests** | Outcome (value changed) | Contract (method called) |
| **Catches violations?** | ❌ No | ✅ Yes |
| **Enforces patterns?** | ❌ No | ✅ Yes |
| **Allows shortcuts?** | ✅ Yes (bad!) | ❌ No (good!) |
| **When to use** | After architectural test passes | Always, before behavioral |

---

## Pattern 1: Testing Number Entity Setters

### ❌ WRONG (Behavioral Only):
```python
async def test_brightness_increment_entity():
    coordinator.data["global"]["brightness_increment"] = 20
    entity = ALPBrightnessIncrementNumber(coordinator)

    await entity.async_set_native_value(30)

    # Only verifies outcome, not architecture
    assert coordinator.data["global"]["brightness_increment"] == 30
```

**Problem**: Entity could be violating encapsulation and test still passes.

### ✅ RIGHT (Architectural First, Then Behavioral):
```python
async def test_brightness_increment_calls_coordinator_setter():
    """ARCHITECTURAL TEST: Verify entity uses coordinator API."""
    coordinator = Mock()
    entity = ALPBrightnessIncrementNumber(coordinator)

    await entity.async_set_native_value(30)

    # Verify coordinator method was called correctly
    coordinator.set_brightness_increment.assert_called_once_with(30)

async def test_brightness_increment_validation():
    """BEHAVIORAL TEST: Verify business logic works correctly."""
    # Test actual coordinator method to verify clamping, logging, etc.
    coordinator = create_real_coordinator()  # Not mocked

    await coordinator.set_brightness_increment(75)  # Over max (50)

    assert coordinator.get_brightness_increment() == 50  # Clamped
```

**Why this works**:
- Architectural test ensures proper API usage
- Behavioral test ensures business logic correct
- Can't violate architecture and pass tests

---

## Pattern 2: Testing Service Handlers

### ❌ WRONG (Allows Private Access):
```python
async def test_set_wake_alarm_service():
    coordinator._wake_sequence.set_next_alarm = Mock()

    await handle_set_wake_alarm(service_call)

    # Only verifies wake sequence was called
    coordinator._wake_sequence.set_next_alarm.assert_called_once()
```

**Problem**: Test assumes private access is OK, doesn't enforce coordinator API.

### ✅ RIGHT (Enforces Public API):
```python
async def test_set_wake_alarm_uses_coordinator_method():
    """ARCHITECTURAL TEST: Service must use coordinator.set_wake_alarm()."""
    coordinator = Mock()
    coordinator.set_wake_alarm = Mock()

    service_call = Mock()
    service_call.data = {"alarm_time": datetime(2025, 10, 1, 6, 30)}

    await handle_set_wake_alarm(service_call)

    # Verify coordinator public method was called, not private _wake_sequence
    coordinator.set_wake_alarm.assert_called_once()

    # Verify service NEVER accessed private attributes
    assert not hasattr(coordinator, '_wake_sequence') or \
           not coordinator._wake_sequence.set_next_alarm.called
```

**Why this works**: Test fails if service accesses private `_wake_sequence` directly.

---

## Pattern 3: Testing Integrations

### ❌ WRONG (Allows Data Access):
```python
async def test_zen32_brighter_action():
    coordinator.data["global"]["brightness_increment"] = 10
    coordinator.get_brightness_adjustment.return_value = 20

    await zen32._action_brighter()

    # Only verifies service was called
    hass.services.async_call.assert_called_once()
```

**Problem**: Test doesn't verify WHERE increment value came from.

### ✅ RIGHT (Enforces Getter Usage):
```python
async def test_zen32_brighter_uses_coordinator_getter():
    """ARCHITECTURAL TEST: Zen32 must use coordinator.get_brightness_increment()."""
    coordinator = Mock()
    coordinator.get_brightness_adjustment.return_value = 20
    coordinator.get_brightness_increment.return_value = 10

    zen32 = Zen32Integration(hass, coordinator)
    await zen32._action_brighter()

    # Verify getter was called, not data accessed
    coordinator.get_brightness_increment.assert_called_once()

    # Verify service called with correct calculation
    hass.services.async_call.assert_called_once_with(
        DOMAIN, "adjust_brightness", {"value": 30}  # 20 + 10
    )
```

**Why this works**: If Zen32 reads `coordinator.data` instead of calling getter, test fails.

---

## Pattern 4: Testing Coordinator Methods

Coordinator methods should have BOTH types of tests:

### Architectural Test (Contract):
```python
async def test_set_brightness_increment_updates_listeners():
    """ARCHITECTURAL TEST: Config changes must call async_update_listeners, not refresh."""
    coordinator = await create_coordinator()
    coordinator.async_update_listeners = Mock()
    coordinator.async_request_refresh = Mock()

    await coordinator.set_brightness_increment(25)

    # Verify correct update method used
    coordinator.async_update_listeners.assert_called_once()

    # Verify wasteful refresh NOT called
    coordinator.async_request_refresh.assert_not_called()
```

### Behavioral Test (Business Logic):
```python
async def test_set_brightness_increment_clamps_to_range():
    """BEHAVIORAL TEST: Verify clamping logic works correctly."""
    coordinator = await create_coordinator()

    # Test over max (50)
    await coordinator.set_brightness_increment(75)
    assert coordinator.get_brightness_increment() == 50

    # Test under min (5)
    await coordinator.set_brightness_increment(2)
    assert coordinator.get_brightness_increment() == 5

    # Test valid value
    await coordinator.set_brightness_increment(25)
    assert coordinator.get_brightness_increment() == 25
```

---

## Test Development Workflow

1. **Write Architectural Test First**
   - Mock coordinator methods
   - Assert correct method called
   - This test will FAIL initially

2. **Implement Coordinator Method**
   - Add method to coordinator
   - Implement validation, logging
   - Architectural test now PASSES

3. **Write Behavioral Tests**
   - Test business logic (clamping, edge cases)
   - Use real coordinator (not mocked)
   - Verify actual behavior

4. **Implement Consumer Code**
   - Platform/service/integration calls coordinator method
   - Both architectural and behavioral tests PASS

**NEVER skip step 1** - Without architectural tests, violations slip through.

---

## Red Flags in Existing Tests

Search your test files for these patterns - they indicate behavioral-only testing:

### 🚩 Red Flag 1: Direct Data Manipulation
```python
# BAD - test setup mutates data directly
coordinator.data["global"]["brightness_increment"] = 10
```

**Fix**: Mock the getter instead:
```python
# GOOD - test setup mocks coordinator method
coordinator.get_brightness_increment.return_value = 10
```

### 🚩 Red Flag 2: Data Assertion
```python
# BAD - test verifies data changed
assert coordinator.data["global"]["x"] == value
```

**Fix**: Assert method was called:
```python
# GOOD - test verifies method called
coordinator.set_x.assert_called_once_with(value)
```

### 🚩 Red Flag 3: No Method Mocking
```python
# BAD - coordinator not mocked at all
coordinator = Mock()  # Only Mock(), no method mocks
```

**Fix**: Mock the methods being called:
```python
# GOOD - specific methods mocked
coordinator = Mock()
coordinator.get_x.return_value = 10
coordinator.set_x = Mock()
```

---

## Migration Strategy for Existing Tests

If you have behavioral-only tests, don't delete them - **augment** them:

```python
# STEP 1: Add architectural test (new)
async def test_entity_uses_coordinator_method():
    """ARCHITECTURAL: Verify proper API usage."""
    coordinator = Mock()
    # ... architectural assertions ...

# STEP 2: Keep behavioral test (existing, rename)
async def test_entity_business_logic():
    """BEHAVIORAL: Verify feature works correctly."""
    # ... existing test code ...
```

Both tests together provide:
- Architectural test → Prevents violations
- Behavioral test → Ensures correctness

---

## Summary: The Testing Philosophy Shift

| Old Philosophy | New Philosophy |
|---------------|---------------|
| "Does it work?" | "Does it follow our design AND work?" |
| Outcome-focused | Contract-focused first, then outcome |
| False confidence | Real confidence |
| Violations slip through | Violations caught immediately |

**Bottom line**: Architectural tests are not "extra" - they're **essential**. Without them, you're testing the wrong thing.
