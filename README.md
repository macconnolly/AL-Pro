# Adaptive Lighting Pro (ALP)

**A first-class Home Assistant custom integration for sophisticated adaptive lighting control**

---

## 🚀 Project Status

**Phase**: Planning Complete ✅
**Status**: Ready for Phase 1 Implementation
**Version**: Planning v1.0
**Last Updated**: 2025-10-01

---

## 📋 Quick Start for Developers

### Documentation Structure

This project uses a **single source of truth** approach:

1. **[claude.md](claude.md)** - **START HERE** 🔥
   - **THE** authoritative project context
   - Architecture decisions and patterns
   - Critical implementation details
   - AI assistant guidelines
   - **Read this first before any implementation**

2. **[PROJECT_PLAN.md](PROJECT_PLAN.md)**
   - 8-phase implementation strategy
   - Detailed architecture breakdown
   - Data models and schemas
   - Testing strategy

3. **[TODO.md](TODO.md)**
   - 128 implementation tasks
   - Phase-by-phase checklist
   - Progress tracking

4. **[implementation_1.yaml](implementation_1.yaml)**
   - Original YAML package (3,216 lines)
   - Source of truth for feature behavior
   - Logic to be ported

### Implementation Workflow

```bash
# 1. Read the context
cat claude.md          # Understand the mission and architecture

# 2. Check the plan
cat PROJECT_PLAN.md    # Review phase you're working on

# 3. Find your task
cat TODO.md            # Identify next unchecked task

# 4. Reference source
# When porting logic, cite line numbers from implementation_1.yaml
# Example: "Porting asymmetric boundary logic from implementation_1.yaml:1845-1881"

# 5. Implement with discipline
# - Follow naming conventions in claude.md
# - Write tests alongside code
# - Update TODO.md when complete
```

---

## 🎯 Project Mission

Transform a 3,200-line YAML package into a production-grade Home Assistant custom integration that:

1. ✅ Preserves 100% of original functionality
2. ✅ Fixes all identified bugs and dead code
3. ✅ Adds high-value features (config flow, migration tool, diagnostics)
4. ✅ Provides superior UX through native HA patterns
5. ✅ Enables extensibility through services and blueprints

---

## 🏗️ Architecture at a Glance

### Coordinator-Centric Design
- **Single DataUpdateCoordinator** as source of truth
- All entities are views into coordinator state
- 30-second polling interval
- Event-driven updates for real-time feedback

### Key Modules
- `coordinator.py` - Central orchestration engine
- `adjustment_engine.py` - Asymmetric boundary logic (critical!)
- `zone_manager.py` - Per-zone state and timers
- `mode_controller.py` - 8 home mode profiles
- `environmental.py` - Lux/weather/sunset processing

### Platform Support
- **Switch**: Zone switches, global pause
- **Number**: Brightness/warmth adjustments
- **Select**: Home modes, lighting scenes
- **Sensor**: Status, analytics, monitoring
- **Button**: Quick actions (brighter, dimmer, reset)
- **Light**: Virtual zone groups

---

## 📊 Implementation Phases

| Phase | Focus | Duration | Tasks |
|-------|-------|----------|-------|
| 1 | Foundation | Week 1 | 14 |
| 2 | Core Engine | Week 1-2 | 18 |
| 3 | Environmental | Week 2 | 12 |
| 4 | Modes | Week 2-3 | 15 |
| 5 | Monitoring | Week 3 | 16 |
| 6 | Integrations | Week 3-4 | 19 |
| 7 | High-Value Adds | Week 4 | 14 |
| 8 | Polish & Docs | Week 4-5 | 20 |
| **Total** | | **4-5 weeks** | **128** |

---

## 🔑 Core Features

### Multi-Zone Lighting (5 Zones)
- Independent brightness/color temp ranges per zone
- Per-zone manual control timers
- Configurable via UI (no YAML editing)

### Manual Override System
- Fixed increment controls (±20% brightness, ±500K color temp)
- **Asymmetric boundary logic** (patent-worthy innovation):
  - Positive brightness adjustments → raise minimum only
  - Negative brightness adjustments → lower maximum only
  - Prevents min/max crossover

### Environmental Adaptation
- Lux-based brightness boost (logarithmic curve)
- Weather-aware adjustments (13 conditions)
- Seasonal modifiers
- Pre-sunset progressive dimming

### Home Modes (8 Modes)
- Default, Work, Late Night, Movie
- Bright Focus, Dim Relax, Warm Evening, Cool Energy
- Mode-specific boundary overrides
- Automatic timer management

