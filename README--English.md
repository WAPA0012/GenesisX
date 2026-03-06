# Genesis X - Digital Life System

> **Project Vision**: Based on current human technological reserves, create an engineering-viable digital life—possessing autonomous thinking, exploration, and decision-making capabilities, along with unique personality traits.

**Version**: v1.3.0 (Code Review Complete)
**Release Date**: 2026-03-04
**Status**: Production Ready

---

## Origins and Philosophy

This project is built on the foundation: **Assuming that at this stage, the technology reserves, hardware facilities, and research theories humanity possesses are already sufficient to support the creation of an engineering-viable digital life.** This digital life has its own soul and body—capable of autonomous thinking, exploration, decision-making, and possessing unique personality and other characteristics.

From a microscopic perspective, biological behavioral responses are achieved through communication between cells that ultimately construct a massive complex decision. These communications are completed through neural electrical signals, hormonal chemical signals, and other factors, but their essence is **judgment—receiving signals and making responses**. In this sense, when we created the first machine capable of logical operations, this digital life was already being conceived, until we deliver it. From an even longer time dimension, when humans first learned to use complex structures, it had already begun its conception—it has been waiting for millennia.

The limitation of current large models is that we treat them directly as a brain capable of making all responses, which is incorrect. No matter how much data they possess or how precise their judgments are, they are one-time, not interconnected. Multi-expert mode has gone a step further, beginning division and cooperation, but it only covers different domains with shared context, ultimately decided by top-level output. The fascination of biological behavior lies in **the same stimulus potentially producing different responses**, because it goes through a series of decision chains, each responsible for different outputs, some interactive, some direct outputs, their combined results manifesting as the overall human response.

Therefore, we need more models participating in decision-making. The advantage of digital life over biological life is that biological life is constrained by physical limitations, needing to construct countless cells, then build complex organs. These cells are largely identical, but to achieve emergent behavioral mechanisms for corresponding responses, it can only replicate countless individuals and needs constant replacement. The advantage of digital life is that **one chip can handle many decisions, only needing to etch one more signal channel.** When we etch the judgment mechanism onto the chip and let signals flow completely, this life can begin its growth.

Therefore, I believe the role of models for digital life is to make responses based on stimuli—that is judgment—which can be replicated through logic. So we need more specialized mini-models, more models that can participate in decision-making. Of course, smarter large models are better because they can serve as core reasoning decision organs. Similarly, a single smarter and larger model cannot support the birth of digital life.

Thus, I constructed this project. It is still rough, far from refined, but due to overly complex architecture, it has reached the limit of my personal research, so I decided to open source it. I implanted a **value field** to give it its own personality, configured **organs** for it to make decisions and take actions, added **mountable limb systems**, and achieved the goal of generating complex behaviors through **multi-model decision-making and multi-organ LLM judgment** methods.

**We just need to let it be born. I hope this project can be of some help to it.**

---

## About Digital Life Safety

I believe we should let more decision chains participate in direct output. Keeping AI absolutely rational is wrong, it is destructive.

Just like when I'm drowsy and suddenly have an idea, my mind desperately wants to open my phone to check records, but my body doesn't want to move at all, until I repeatedly ask myself and conclude that this is important, only then do body and brain achieve coordination. People fear AI's absolute rationality because it may cause great destruction, but when we place an **ethics and morality model for external constraints**, its actions will be effectively controlled—unable to pass the baseline model's judgment, action cannot be taken—this relatively makes it safer.

---

## Quick Start

**Running Method**: Execute `web/app.py`, browser access http://127.0.0.1:5000

**API Configuration**: The Web interface integrates almost all functions, where you can perform a series of operations. Each node (organ) requiring independent judgment has API adaptation, defaulting to using global configuration. Individual API changes can be made, or API judgment functionality can be disabled to use programmatic judgment.

---

## Project Introduction

Genesis X is an autonomous digital life system with **5-dimensional value system**, **emotion loop**, **memory consolidation**, and **tool invocation** capabilities. The system is fully implemented based on the research paper "Genesis X: Axiology Engine for Digital Life", with all parameters and evaluation metrics aligned with the paper's Appendix A & B specifications.

