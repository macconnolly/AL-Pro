#!/bin/bash
# Architectural linter - catches Single Responsibility Principle violations
#
# This script enforces architectural boundaries by detecting:
# - Direct coordinator.data access from consumer layers
# - Private attribute access (coordinator._x) from consumers
# - Incorrect refresh patterns in configuration entities
#
# Run after implementing ANY feature to verify architectural consistency.

set -e

echo "🔍 Architectural Linter - Checking for SRP violations..."
echo ""

VIOLATIONS=0
BASE_DIR="custom_components/adaptive_lighting_pro"

# Check for coordinator.data access in consumer layers
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking for coordinator.data access in platforms/services/integrations..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DATA_ACCESS=$(grep -rn "coordinator\.data\[" \
    "$BASE_DIR/platforms/" \
    "$BASE_DIR/services.py" \
    "$BASE_DIR/integrations/" 2>/dev/null | \
    grep -v "# OK:" || true)

if [ -n "$DATA_ACCESS" ]; then
    echo "❌ VIOLATION: Direct coordinator.data access found:"
    echo ""
    echo "$DATA_ACCESS" | sed 's/^/   /'
    echo ""
    echo "   💡 FIX: Use coordinator.get_X() or set_X() methods instead"
    echo "   Example: coordinator.get_brightness_increment() instead of coordinator.data['global']['brightness_increment']"
    echo ""
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No coordinator.data access violations"
    echo ""
fi

# Check for private attribute access
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking for coordinator private attribute access..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PRIVATE_ACCESS=$(grep -rn "coordinator\._[a-z]" \
    "$BASE_DIR/platforms/" \
    "$BASE_DIR/services.py" \
    "$BASE_DIR/integrations/" 2>/dev/null | \
    grep -v "coordinator\._attr_" | \
    grep -v "# OK:" || true)  # Exclude HA's _attr_ and documented exceptions

if [ -n "$PRIVATE_ACCESS" ]; then
    echo "❌ VIOLATION: Private coordinator attribute access found:"
    echo ""
    echo "$PRIVATE_ACCESS" | sed 's/^/   /'
    echo ""
    echo "   💡 FIX: Add public coordinator method instead"
    echo "   Example: coordinator.set_wake_alarm() instead of coordinator._wake_sequence.set_next_alarm()"
    echo ""
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No private attribute access violations"
    echo ""
fi

# Check for incorrect refresh usage in configuration entities
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking for incorrect refresh patterns in configuration entities..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# This is a warning, not a hard failure
CONFIG_REFRESH=$(grep -B 10 "async_request_refresh" "$BASE_DIR/platforms/number.py" 2>/dev/null | \
    grep -E "class.*(Increment|Timeout)Number" || true)

if [ -n "$CONFIG_REFRESH" ]; then
    echo "⚠️  WARNING: Configuration entities may be using async_request_refresh"
    echo ""
    echo "   Configuration changes (increment, timeout) should use:"
    echo "   - self.coordinator.async_update_listeners() (efficient, no zone recalc)"
    echo ""
    echo "   State changes (brightness_adjustment, wake_alarm) should use:"
    echo "   - await self.coordinator.async_request_refresh() (full recalc)"
    echo ""
else
    echo "✅ Refresh patterns look correct"
    echo ""
fi

# Check for test mocking patterns (look for behavioral tests that should be architectural)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking test patterns..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

BAD_TEST_PATTERN=$(grep -rn "coordinator\.data\[.*\] =" tests/unit/ 2>/dev/null | \
    grep -v "# Test setup" || true)

if [ -n "$BAD_TEST_PATTERN" ]; then
    echo "⚠️  WARNING: Tests may be using behavioral patterns instead of architectural patterns"
    echo ""
    echo "$BAD_TEST_PATTERN" | sed 's/^/   /'
    echo ""
    echo "   💡 RECOMMENDATION: Mock coordinator methods, not data structures"
    echo "   Good: coordinator.set_brightness_increment.assert_called_once_with(20)"
    echo "   Bad:  assert coordinator.data['global']['brightness_increment'] == 20"
    echo ""
else
    echo "✅ Test patterns look good"
    echo ""
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $VIOLATIONS -eq 0 ]; then
    echo "✅ No architectural violations found!"
    echo ""
    echo "Your code respects the Single Responsibility Principle."
    echo "Coordinator API boundaries are properly maintained."
    exit 0
else
    echo "❌ Found $VIOLATIONS violation type(s)"
    echo ""
    echo "Fix these violations before committing."
    echo "See CLAUDE.md 'Architectural Enforcement Rules' section for guidance."
    exit 1
fi