### Physical Control
- **Zen32 Scene Controller** integration
- **Sonos Alarm** sunrise synchronization
- **4 Lighting Scenes** with one-button activation

### Comprehensive Monitoring
- 18+ sensors for status and analytics
- Event-driven real-time updates
- Dashboard-ready attributes

---

## 🐛 Critical Bugs Fixed

From original YAML package:

1. ❌ Removed 400+ lines of dead code (disabled automations)
2. ❌ Fixed entity typo: `light.cradenza_accent`
3. ❌ Fixed duplicate entity reference
4. ❌ Fixed invalid timer reference
5. ❌ Standardized `adapt_delay` values
6. ❌ Centralized zone mapping logic

---

## 🎓 For AI Assistants

If you're an AI assistant working on this project:

**MANDATORY CHECKLIST** before implementing:
- [ ] Read [claude.md](claude.md) in full
- [ ] Review relevant sections of [PROJECT_PLAN.md](PROJECT_PLAN.md)
- [ ] Check [TODO.md](TODO.md) for current phase/task
- [ ] Understand the asymmetric boundary logic (it's critical!)
- [ ] Follow naming conventions: `alp_*` for entities, `adaptive_lighting_pro.*` for services

**Non-Negotiable Rules**:
- ✅ Cite line numbers when referencing YAML
- ✅ Write comprehensive docstrings and type hints
- ✅ Add unit tests for all logic
- ✅ Update [TODO.md](TODO.md) when completing tasks
- ❌ NEVER skip phases or implement out of order
- ❌ NEVER contradict architectural decisions in [claude.md](claude.md)
- ❌ NEVER add undocumented features

---

## 📦 Project Structure

```
/home/mac/dev/HA/
├── README.md                     # This file - project overview
├── claude.md                     # 🔥 SINGLE SOURCE OF TRUTH
├── PROJECT_PLAN.md               # Implementation plan and architecture
├── TODO.md                       # Task tracking (128 tasks)
├── implementation_1.yaml         # Original YAML package (source material)
│
└── custom_components/adaptive_lighting_pro/  # (To be created in Phase 1)
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── config_flow.py
    ├── coordinator.py            # Central engine
    ├── adjustment_engine.py      # Asymmetric boundary logic
    ├── zone_manager.py
    ├── mode_controller.py
    ├── environmental.py
    ├── entity.py
    ├── light.py
    ├── sensor.py
    ├── switch.py
    ├── number.py
    ├── select.py
    ├── button.py
    ├── services.yaml
    ├── services.py
    ├── integrations/
    │   ├── sonos.py
    │   └── zen32.py
    ├── migration.py
    ├── strings.json
    └── translations/
        └── en.json
```

---

## 🚦 Current Status

**✅ Completed**:
- Full analysis of original YAML package (3,216 lines)
- Architecture design and patterns defined
- 8-phase implementation plan created
- 128 tasks identified and organized
- Critical bugs documented
- Entity/service naming conventions established
- Single source of truth documentation structure

**⏭️ Next Action**:
Begin [TODO.md](TODO.md) **Phase 1, Task 1.1**: Create `custom_components/adaptive_lighting_pro/` directory structure

---

## 📖 Documentation Philosophy

This project prioritizes:
1. **Single Source of Truth**: All architectural decisions in [claude.md](claude.md)
2. **Explicit Over Implicit**: No assumptions, everything documented
3. **Traceable**: All ported logic cites YAML line numbers
4. **AI-Friendly**: Structured for AI assistant consumption
5. **Human-Readable**: Clear prose, not just bullet points

---

## 🤝 Contributing

**For Human Contributors**:
- Read [claude.md](claude.md) for project philosophy
- Follow [PROJECT_PLAN.md](PROJECT_PLAN.md) phase sequence
- Update [TODO.md](TODO.md) when completing tasks
- Write tests alongside code
- Document the "why", not just the "what"

**For AI Assistants**:
- See enforcement rules in [claude.md](claude.md) § "Single Source of Truth - Enforcement"
- Always cite source material with line numbers
- Ask before deviating from architecture
- Update documentation when discovering new details

---

## 📄 License

(To be determined - likely MIT or Apache 2.0 for HA custom integrations)

---

## 🙏 Acknowledgments

- **Original YAML Package**: Enhanced Adaptive Lighting Controls v4.5 (author TBD)
- **Home Assistant Adaptive Lighting Integration**: Basnijenhuis
- **Home Assistant Core**: The foundation we build upon

---

**Ready to build something great? Start with [claude.md](claude.md) →**