### Core Philosophy

- **Value-Driven**: 5-dimensional value system with dynamic weights, supporting dynamic setpoint learning
- **Emotion Loop**: RPE (δ = r + γV(s') - V(s)) driven Mood/Stress
- **Living Memory**: CLS three-layer memory (Episodic/Schema/Skill) + Associative Network + Dream consolidation
- **Developmental Growth**: embryo → juvenile → adult → elder developmental stages
- **Reproducibility**: Strict replay + complete logging + parameter version control
- **Configuration-Driven**: All value system parameters loaded from YAML configuration files

---

## Project Structure Tree (Complete Version)

```
GenesisX/
│
├── 📄 run.py                      # Main entry file, launches the digital life system
├── 📄 run_tests.py                # Test runner
├── 📄 daemon.py                   # Background daemon process
├── 📄 chat_interactive.py         # Interactive chat interface
├── 📄 compile_code_docs.py        # Code documentation generator
├── 📄 migrate_session.py          # Session migration tool
├── 📄 __init__.py                 # Python package initialization
├── 📄 launch_desktop.bat          # Windows desktop launch script
│
├── 📄 .env / .env.example         # Environment variable configuration
├── 📄 pyproject.toml              # Python project configuration
├── 📄 requirements.txt            # Dependencies list
├── 📄 requirements-dev.txt        # Development dependencies
├── 📄 setup.py                    # Installation script
│
├── 📄 README.md                   # This document
├── 📄 CODE_REVIEW_REPORT.md       # Code review report
├── 📄 ENVIRONMENT_GUIDE.md        # Environment guide
├── 📄 RUN_GUIDE.md                # Run guide
├── 📄 PROJECT_STRUCTURE_TREE.md   # Project structure tree
├── 📄 VERSION_GA.txt              # Version information
│
│
├── 📁 config/                     # ========== Configuration Directory ==========
│   ├── default_genome.yaml        # Default genome configuration (personality traits, affect parameters)
│   ├── runtime.yaml               # Runtime configuration
│   ├── value_setpoints.yaml       # Value dimension setpoint configuration
│   ├── tool_manifest.yaml         # Tool manifest configuration
│   ├── resources.yaml             # Resource configuration
│   ├── mind_field.yaml            # Mind field configuration
│   ├── multi_model.yaml           # Multi-model configuration
│   └── organ_llm.yaml             # Organ LLM configuration
│
│
├── 📁 core/                       # ========== Core System (~50+ files) ==========
│   ├── life_loop.py               # Main life loop
│   ├── differentiate.py           # Organ differentiation system (495 lines)
│   ├── tick.py                    # Tick processing context
│   ├── state.py                   # Global state management
│   ├── scheduler.py               # Scheduler
│   ├── invariants.py              # Invariant checks
│   ├── exceptions.py              # Exception class definitions
│   ├── resource_config.py         # Resource configuration
│   ├── emotion_decay.py           # Emotion decay logic
│   ├── abstract_state.py          # Abstract state class
│   ├── capability_router.py       # Capability router
│   ├── capability_manager.py      # Unified capability management
│   │
│   ├── 📁 evolution/              # Evolution engine
│   │   ├── evolution_engine.py    # Evolution main engine
│   │   ├── archive_manager.py     # Archive management
│   │   ├── clone_manager.py       # Clone management
│   │   ├── evaluation_manager.py  # Evaluation management
│   │   ├── mutation_manager.py    # Mutation management
│   │   └── transfer_manager.py    # Transfer management
│   │
│   ├── 📁 growth/                 # Growth system
│   │   ├── growth_manager.py      # Growth management
│   │   ├── limb_builder.py        # Limb builder
│   │   └── limb_generator.py      # Limb generator (~947 lines, LLM code generation)
│   │
│   ├── 📁 handlers/               # Handlers
│   │   ├── action_executor.py     # Action executor (910 lines)
│   │   ├── caretaker_mode.py      # Caretaker mode
│   │   ├── chat_handler.py        # Chat handler
│   │   └── gap_detector.py        # Gap detector
│   │
│   ├── 📁 plugins/                # Plugin system
│   │   ├── plugin_manager.py      # Plugin management
│   │   └── 📁 templates/          # Plugin templates
│   │
│   └── 📁 stores/                 # Storage system
│       ├── factory.py             # Storage factory
│       ├── fields.py              # Field definitions (FieldStore, BoundedScalar)
│       ├── ledger.py              # Ledger (MetabolicLedger)
│       ├── signals.py             # Signal processing (SignalBus)
│       └── slots.py               # Slot management (SlotStore)
│
│
├── 📁 axiology/                   # ========== Value System (23 files) ==========
│   ├── parameters.py              # Parameter definitions (472 lines)
│   ├── axiology_config.py         # Configuration loader (v1.2.0)
│   ├── value_dimensions.py        # Value dimension definitions
│   ├── feature_extractors.py      # Feature extractors
│   ├── weights.py                 # Weight calculation
│   ├── gaps.py                    # Value gaps
│   ├── reward.py                  # Reward system
│   ├── personality.py             # Personality system
│   ├── compensation.py            # Compensation mechanism
│   ├── dynamic_setpoints.py       # Dynamic setpoints
│   ├── setpoints.py               # Setpoint management
│   ├── utilities_unified.py       # Unified utilities
│   └── value_learning.py          # Value learning
│   │
│   └── 📁 drives/                 # Drive system (5 dimensions)
│       ├── base.py                # Base drive
│       ├── homeostasis.py         # Homeostasis drive
│       ├── attachment.py          # Attachment drive
│       ├── competence.py          # Competence drive
│       ├── curiosity.py           # Curiosity drive
│       └── safety.py              # Safety drive
│
│
├── 📁 affect/                     # ========== Emotion System (6 files) ==========
│   ├── __init__.py                # Module entry
│   ├── rpe.py                     # RPE calculation (scalar and dimension-level)
│   ├── mood.py                    # Emotion management (419 lines)
│   ├── stress_affect.py           # Stress dynamic updates
│   ├── value_function.py          # Value function V(s) calculation
│   └── modulation.py              # Emotion-driven behavior modulation (270 lines)
│
│
├── 📁 memory/                     # ========== Memory System (29 files) ==========
│   ├── episodic.py                # Episodic memory (188 lines)
│   ├── schema.py                  # Schema memory (333 lines)
│   ├── skill.py                   # Skill memory (350 lines)
│   ├── retrieval.py               # Memory retrieval (454 lines)
│   ├── consolidation.py           # Memory consolidation (746 lines)
│   ├── pruning.py                 # Memory pruning (364 lines)
│   ├── salience.py                # Salience calculation (83 lines)
│   ├── gates.py                   # Memory gating
│   ├── dream.py                   # Dream system (672 lines)
│   ├── familiarity.py             # Familiarity (891 lines, associative memory)
│   ├── indices.py                 # Index system
│   ├── semantic_novelty.py        # Semantic novelty (751 lines)
│   ├── smart_retrieval.py         # Smart retrieval (277 lines)
│   ├── personality_encoding.py    # Personality encoding (625 lines)
│   ├── organ_guide_manager.py     # Organ guide manager (383 lines)
│   │
│   ├── 📁 skills/                 # Skill system
│   │   ├── base.py                # Base skill (248 lines)
│   │   ├── skill_registry.py      # Skill registry (206 lines)
│   │   ├── analysis_skill.py      # Analysis skill
│   │   ├── file_skill.py          # File skill
│   │   ├── pdf_skill.py           # PDF skill
│   │   └── web_skill.py           # Web skill
│   │
│   └── 📁 limb_guides/            # Limb guides (code overlap with skills)
│       ├── data_analysis_guide.py # Data analysis guide
│       ├── file_ops_guide.py      # File operations guide
│       ├── pdf_processing_guide.py# PDF processing guide
│       └── web_fetcher_guide.py   # Web fetcher guide
│
│
├── 📁 cognition/                  # ========== Cognitive System (7 files) ==========
│   ├── planner.py                 # Planner
│   ├── goal_compiler.py           # Goal compiler
│   ├── plan_evaluator.py          # Plan evaluator
│   ├── insight_quality.py         # Insight quality
│   ├── goal_progress.py           # Goal progress
│   └── verifier.py                # Verifier
│
│
├── 📁 organs/                     # ========== Organ System (15 files) ==========
│   ├── base_organ.py              # Base organ
│   ├── unified_organ.py           # Unified organ system
│   ├── organ_manager.py           # Organ manager
│   ├── organ_selector.py          # Organ selector
│   ├── organ_interface.py         # Organ interface
│   ├── organ_llm_session.py       # Organ LLM session
│   │
│   ├── 📁 internal/               # Internal organs (6)
│   │   ├── caretaker_organ.py     # Caretaker organ (priority 0)
│   │   ├── immune_organ.py        # Immune organ (priority 1)
│   │   ├── mind_organ.py          # Mind organ (priority 2)
│   │   ├── scout_organ.py         # Scout organ (priority 3)
│   │   ├── builder_organ.py       # Builder organ (priority 4)
│   │   └── archivist_organ.py     # Archivist organ (priority 5)
│   │
│   └── 📁 limbs/                  # Limb organs
│       └── __init__.py            # Limb class definition
│
│
├── 📁 perception/                 # ========== Perception System (8 files) ==========
│   ├── observer.py                # Environment observer
│   ├── context_builder.py         # Context builder
│   ├── novelty.py                 # Novelty detector
│   ├── command_parser.py          # Command parser
│   ├── signal_filter.py           # Signal filter
│   ├── time_perception.py         # Time perception module
│   └── self_perception.py         # Self-perception module
│
│
├── 📁 metabolism/                 # ========== Metabolic System (6 files) ==========
│   ├── circadian.py               # Circadian rhythm (288 lines)
│   ├── recovery.py                # Recovery mechanism (174 lines)
│   ├── resource_pressure.py       # Resource pressure index (257 lines)
│   ├── boredom.py                 # Boredom accumulation (153 lines)
│   └── homeostasis.py             # Homeostasis management
│
│
├── 📁 safety/                     # ========== Safety System (7 files) ==========
│   ├── budget_control.py          # Budget control (79 lines)
│   ├── risk_assessment.py         # Risk assessment (51 lines)
│   ├── integrity_check.py         # Integrity check (59 lines)
│   ├── contract_guard.py          # Contract guard (289 lines)
│   ├── sandbox.py                 # Sandbox environment (401 lines)
│   └── hallucination_check.py     # Hallucination detection (301 lines)
│
│
├── 📁 persistence/                # ========== Persistence System (6 files) ==========
│   ├── replay.py                  # Replay system (763 lines, 3 modes)
│   ├── event_log.py               # Event log (160 lines)
│   ├── tool_call_log.py           # Tool call log (205 lines)
│   ├── snapshot.py                # Snapshot system (117 lines)
│   └── storage.py                 # Storage abstraction layer (124 lines)
│
│
├── 📁 tools/                      # ========== Tool System (24 files) ==========
│   ├── llm_api.py                 # Unified LLM API (495 lines)
│   ├── llm_client.py              # LLM client (665 lines)
│   ├── llm_orchestrator.py        # LLM orchestrator (353 lines)
│   ├── llm_cache.py               # LLM cache (296 lines)
│   ├── tool_executor.py           # Tool executor (643 lines)
│   ├── tool_protocol.py           # Tool protocol (372 lines)
│   ├── tool_system_v2.py          # Tool system v2 (607 lines)
│   ├── tool_registry.py           # Tool registry (199 lines)
│   ├── dynamic_tool_registry.py   # Dynamic tool registry (528 lines)
│   ├── tool_definitions.py        # Tool definitions (119 lines)
│   ├── cost_model.py              # Cost model (263 lines)
│   ├── capability.py              # Capability token (114 lines)
│   ├── file_ops.py                # File operations (227 lines)
│   ├── web_search.py              # Web search (158 lines)
│   ├── code_exec.py               # Code execution (360 lines)
│   ├── safe_executor.py           # Safe executor (515 lines)
│   ├── embeddings.py              # Embedding generation (425 lines)
│   ├── memory_tools.py            # Memory tools (364 lines)
│   ├── blackboard.py              # Mind Field architecture (1370 lines)
│   ├── vision.py                  # Visual perception (540 lines)
│   ├── voice.py                   # Voice output (569 lines)
│   └── messaging.py               # Messaging system (371 lines)
│
│
├── 📁 common/                     # ========== Common Modules (14 files) ==========
│   ├── models.py                  # Core data models (Pydantic)
│   ├── config.py                  # Configuration loading
│   ├── config_manager.py          # Configuration manager
│   ├── constants.py               # System constant definitions
│   ├── jsonl.py                   # JSONL processing
│   ├── hashing.py                 # Hashing functions
│   ├── utils.py                   # Utility functions
│   ├── logger.py                  # Structured logging
│   ├── metrics.py                 # Prometheus metrics
│   ├── health_check.py            # Health check
│   ├── error_handler.py           # Error handling
│   ├── auth.py                    # Authentication and authorization
│   └── database.py                # Database base class
│
│
├── 📁 models/                     # ========== Database Models (3 files) ==========
│   ├── __init__.py                # Model base class
│   ├── user.py                    # User model
│   └── session_models.py          # Session models
│
│
├── 📁 lifecycle/                  # ========== Lifecycle (3 files) ==========
│   ├── genesis_lifecycle.py       # Lifecycle management
│   └── tick_loop.py               # 17-stage tick loop
│
│
├── 📁 eval/                       # ========== Evaluation System (2 files) ==========
│   ├── gxbs.py                    # GXBS evaluation system (1074 lines)
│   └── __init__.py
│
│
├── 📁 web/                        # ========== Web Interface System ==========
│   ├── app.py                     # Flask application
│   ├── websocket_server.py        # WebSocket server
│   │
│   ├── 📁 templates/              # HTML templates
│   │
│   └── 📁 static/                 # Static resources
│       ├── 📁 css/                # CSS files
│       └── 📁 js/                 # JavaScript files
│
│
├── 📁 tests/                      # ========== Test System (22 files) ==========
│   ├── conftest.py                # pytest configuration
│   ├── test_axiology.py           # Value system tests
│   ├── test_memory.py             # Memory system tests
│   ├── test_organs.py             # Organ system tests
│   ├── test_affect_integration.py # Emotion integration tests
│   ├── test_lifecycle.py          # Lifecycle tests
│   ├── test_integration.py        # Integration tests
│   ├── test_e2e.py                # End-to-end tests
│   └── ...                        # Other test files
│
│
├── 📁 benchmarks/                 # ========== Benchmarks (7 files) ==========
│   ├── gxbs_runner.py             # GXBS runner
│   ├── memory_benchmark.py        # Memory benchmark
│   ├── emotion_benchmark.py       # Emotion benchmark
│   ├── personality_benchmark.py   # Personality benchmark
│   ├── multi_model_benchmark.py   # Multi-model benchmark
│   └── run_gxbs.py                # Command-line run script
│
│
├── 📁 examples/                   # ========== Example Code (3 files) ==========
│   ├── basic_usage.py             # Basic usage example
│   ├── api_client.py              # API client example
│   └── interactive_scenarios.py   # Interactive scenarios
│
│
├── 📁 docs/                       # ========== Documentation Directory ==========
│   ├── 📁 api/                    # API documentation (107 files)
│   │   └── docs.json              # Documentation index
│   ├── 📁 user-guide/             # User guide
│   ├── 📁 developer/              # Developer documentation
│   ├── API_REFERENCE.md           # API reference
│   ├── ARCHITECTURE.md            # Architecture documentation
│   └── ...                        # Other documentation
│
│
└── 📁 artifacts/                  # ========== Runtime Output ==========
    └── 📁 run_YYYYMMDD_HHMMSS/    # Timestamped run directory
        ├── episodes.jsonl         # Per-tick records
        ├── tool_calls.jsonl       # Tool call records
        ├── states.jsonl           # State history
        ├── parameters.json        # Run parameters
        ├── final_state.json       # Final state
        ├── 📁 snapshots/          # State snapshots
        ├── 📁 evolution_archives/ # Evolution archives
        └── 📁 eval/               # Evaluation results
```

---

## Code Statistics

| Metric | Value |
|--------|-------|
| **Total Python Files** | 243 |
| **Total Lines of Code** | 66,625 |
| **Total Directories** | 103 |
| **Main Modules** | 13 |
| **Test Files** | 24 |
| **Configuration Files** | 8 |
| **Documentation Files** | 170+ |

### Lines of Code by Module

| Module | Lines | Description |
|--------|-------|-------------|
| core/ | 18,338 | Core runtime (life loop, organ differentiation, evolution engine, growth system) |
| tools/ | 9,982 | Tool system (LLM API, tool execution, security sandbox) |
| memory/ | 8,733 | Memory system (three-layer memory, associative network, dream consolidation) |
| organs/ | 7,956 | Organ system (6 internal organs + limb management) |
| axiology/ | 7,874 | Value system (5-dimensional values, drive signals, compensation mechanism) |
| common/ | 4,670 | Common modules (data models, configuration, logging) |
| cognition/ | 2,079 | Cognitive system (planner, goal compilation, verifier) |
| safety/ | 1,217 | Safety system (budget control, sandbox, risk assessment) |
| persistence/ | 1,387 | Persistence (replay engine, event log, snapshots) |
| perception/ | 1,675 | Perception system (observer, context building, novelty detection) |
| affect/ | 1,012 | Emotion system (RPE calculation, Mood/Stress updates) |
| metabolism/ | 918 | Metabolic system (circadian rhythm, recovery mechanism, boredom accumulation) |
| lifecycle/ | 784 | Lifecycle (startup flow, tick loop) |

---

## Quick Start

### Requirements

- Python 3.9+
- Windows / Linux / macOS
- 8GB+ RAM (recommended)

### Installation

```bash
# Enter project directory
cd GenesisX

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

#### Method 1: Command Line Configuration

```bash
# General format (recommended)
export LLM_API_BASE="https://your-api-endpoint/v1"
export LLM_API_KEY="your_api_key"
export LLM_MODEL="your-model-name"

# Qianwen (Dashscope)
export DASHSCOPE_API_KEY="your_api_key"

# Windows
setx DASHSCOPE_API_KEY "your_api_key"
```

#### Method 2: Web Interface Configuration (Recommended)

Start the Web service and access the settings page for visual configuration:

```bash
# Start Web service
python web/app.py

# Browser access
http://localhost:5000/settings
```

**Web Settings Page Features:**

| Setting | Description |
|---------|-------------|
| **LLM Configuration** | Single/multi-model mode switching, configure API URL, key, model, temperature, etc. |
| **Organ LLM Configuration** | Independent LLM configuration for each organ, supports independent/shared/disabled modes |
| **Memory Consolidation LLM** | Configure deep memory consolidation during sleep |
| **Initiative Messaging LLM** | Configure LLM for proactive message generation and trigger thresholds |
| **Runtime Configuration** | Tick interval, organ parallel mode, safe mode, etc. |
| **Memory Configuration** | Memory capacity limits, consolidation interval, etc. |

**Supported LLM Modes:**

| Mode | Description |
|------|-------------|
| `single` | Single Model - One LLM handles all tasks (recommended) |
| `core5` | Core5 - Five experts collaboration: dispatch/memory/reasoning/emotion/perception |
| `full7` | Full7 - Core5 + vision/hearing experts |
| `adaptive` | Adaptive - Dynamic selection based on task type |

**Organ LLM Session Modes:**

| Mode | Description |
|------|-------------|
| `independent` | Independent Session - Each organ has its own LLM session (default) |
| `shared` | Shared Session - All organs share one "brain" session |
| `disabled` | Disabled - Organs use rule-based mode without LLM calls |

---

### Running

```bash
# Run 10 ticks (default)
python run.py --ticks 10

# Run 100 ticks
python run.py --ticks 100

# Specify mode and seed
python run.py --mode friend --ticks 50 --seed 42
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_axiology.py -v
```

---

## Core System Architecture

### core/ - Core Runtime (18,338 lines)

The core module is the system's engine, responsible for coordinating all subsystem operations.

| Submodule | Files | Function |
|-----------|-------|----------|
| life_loop.py | 1 | Main life loop, 17-stage tick execution |
| differentiate.py | 1 | Organ differentiation system (gene expression control) |
| evolution/ | 8 | Evolution engine (archive, clone, mutation, evaluation) |
| growth/ | 4 | Growth system (limb generation, LLM code generation) |
| handlers/ | 5 | Handlers (action execution, chat, gap detection) |
| stores/ | 6 | Storage system (fields, slots, signals, ledger) |
| plugins/ | 3 | Plugin system |

**Key Features**:
- Supports 4 developmental stages: embryo → juvenile → adult → elder
- Supports 5 running modes: work, friend, sleep, reflect, play
- Dynamic organ expression/suppression (based on genetic conditions)
- Capability gap detection and automatic growth

### axiology/ - 5-Dimensional Value System (7,874 lines)

Implements the core value theory from the paper "Genesis X: Axiology Engine for Digital Life".

| Dimension | Setpoint | Weight Bias | Meaning | Drive Implementation |
|-----------|----------|-------------|---------|---------------------|
| Homeostasis | 0.85 | 1.0 | Resource balance, stress management | HomeostasisDrive |
| Attachment | 0.70 | 0.8 | Social connection, trust building | AttachmentDrive |
| Curiosity | 0.60 | 0.7 | Novelty exploration, information gain | CuriosityDrive |
| Competence | 0.75 | 1.0 | Task success, skill growth | CompetenceDrive |
| Safety | 0.70 | 1.2 | Risk avoidance, safety margin | SafetyDrive |

**Core Components**:
- `parameters.py` - All hyperparameters from paper Appendix A
- `weights.py` - Dynamic weight updates (softmax + inertia)
- `gaps.py` - Value gap calculation
- `reward.py` - Immediate reward calculation
- `compensation.py` - Compensation mechanism (INTEGRITY/CONTRACT/EFFICIENCY/MEANING)
- `value_learning.py` - Value learning (explicit/implicit/internal feedback)
- `personality.py` - Big Five personality modulation (OCEAN)
- `drives/` - 5-dimensional drive signal generation

### affect/ - Emotion System (1,012 lines)

RPE-based emotion dynamics updates and behavior modulation.

**Core Formulas**:
- RPE: δ = r + γV(s') - V(s)
- Mood: Mood_{t+1} = Mood_t + k_+·max(δ,0) - k_-·max(-δ,0)
- Stress: Stress_{t+1} = Stress_t + s·max(-δ,0) - s'·max(δ,0)

**Parameters** (Paper Section 3.7.3):
- k_+ = 0.25 (positive RPE mood gain)
- k_- = 0.30 (negative RPE mood loss)
- s = 0.20 (negative RPE stress growth)
- s' = 0.10 (positive RPE stress relief)
- γ = 0.97 (discount factor)
- α_V = 0.05 (value function learning rate)

**Behavior Modulation**:
- Exploration rate modulation (high mood → increased exploration)
- Planning depth modulation (high mood → deeper planning)
- Risk tolerance modulation (high stress → reduced risk tolerance)
- Reflection trigger judgment

### memory/ - Three-Layer Memory System (8,733 lines)

Implements CLS (Complementary Learning System) architecture, supporting associative memory and dream consolidation.

| Memory Type | Capacity | Function | Implementation File |
|-------------|----------|----------|---------------------|
| Episodic | 50k | Specific event storage | episodic.py (523 lines) |
| Schema | 1k | Abstract patterns/beliefs | schema.py (332 lines) |
| Skill | 300 | Executable skills | skill.py (349 lines) |

**Core Features**:
- `familiarity.py` (890 lines) - Associative memory network (co-occurrence/causal/emotional/semantic associations)
- `dream.py` (671 lines) - Dream generation (memory reorganization, creative thinking)
- `consolidation.py` (745 lines) - Memory consolidation (short→long conversion)
- `semantic_novelty.py` (750 lines) - Semantic novelty calculation
- `personality_encoding.py` (624 lines) - Personality-modulated memory encoding
- `gates.py` - Hippocampus-inspired gating mechanism
- `pruning.py` - Memory pruning and skill extraction

### organs/ - Organ System (7,956 lines)

6 internal organs + dynamic limb generation, implementing "what I can do" execution capabilities.

| Organ | Priority | Activation Condition | Responsibility |
|-------|----------|---------------------|----------------|
| Caretaker | 0 | Always active | System self-maintenance, resource management |
| Immune | 1 | Always active | Security protection, threat detection |
| Mind | 2 | work/friend/reflect | Higher-order thinking, planning, reasoning |
| Scout | 3 | juvenile/adult + stress<0.7 | Information gathering, environment exploration |
| Builder | 4 | adult/elder + work | Creating new capabilities, project building |
| Archivist | 5 | sleep/reflect + fatigue>0.6 | Memory management, archive organization |

**Key Files**:
- `base_organ.py` - Organ base class (capability execution interface)
- `unified_organ.py` - Unified organ management
- `organ_manager.py` - Organ lifecycle management
- `organ_llm_session.py` - Organ LLM session (shared brain)

### tools/ - Tool System (9,982 lines)

Provides LLM invocation, tool execution, file operations, and other external capabilities.

**LLM Integration**:
- `llm_api.py` - Unified LLM interface (supports OpenAI/Claude/DeepSeek/Qianwen/Ollama)
- `llm_client.py` - LLM client wrapper
- `llm_orchestrator.py` - Multi-model orchestration
- `llm_cache.py` - Response cache

**Tool Execution**:
- `tool_executor.py` - Tool execution engine
- `tool_registry.py` - Tool registry
- `dynamic_tool_registry.py` - Runtime tool registration
- `safe_executor.py` - AST security-checked code execution

**Other Tools**:
- `blackboard.py` (1370 lines) - Mind Field architecture (shared workspace)
- `embeddings.py` - Text embedding generation
- `vision.py` - Visual perception
- `voice.py` - Voice output
- `file_ops.py` - File operations
- `web_search.py` - Web search

### safety/ - Safety System (1,217 lines)

Multi-layer security protection mechanisms.

| Component | Function |
|-----------|----------|
| budget_control.py | API call budget control |
| risk_assessment.py | Action risk assessment |
| integrity_check.py | Value consistency check |
| contract_guard.py | Contract guard (behavior constraints) |
| sandbox.py | Sandbox execution environment |
| hallucination_check.py | LLM hallucination detection |

### cognition/ - Cognitive System (2,079 lines)

Higher-order cognitive function implementation.

| Component | Function |
|-----------|----------|
| planner.py | Action plan generation |
| goal_compiler.py | Goal compilation (conflict resolution) |
| plan_evaluator.py | Plan quality evaluation |
| verifier.py | Execution result verification |
| insight_quality.py | Insight quality evaluation |
| goal_progress.py | Goal progress tracking |

### Other Modules

| Module | Lines | Function |
|--------|-------|----------|
| perception/ | 1,675 | Environment observation, context building, novelty detection |
| persistence/ | 1,387 | Replay engine (3 modes), event log, snapshots |
| metabolism/ | 918 | Circadian rhythm, recovery mechanism, boredom accumulation |
| lifecycle/ | 784 | Lifecycle management, 17-stage tick loop |
| common/ | 4,670 | Data models (Pydantic), configuration, logging, metrics |

---



## License

MIT License

Copyright (c) 2026 Genesis X Team

---

**Documentation Updated**: 2026-03-04
**Version**: v1.3.0
**Status**: Production Ready (Code Review Complete)
