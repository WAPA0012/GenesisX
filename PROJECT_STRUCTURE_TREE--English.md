# GenesisX Project Structure Tree - Complete Documentation

**Version**: v1.3.0
**Generated**: 2026-03-04
**Project Description**: A digital life system with a 5-dimensional value system, emotional feedback loop, memory consolidation, and autonomous capabilities

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Total Python Files | 243 |
| Total Directories | 103 |
| Total Lines of Code | 66,625 |
| Core Modules | 13 |
| Test Files | 24 |
| Configuration Files | 8 |
| Documentation Files | 170+ |

### Code Lines by Module

| Module | Lines | Primary Functions |
|--------|-------|-------------------|
| core/ | 18,338 | Core runtime (life loop, organ differentiation, evolution engine, growth system) |
| tools/ | 9,982 | Tool system (LLM API, tool execution, security sandbox) |
| memory/ | 8,733 | Memory system (three-layer memory, associative network, dream consolidation) |
| organs/ | 7,956 | Organ system (6 internal organs + limb management) |
| axiology/ | 7,874 | Value system (5-dimensional values, drive signals, compensation mechanisms) |
| common/ | 4,670 | Common modules (data models, configuration, logging) |
| cognition/ | 2,079 | Cognitive system (planner, goal compiler, verifier) |
| safety/ | 1,217 | Safety system (budget control, sandbox, risk assessment) |
| persistence/ | 1,387 | Persistence (replay engine, event log, snapshots) |
| perception/ | 1,675 | Perception system (observer, context builder, novelty detection) |
| affect/ | 1,012 | Affect system (RPE calculation, Mood/Stress updates) |
| metabolism/ | 918 | Metabolism system (circadian rhythm, recovery mechanisms, boredom accumulation) |
| lifecycle/ | 784 | Lifecycle (startup flow, tick loop) |

---

## Directory Tree Overview

```
GenesisX/
├── 📄 Root Files (15 files)
├── 📁 affect/              # Affect System (6 files)
├── 📁 artifacts/           # Runtime Output Directory (runtime data)
├── 📁 axiology/            # Value System (17 files)
│   ├── 📁 drives/          # Drive Subsystem (6 files)
│   └── 📁 examples/        # Value System Examples (2 files)
├── 📁 benchmarks/          # Benchmarks (7 files)
├── 📁 cognition/           # Cognitive System (7 files)
├── 📁 common/              # Common Modules (15 files)
├── 📁 config/              # Configuration Files (9 files)
├── 📁 core/                # Core Runtime (32 files)
│   ├── 📁 evolution/       # Evolution Subsystem (8 files)
│   ├── 📁 growth/          # Growth Subsystem (4 files)
│   ├── 📁 handlers/        # Event Handlers (5 files)
│   ├── 📁 plugins/         # Plugin System (3 files)
│   └── 📁 stores/          # Storage Backends (6 files)
├── 📁 docs/                # Documentation Directory (80+ files)
│   ├── 📁 api/             # API Documentation (140+ files)
│   ├── 📁 developer/       # Developer Documentation
│   └── 📁 user-guide/      # User Guide
├── 📁 eval/                # Evaluation System (2 files)
├── 📁 examples/            # Example Code (3 files)
├── 📁 lifecycle/           # Lifecycle (3 files)
├── 📁 logs/                # Log Files (4 files)
├── 📁 memory/              # Memory System (24 files)
│   ├── 📁 limb_guides/     # Limb Guides (5 files + data/)
│   └── 📁 skills/          # Skill Memory (7 files)
├── 📁 metabolism/          # Metabolism System (5 files)
├── 📁 models/              # Data Models (3 files)
├── 📁 organs/              # Organ System (13 files)
│   ├── 📁 internal/        # Internal Organs (7 files)
│   └── 📁 limbs/           # Limb Organs
├── 📁 perception/          # Perception System (8 files)
├── 📁 persistence/         # Persistence (6 files)
├── 📁 safety/              # Safety System (7 files)
├── 📁 tests/               # Test Suite (24 files)
├── 📁 tools/               # Tool System (25 files)
├── 📁 web/                 # Web Interface (20+ files)
│   ├── 📁 artifacts/       # Web Runtime Output
│   ├── 📁 logs/            # Web Logs
│   ├── 📁 static/          # Static Resources (CSS/JS)
│   └── 📁 templates/       # HTML Templates (9 files)
├── 📁 __pycache__/         # Python Cache
└── 📁 .pytest_cache/       # Pytest Cache
```

---

## 1. Root Files

| File | Description |
|------|-------------|
| [.env](.env) | **Environment Variables** - Sensitive information like API keys (not committed to git) |
| [.env.example](.env.example) | **Environment Variable Template** - Example environment variable configuration |
| [.gitignore](.gitignore) | **Git Ignore Configuration** - Specifies files not to be committed |
| [__init__.py](__init__.py) | **Package Initialization** - Python package initialization file |
| [chat_interactive.py](chat_interactive.py) | **Interactive Chat** - Entry script for conversational interaction with digital life |
| [chat_test.txt](chat_test.txt) | **Chat Test Data** - Test chat content |
| [compile_code_docs.py](compile_code_docs.py) | **Documentation Generator** - Compiles and generates code documentation |
| [daemon.py](daemon.py) | **Daemon Process** - Background running mode entry |
| [launch_desktop.bat](launch_desktop.bat) | **Desktop Launch Script** - Windows quick-start batch file |
| [migrate_session.py](migrate_session.py) | **Session Migration Tool** - Migrates legacy session data |
| [pyproject.toml](pyproject.toml) | **Project Configuration** - Modern Python project configuration (PEP 517/518) |
| [README.md](README.md) | **Project Readme** - Project introduction, installation, and usage guide |
| [requirements.txt](requirements.txt) | **Production Dependencies** - Required Python packages for runtime |
| [requirements-dev.txt](requirements-dev.txt) | **Development Dependencies** - Additional packages for development and testing |
| [run.py](run.py) | **Main Entry File** - Main program entry for launching GenesisX digital life |
| [run_tests.py](run_tests.py) | **Test Runner** - Executes the test suite |
| [setup.py](setup.py) | **Installation Script** - Traditional Python package installation configuration |
| [test_tools.py](test_tools.py) | **Tool Testing** - Tool system test script |
| [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md) | **Environment Configuration Guide** - Detailed environment configuration instructions |
| [RUN_GUIDE.md](RUN_GUIDE.md) | **Run Guide** - System operation documentation |
| [PROJECT_STRUCTURE_TREE.md](PROJECT_STRUCTURE_TREE.md) | **Project Structure Tree** - This file |

---

## 2. affect/ - Affect System Module

Responsible for emotional computation, RPE (Reward Prediction Error) processing, emotion decay, etc.

| File | Function |
|------|----------|
| [__init__.py](affect/__init__.py) | Module initialization, exports main classes and functions |
| [rpe.py](affect/rpe.py) | **RPE Calculation** - Implements reward prediction error δ = r + γV(s') - V(s) |
| [mood.py](affect/mood.py) | **Mood System** - Updates mood based on RPE, supports multi-dimensional emotions |
| [stress_affect.py](affect/stress_affect.py) | **Stress System** - Accumulates stress based on negative RPE, supports stress relief |
| [modulation.py](affect/modulation.py) | **Emotion Modulation** - Emotional regulation of cognition and behavior |
| [value_function.py](affect/value_function.py) | **Value Function** - Estimation and update of state value V(s) |

---

## 3. axiology/ - Value System Module

Implements the 5-dimensional value system (homeostasis, attachment, curiosity, competence, safety), including feature extraction, gap calculation, dynamic weights, etc.

### 3.1 Main Module Files

| File | Function |
|------|----------|
| [__init__.py](axiology/__init__.py) | Module initialization, exports all public interfaces and compensation mechanisms |
| [axiology_config.py](axiology/axiology_config.py) | **Configuration Loader** - Loads value system parameters from YAML |
| [parameters.py](axiology/parameters.py) | **Parameter Definitions** - All hyperparameters from paper Appendix A |
| [value_dimensions.py](axiology/value_dimensions.py) | **Value Dimensions** - Defines 5 value dimensions and their calculation methods |
| [feature_extractors.py](axiology/feature_extractors.py) | **Feature Extraction** - Extracts feature values for each value dimension from state |
| [gaps.py](axiology/gaps.py) | **Gap Calculation** - Calculates gaps between feature values and setpoints |
| [weights.py](axiology/weights.py) | **Dynamic Weights** - Computes softmax weight distribution based on gaps |
| [reward.py](axiology/reward.py) | **Reward Function** - Computes immediate reward by combining all dimensions |
| [setpoints.py](axiology/setpoints.py) | **Setpoint Management** - Manages target values for each dimension |
| [dynamic_setpoints.py](axiology/dynamic_setpoints.py) | **Dynamic Setpoints** - Automatically learns optimal setpoints |
| [utilities_unified.py](axiology/utilities_unified.py) | **Unified Utility Function** - Computes utility values for each dimension |
| [value_learning.py](axiology/value_learning.py) | **Value Learning** - Learns value preferences from experience |
| [personality.py](axiology/personality.py) | **Personality System** - Defines individual character traits and preferences |
| [compensation.py](axiology/compensation.py) | **Compensation Mechanism (Plan B)** - Implementation of INTEGRITY/CONTRACT/EFFICIENCY/MEANING compensation |

### 3.2 drives/ - Drive Subsystem

| File | Function |
|------|----------|
| [__init__.py](axiology/drives/__init__.py) | Drive module initialization |
| [base.py](axiology/drives/base.py) | **Drive Base Class** - Abstract base class for all drives |
| [homeostasis.py](axiology/drives/homeostasis.py) | **Homeostasis Drive** - Maintains internal balance (energy, fatigue, stress) |
| [attachment.py](axiology/drives/attachment.py) | **Attachment Drive** - Social connection and relationship building |
| [curiosity.py](axiology/drives/curiosity.py) | **Curiosity Drive** - Motivation to explore novel things |
| [competence.py](axiology/drives/competence.py) | **Competence Drive** - Drive to master skills and complete tasks |
| [safety.py](axiology/drives/safety.py) | **Safety Drive** - Risk avoidance and self-protection |

### 3.3 examples/ - Example Code

| File | Function |
|------|----------|
| [__init__.py](axiology/examples/__init__.py) | Example module initialization |
| [compensation_example.py](axiology/examples/compensation_example.py) | Compensation mechanism usage example |

---

## 4. cognition/ - Cognitive System Module

Responsible for high-level cognitive functions: planning, goal compilation, verification, etc.

| File | Function |
|------|----------|
| [__init__.py](cognition/__init__.py) | Cognitive module initialization |
| [goal_compiler.py](cognition/goal_compiler.py) | **Goal Compiler** - Compiles user goals into system-executable goals |
| [goal_progress.py](cognition/goal_progress.py) | **Goal Progress** - Tracks goal completion progress |
| [insight_quality.py](cognition/insight_quality.py) | **Insight Quality** - Evaluates value and quality of insights |
| [planner.py](cognition/planner.py) | **Plan Generator** - Generates action plans |
| [plan_evaluator.py](cognition/plan_evaluator.py) | **Plan Evaluator** - Evaluates plan quality and feasibility |
| [verifier.py](cognition/verifier.py) | **Verifier** - Verifies plan execution results |

---

## 5. common/ - Common Modules

General utilities, configuration, and base components.

| File | Function |
|------|----------|
| [__init__.py](common/__init__.py) | Common module initialization |
| [auth.py](common/auth.py) | **Authentication** - User authentication and authorization |
| [config.py](common/config.py) | **Configuration** - Configuration management |
| [config_manager.py](common/config_manager.py) | **Config Manager** - Configuration file loading and management |
| [constants.py](common/constants.py) | **Constants** - System constant definitions |
| [database.py](common/database.py) | **Database** - Database connection management |
| [error_handler.py](common/error_handler.py) | **Error Handling** - Unified error handling mechanism |
| [hashing.py](common/hashing.py) | **Hashing** - Hash calculation utilities |
| [health_check.py](common/health_check.py) | **Health Check** - System health status checking |
| [jsonl.py](common/jsonl.py) | **JSONL Processing** - JSONL format read/write utilities |
| [logger.py](common/logger.py) | **Logging System** - Unified logging |
| [metrics.py](common/metrics.py) | **Metrics Collection** - System metrics collection and reporting |
| [models.py](common/models.py) | **Data Models** - Core data model definitions |
| [utils.py](common/utils.py) | **Utility Functions** - General utility function collection |

---

## 6. config/ - Configuration Files Directory

| File | Function |
|------|----------|
| [default_genome.yaml](config/default_genome.yaml) | **Default Genome** - Organ gene configuration, defines initial personality |
| [llm_config.env.example](config/llm_config.env.example) | **LLM Config Example** - LLM service configuration template |
| [mind_field.yaml](config/mind_field.yaml) | **Mind Field Configuration** - Mind field parameter settings |
| [multi_model.yaml](config/multi_model.yaml) | **Multi-Model Configuration** - Multi-LLM model coordination configuration |
| [organ_llm.yaml](config/organ_llm.yaml) | **Organ LLM Configuration** - LLM configuration used by each organ |
| [resources.yaml](config/resources.yaml) | **Resource Configuration** - Resource limits and quota configuration |
| [runtime.yaml](config/runtime.yaml) | **Runtime Configuration** - Tick configuration, budget constraints, etc. |
| [tool_manifest.yaml](config/tool_manifest.yaml) | **Tool Manifest** - Available tool definitions and permissions |
| [value_setpoints.yaml](config/value_setpoints.yaml) | **Value Setpoints** - Setpoint configuration for 5-dimensional value system |

---

## 7. core/ - Core Runtime Module

The system's core engine, responsible for life loop, organ differentiation, state management, tick scheduling, etc.

### 7.1 Main Module Files

| File | Function |
|------|----------|
| [__init__.py](core/__init__.py) | Core module initialization |
| [abstract_state.py](core/abstract_state.py) | **Abstract State** - State base class definition |
| [autonomous_scheduler.py](core/autonomous_scheduler.py) | **Autonomous Scheduler** - Scheduling management for autonomous behaviors |
| [capability_gap_detector.py](core/capability_gap_detector.py) | **Capability Gap Detector** - Identifies system capability deficiencies |
| [capability_manager.py](core/capability_manager.py) | **Capability Manager** - System capability management |
| [capability_router.py](core/capability_router.py) | **Capability Router** - Dynamic capability dispatch and routing |
| [differentiate.py](core/differentiate.py) | **Organ Differentiation** - Developmental stages and organ expression system |
| [emotion_decay.py](core/emotion_decay.py) | **Emotion Decay** - Natural decay of emotions over time |
| [exceptions.py](core/exceptions.py) | **Exception Definitions** - Core exception classes |
| [exploration.py](core/exploration.py) | **Exploration System** - Exploration behavior management |
| [invariants.py](core/invariants.py) | **Invariant Checking** - Maintains system invariants |
| [life_loop.py](core/life_loop.py) | **Life Loop** - Main loop engine, coordinates all systems |
| [life_loop_backup.py](core/life_loop_backup.py) | **Life Loop Backup** - Backup version |
| [resource_config.py](core/resource_config.py) | **Resource Configuration** - Resource management configuration |
| [scheduler.py](core/scheduler.py) | **Scheduler** - Task and organ scheduling management |
| [state.py](core/state.py) | **State Management** - System state definition and updates |
| [tick.py](core/tick.py) | **Tick Execution** - Complete execution flow of a single tick |

### 7.2 evolution/ - Evolution Subsystem

| File | Function |
|------|----------|
| [__init__.py](core/evolution/__init__.py) | Evolution module initialization |
| [archive_manager.py](core/evolution/archive_manager.py) | **Archive Management** - Storage and retrieval of evolution archives |
| [clone_manager.py](core/evolution/clone_manager.py) | **Clone Management** - System cloning and replication |
| [evaluation_manager.py](core/evolution/evaluation_manager.py) | **Evaluation Management** - Evolution fitness evaluation |
| [evolution_engine.py](core/evolution/evolution_engine.py) | **Evolution Engine** - Core evolution algorithms |
| [models.py](core/evolution/models.py) | **Evolution Models** - Evolution data model definitions |
| [mutation_manager.py](core/evolution/mutation_manager.py) | **Mutation Management** - Parameter mutation and optimization |
| [transfer_manager.py](core/evolution/transfer_manager.py) | **Transfer Management** - Learning transfer and sharing |

### 7.3 growth/ - Growth Subsystem

| File | Function |
|------|----------|
| [__init__.py](core/growth/__init__.py) | Growth module initialization |
| [growth_manager.py](core/growth/growth_manager.py) | **Growth Manager** - Manages system growth process |
| [limb_builder.py](core/growth/limb_builder.py) | **Limb Builder** - Dynamically builds new limbs/tools |
| [limb_generator.py](core/growth/limb_generator.py) | **Limb Generator** - LLM-driven limb generation (V32 style) |

### 7.4 handlers/ - Event Handlers

| File | Function |
|------|----------|
| [__init__.py](core/handlers/__init__.py) | Handler module initialization |
| [action_executor.py](core/handlers/action_executor.py) | **Action Executor** - Executes system actions |
| [caretaker_mode.py](core/handlers/caretaker_mode.py) | **Caretaker Mode** - Self-maintenance mode |
| [chat_handler.py](core/handlers/chat_handler.py) | **Chat Handler** - Handles chat interactions |
| [gap_detector.py](core/handlers/gap_detector.py) | **Gap Detector** - Detects state gaps |

### 7.5 plugins/ - Plugin System

| File | Function |
|------|----------|
| [__init__.py](core/plugins/__init__.py) | Plugin module initialization |
| [plugin_manager.py](core/plugins/plugin_manager.py) | **Plugin Manager** - Manages system plugins |
| [templates/__init__.py](core/plugins/templates/__init__.py) | Plugin templates |

### 7.6 stores/ - Storage Backends

| File | Function |
|------|----------|
| [__init__.py](core/stores/__init__.py) | Storage module initialization |
| [factory.py](core/stores/factory.py) | **Storage Factory** - Creates storage instances |
| [fields.py](core/stores/fields.py) | **Field Storage** - Storage and access of state fields |
| [ledger.py](core/stores/ledger.py) | **Ledger Storage** - Metabolism ledger, tracks resource consumption |
| [signals.py](core/stores/signals.py) | **Signal Storage** - Storage and update of signal values |
| [slots.py](core/stores/slots.py) | **Slot Storage** - Dynamic slot management |

---

## 8. docs/ - Documentation Directory

### 8.1 Main Documentation Files

| File | Function |
|------|----------|
| [API_REFERENCE.md](docs/API_REFERENCE.md) | **API Reference Manual** - Complete API documentation |
| [architecture_clarification.md](docs/architecture_clarification.md) | **Architecture Clarification** - System architecture clarification |
| [architecture_diagram.md](docs/architecture_diagram.md) | **Architecture Diagram** - System architecture visualization |
| [dependency_analysis.md](docs/dependency_analysis.md) | **Dependency Analysis** - Module dependency relationship analysis |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | **Deployment Guide** - Production environment deployment instructions |
| [evolution_stages.md](docs/evolution_stages.md) | **Evolution Stages** - System evolution stage explanation |
| [LLM_API_CONFIGURATION_GUIDE.md](docs/LLM_API_CONFIGURATION_GUIDE.md) | **LLM Configuration Guide** - LLM API configuration |
| [MULTI_MODEL_GUIDE.md](docs/MULTI_MODEL_GUIDE.md) | **Multi-Model Guide** - Multi-LLM model usage |
| [project_structure_full.md](docs/project_structure_full.md) | **Full Structure** - Complete project structure explanation |
| [refactoring_complete.md](docs/refactoring_complete.md) | **Refactoring Notes** - Refactoring completion record |
| [skills_vs_organs_summary.md](docs/skills_vs_organs_summary.md) | **Skills vs Organs** - Comparison summary of the two |
| [tutorials.md](docs/tutorials.md) | **Tutorials** - Usage tutorials |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | **User Guide** - User instructions |
| [VALUE_SYSTEM_CONFIG.md](docs/VALUE_SYSTEM_CONFIG.md) | **Value System Configuration** - Detailed value system configuration |
| [WEB_OPTIMIZATION.md](docs/WEB_OPTIMIZATION.md) | **Web Optimization** - Web interface optimization guide |

### 8.2 api/ - API Documentation Directory (140+ files)

Auto-generated API documentation, each module and submodule has corresponding .md files:

- `affect*.md` - Affect system API
- `axiology*.md` - Value system API
- `cognition*.md` - Cognitive system API
- `common*.md` - Common components API
- `core*.md` - Core system API
- `memory*.md` - Memory system API
- `metabolism*.md` - Metabolism system API
- `organs*.md` - Organ system API
- `perception*.md` - Perception system API
- `persistence*.md` - Persistence API
- `safety*.md` - Safety system API
- `tools*.md` - Tool system API

| Key File | Function |
|---------|----------|
| [docs.json](docs/api/docs.json) | API documentation JSON index |
| [README.md](docs/api/README.md) | API documentation index page |

### 8.3 developer/ & user-guide/

| Directory | Function |
|-----------|----------|
| [developer/README.md](docs/developer/README.md) | Developer documentation entry |
| [user-guide/README.md](docs/user-guide/README.md) | User guide entry |

---

## 9. eval/ - Evaluation System

| File | Function |
|------|----------|
| [__init__.py](eval/__init__.py) | Evaluation module initialization |
| [gxbs.py](eval/gxbs.py) | **GXBS Evaluation** - GenesisX Benchmark Evaluation Standard |

---

## 10. examples/ - Example Code

| File | Function |
|------|----------|
| [api_client.py](examples/api_client.py) | **API Client Example** - Demonstrates how to call the API |
| [basic_usage.py](examples/basic_usage.py) | **Basic Usage** - Basic system usage example |
| [interactive_scenarios.py](examples/interactive_scenarios.py) | **Interactive Scenarios** - Interactive usage scenario examples |

---

## 11. lifecycle/ - Lifecycle

| File | Function |
|------|----------|
| [__init__.py](lifecycle/__init__.py) | Lifecycle module initialization |
| [genesis_lifecycle.py](lifecycle/genesis_lifecycle.py) | **Genesis Lifecycle** - System startup and initialization flow |
| [tick_loop.py](lifecycle/tick_loop.py) | **Tick Loop** - Main running loop implementation |

---

## 12. logs/ - Log Directory

| File | Function |
|------|----------|
| [errors.json](logs/errors.json) | **Error Log** - Error records in JSON format |
| [genesis.json](logs/genesis.json) | **Main Log** - System running log |
| [genesis.json.1](logs/genesis.json.1) | **Log Backup** - Rotated backup log |
| [server.log](logs/server.log) | **Server Log** - Web server log |

---

## 13. memory/ - Memory System Module

Implements episodic memory, schema memory, associative memory, memory consolidation, etc.

### 13.1 Main Module Files

| File | Function |
|------|----------|
| [__init__.py](memory/__init__.py) | Memory module initialization |
| [consolidation.py](memory/consolidation.py) | **Memory Consolidation** - Dream-reflection-insight consolidation mechanism |
| [dream.py](memory/dream.py) | **Dream System** - Memory processing and integration during sleep |
| [episodic.py](memory/episodic.py) | **Episodic Memory** - Stores specific events and experiences |
| [familiarity.py](memory/familiarity.py) | **Familiarity** - Familiarity calculation for associative memory |
| [gates.py](memory/gates.py) | **Memory Gating** - Controls information flow into memory |
| [indices.py](memory/indices.py) | **Memory Indices** - Memory indexing system |
| [organ_guide_manager.py](memory/organ_guide_manager.py) | **Organ Guide Manager** - Manages organ usage guides |
| [personality_encoding.py](memory/personality_encoding.py) | **Personality Encoding** - Personality-modulated memory encoding |
| [pruning.py](memory/pruning.py) | **Memory Pruning** - Forgetting curve and memory cleanup |
| [retrieval.py](memory/retrieval.py) | **Memory Retrieval** - Hybrid retrieval system |
| [salience.py](memory/salience.py) | **Salience** - Calculates memory importance |
| [schema.py](memory/schema.py) | **Schema Memory** - Abstract patterns and regularities |
| [semantic_novelty.py](memory/semantic_novelty.py) | **Semantic Novelty** - Evaluates novelty using embedding vectors |
| [skill.py](memory/skill.py) | **Skill Memory** - Skill storage and learning |
| [smart_retrieval.py](memory/smart_retrieval.py) | **Smart Retrieval** - Intelligent memory retrieval system |
| [utils.py](memory/utils.py) | **Memory Utils** - Memory-related utility functions |

### 13.2 limb_guides/ - Limb Guides

| File | Function |
|------|----------|
| [__init__.py](memory/limb_guides/__init__.py) | Limb guide module initialization |
| [data/organ_guides.json](memory/limb_guides/data/organ_guides.json) | **Organ Guide Data** - Guide data in JSON format |
| [data_analysis_guide.py](memory/limb_guides/data_analysis_guide.py) | **Data Analysis Guide** - Data analysis capability guide |
| [file_ops_guide.py](memory/limb_guides/file_ops_guide.py) | **File Operations Guide** - File operations capability guide |
| [pdf_processing_guide.py](memory/limb_guides/pdf_processing_guide.py) | **PDF Processing Guide** - PDF processing capability guide |
| [web_fetcher_guide.py](memory/limb_guides/web_fetcher_guide.py) | **Web Fetcher Guide** - Web fetching capability guide |

### 13.3 skills/ - Skill System

| File | Function |
|------|----------|
| [__init__.py](memory/skills/__init__.py) | Skill module initialization |
| [analysis_skill.py](memory/skills/analysis_skill.py) | **Analysis Skill** - Data analysis skill implementation |
| [base.py](memory/skills/base.py) | **Skill Base Class** - Abstract base class for all skills |
| [file_skill.py](memory/skills/file_skill.py) | **File Skill** - File operations skill implementation |
| [pdf_skill.py](memory/skills/pdf_skill.py) | **PDF Skill** - PDF processing skill implementation |
| [skill_registry.py](memory/skills/skill_registry.py) | **Skill Registry** - Skill registration and management |
| [web_skill.py](memory/skills/web_skill.py) | **Web Skill** - Web operations skill implementation |

---

## 14. metabolism/ - Metabolism System Module

Responsible for energy management and resource regulation of digital life.

| File | Function |
|------|----------|
| [__init__.py](metabolism/__init__.py) | Metabolism module initialization |
| [boredom.py](metabolism/boredom.py) | **Boredom System** - Incentivizes exploration, prevents stagnation |
| [circadian.py](metabolism/circadian.py) | **Circadian Rhythm** - Simulates biological clock |
| [recovery.py](metabolism/recovery.py) | **Recovery System** - Rest and recovery mechanisms |
| [resource_pressure.py](metabolism/resource_pressure.py) | **Resource Pressure** - Behavior regulation during resource scarcity |

---

## 15. models/ - Data Models

| File | Function |
|------|----------|
| [__init__.py](models/__init__.py) | Model module initialization |
| [session_models.py](models/session_models.py) | **Session Models** - Session data model definitions |
| [user.py](models/user.py) | **User Models** - User data model definitions |

---

## 16. organs/ - Organ System Module

Manages all internal organs and limbs, provides unified calling interface.

### 16.1 Main Module Files

| File | Function |
|------|----------|
| [__init__.py](organs/__init__.py) | Organ module initialization |
| [base_organ.py](organs/base_organ.py) | **Organ Base Class** - Abstract base class for all organs |
| [organ_interface.py](organs/organ_interface.py) | **Organ Interface** - Organ interface definition |
| [organ_llm_session.py](organs/organ_llm_session.py) | **Organ LLM Session** - LLM session management for organs |
| [organ_manager.py](organs/organ_manager.py) | **Organ Manager** - Manages all organs and limbs |
| [organ_selector.py](organs/organ_selector.py) | **Organ Selector** - Selects organs based on context |
| [unified_organ.py](organs/unified_organ.py) | **Unified Organ** - Unified organ implementation |

### 16.2 internal/ - Internal Organs

| File | Function |
|------|----------|
| [__init__.py](organs/internal/__init__.py) | Internal organ module initialization |
| [archivist_organ.py](organs/internal/archivist_organ.py) | **Archivist Organ** - Memory management and archiving |
| [builder_organ.py](organs/internal/builder_organ.py) | **Builder Organ** - Creates new capabilities and limbs |
| [caretaker_organ.py](organs/internal/caretaker_organ.py) | **Caretaker Organ** - System self-maintenance |
| [immune_organ.py](organs/internal/immune_organ.py) | **Immune Organ** - Security protection and threat detection |
| [mind_organ.py](organs/internal/mind_organ.py) | **Mind Organ** - High-level thinking and decision making |
| [scout_organ.py](organs/internal/scout_organ.py) | **Scout Organ** - Information gathering and exploration |

### 16.3 limbs/ - Limb Organs

| File | Function |
|------|----------|
| [__init__.py](organs/limbs/__init__.py) | Limb module initialization (dynamically extensible) |

---

## 17. perception/ - Perception System Module

Responsible for perceptual input and environmental understanding.

| File | Function |
|------|----------|
| [__init__.py](perception/__init__.py) | Perception module initialization |
| [command_parser.py](perception/command_parser.py) | **Command Parser** - Parses user commands |
| [context_builder.py](perception/context_builder.py) | **Context Builder** - Builds perception context |
| [novelty.py](perception/novelty.py) | **Novelty Detection** - Detects novel stimuli |
| [observer.py](perception/observer.py) | **Observer** - Monitors system and environment |
| [self_perception.py](perception/self_perception.py) | **Self Perception** - Self-state monitoring |
| [signal_filter.py](perception/signal_filter.py) | **Signal Filter** - Filters perception signals |
| [time_perception.py](perception/time_perception.py) | **Time Perception** - Time perception processing |

---

## 18. persistence/ - Persistence Module

Responsible for state and data persistent storage.

| File | Function |
|------|----------|
| [__init__.py](persistence/__init__.py) | Persistence module initialization |
| [event_log.py](persistence/event_log.py) | **Event Log** - Records all events |
| [replay.py](persistence/replay.py) | **Replay Engine** - Three-mode replay (strict/semantic/fork) |
| [snapshot.py](persistence/snapshot.py) | **State Snapshot** - System state snapshots |
| [storage.py](persistence/storage.py) | **Storage Management** - Generic storage interface |
| [tool_call_log.py](persistence/tool_call_log.py) | **Tool Call Log** - Specifically records tool calls |

---

## 19. safety/ - Safety System Module

Responsible for safety protection and risk control of digital life.

| File | Function |
|------|----------|
| [__init__.py](safety/__init__.py) | Safety module initialization |
| [budget_control.py](safety/budget_control.py) | **Budget Control** - Resource usage limits |
| [contract_guard.py](safety/contract_guard.py) | **Contract Guard** - Behavior constraint checking |
| [hallucination_check.py](safety/hallucination_check.py) | **Hallucination Detection** - LLM output verification |
| [integrity_check.py](safety/integrity_check.py) | **Integrity Check** - Value consistency verification |
| [risk_assessment.py](safety/risk_assessment.py) | **Risk Assessment** - Evaluates action risk levels |
| [sandbox.py](safety/sandbox.py) | **Sandbox** - Secure execution environment |

---

## 20. tests/ - Test Suite Directory

Contains 24 test files covering various system modules.

| File | Test Content |
|------|--------------|
| [__init__.py](tests/__init__.py) | Test package initialization |
| [conftest.py](tests/conftest.py) | pytest configuration - test fixtures and shared setup |
| [test_affect_integration.py](tests/test_affect_integration.py) | Affect system integration tests |
| [test_associative_memory.py](tests/test_associative_memory.py) | Associative memory tests |
| [test_axiology.py](tests/test_axiology.py) | Value system tests |
| [test_chat_interaction.py](tests/test_chat_interaction.py) | Chat interaction tests |
| [test_dynamic_setpoints.py](tests/test_dynamic_setpoints.py) | Dynamic setpoint tests |
| [test_e2e.py](tests/test_e2e.py) | End-to-end tests |
| [test_emotion_combinations.py](tests/test_emotion_combinations.py) | Emotion combination tests |
| [test_fixes.py](tests/test_fixes.py) | Fix verification tests |
| [test_fixes_verification.py](tests/test_fixes_verification.py) | Fix confirmation tests |
| [test_goal_compiler.py](tests/test_goal_compiler.py) | Goal compiler tests |
| [test_insight_quality.py](tests/test_insight_quality.py) | Insight quality tests |
| [test_integration.py](tests/test_integration.py) | Integration tests |
| [test_life_loop_integration.py](tests/test_life_loop_integration.py) | Life loop integration tests |
| [test_lifecycle.py](tests/test_lifecycle.py) | Lifecycle tests |
| [test_llm_features.py](tests/test_llm_features.py) | LLM feature tests |
| [test_memory.py](tests/test_memory.py) | Memory system tests |
| [test_organ_coordination.py](tests/test_organ_coordination.py) | Organ coordination tests |
| [test_organs.py](tests/test_organs.py) | Organ system tests |
| [test_p2_9_p1_8.py](tests/test_p2_9_p1_8.py) | Specific feature tests |
| [test_semantic_novelty.py](tests/test_semantic_novelty.py) | Semantic novelty tests |
| [test_tool_parser.py](tests/test_tool_parser.py) | Tool parser tests |
| [test_utility_normalization.py](tests/test_utility_normalization.py) | Utility normalization tests |
| [test_value_dimensions.py](tests/test_value_dimensions.py) | Value dimension tests |

---

## 21. tools/ - Tool System Module

Provides various external tools and capability interfaces.

| File | Function |
|------|----------|
| [__init__.py](tools/__init__.py) | Tool module initialization |
| [blackboard.py](tools/blackboard.py) | **Blackboard System** - Information sharing and workspace |
| [capability.py](tools/capability.py) | **Capability Tool** - System capability interface |
| [code_exec.py](tools/code_exec.py) | **Code Execution** - Secure code execution environment |
| [cost_model.py](tools/cost_model.py) | **Cost Model** - API call cost calculation |
| [dynamic_tool_registry.py](tools/dynamic_tool_registry.py) | **Dynamic Tool Registry** - Runtime tool registration |
| [embeddings.py](tools/embeddings.py) | **Vector Embeddings** - Text embedding tools |
| [file_ops.py](tools/file_ops.py) | **File Operations** - File read/write and management |
| [llm_api.py](tools/llm_api.py) | **LLM API** - LLM service calling interface |
| [llm_cache.py](tools/llm_cache.py) | **LLM Cache** - LLM response caching |
| [llm_client.py](tools/llm_client.py) | **LLM Client** - Unified LLM interface |
| [llm_orchestrator.py](tools/llm_orchestrator.py) | **LLM Orchestrator** - Multi-model coordination |
| [memory_tools.py](tools/memory_tools.py) | **Memory Tools** - Memory operation tools |
| [messaging.py](tools/messaging.py) | **Messaging System** - Internal message passing |
| [safe_executor.py](tools/safe_executor.py) | **Safe Executor** - Executor with AST safety checks |
| [tool_definitions.py](tools/tool_definitions.py) | **Tool Definitions** - Tool metadata definitions |
| [tool_executor.py](tools/tool_executor.py) | **Tool Executor** - Tool execution engine |
| [tool_protocol.py](tools/tool_protocol.py) | **Tool Protocol** - Standard protocol for tool calls |
| [tool_registry.py](tools/tool_registry.py) | **Tool Registry** - Manages all available tools |
| [tool_system_v2.py](tools/tool_system_v2.py) | **Tool System V2** - Unified tool calling interface |
| [vision.py](tools/vision.py) | **Vision Processing** - Image processing tools |
| [voice.py](tools/voice.py) | **Voice Processing** - Speech recognition and synthesis |
| [web_search.py](tools/web_search.py) | **Web Search** - Web search integration |

---

## 22. benchmarks/ - Performance Benchmarks

| File | Function |
|------|----------|
| [__init__.py](benchmarks/__init__.py) | Benchmark module initialization |
| [emotion_benchmark.py](benchmarks/emotion_benchmark.py) | **Emotion Benchmark** - Emotion system performance tests |
| [gxbs_runner.py](benchmarks/gxbs_runner.py) | **GXBS Runner** - GXBS benchmark running |
| [memory_benchmark.py](benchmarks/memory_benchmark.py) | **Memory Benchmark** - Memory system performance tests |
| [multi_model_benchmark.py](benchmarks/multi_model_benchmark.py) | **Multi-Model Benchmark** - Multi-model performance comparison |
| [personality_benchmark.py](benchmarks/personality_benchmark.py) | **Personality Benchmark** - Personality system tests |
| [run_gxbs.py](benchmarks/run_gxbs.py) | **Run GXBS** - GXBS benchmark launch script |
| [results/](benchmarks/results/) | **Results Directory** - Benchmark results storage |

---

## 23. web/ - Web Interface Module

Provides web interface for interaction.

### 23.1 Main Files

| File | Function |
|------|----------|
| [app.py](web/app.py) | **Flask Application** - Web server main program |
| [websocket_server.py](web/websocket_server.py) | **WebSocket Server** - Real-time communication |
| [server.log](web/server.log) | **Server Log** - Web server log |
| [mood-website.html](web/mood-website.html) | **Mood Display** - Emotion state display page |

### 23.2 static/ - Static Resources

#### css/

| File | Function |
|------|----------|
| [chat-styles.css](web/static/css/chat-styles.css) | **Chat Styles** - Chat interface CSS |
| [genesis-theme.css](web/static/css/genesis-theme.css) | **Genesis Theme** - Theme styles |
| [navigation.css](web/static/css/navigation.css) | **Navigation Styles** - Navigation bar CSS |
| [style.css](web/static/css/style.css) | **Main Styles** - Main stylesheet |

#### js/

| File | Function |
|------|----------|
| [app.js](web/static/js/app.js) | **Main App JS** - Main application logic |
| [chat-app.js](web/static/js/chat-app.js) | **Chat App JS** - Chat functionality implementation |
| [navigation.js](web/static/js/navigation.js) | **Navigation JS** - Navigation functionality implementation |

### 23.3 templates/ - HTML Templates

| File | Function |
|------|----------|
| [chat.html](web/templates/chat.html) | **Chat Page** - Chat interface template |
| [dashboard.html](web/templates/dashboard.html) | **Dashboard** - System dashboard |
| [debug.html](web/templates/debug.html) | **Debug Page** - Debug interface |
| [error.html](web/templates/error.html) | **Error Page** - Error display template |
| [index.html](web/templates/index.html) | **Home Page** - Website homepage |
| [monitor.html](web/templates/monitor.html) | **Monitor Page** - System monitoring interface |
| [navigation_test.html](web/templates/navigation_test.html) | **Navigation Test** - Navigation test page |
| [settings.html](web/templates/settings.html) | **Settings Page** - System settings interface |

### 23.4 web/artifacts/ & web/logs/

| Directory/File | Function |
|---------------|----------|
| [artifacts/web_run/](web/artifacts/web_run/) | Web runtime data storage |
| [logs/errors.json](web/logs/errors.json) | Web error log |
| [logs/genesis.json](web/logs/genesis.json) | Web runtime log |

---

## 24. artifacts/ - Runtime Data Directory

Stores various data generated during system runtime (named by timestamp).

### 24.1 Chat Session Data

Each chat session directory contains:

| File | Function |
|------|----------|
| `episodes.jsonl` | **Event Records** - Sequence of events that occurred |
| `states.jsonl` | **State Records** - System state change sequence |
| `tool_calls.jsonl` | **Tool Calls** - Tool call records |

Chat session examples:
- `chat_20260216_142723/`
- `chat_20260216_142739/`
- `chat_20260216_142820/`
- `chat_20260216_143121/`
- `chat_20260216_143156/`
- `chat_20260216_143536/`
- `chat_20260216_144817/`

### 24.2 Run Data

Each complete run contains:

| File/Directory | Function |
|---------------|----------|
| `episodes.jsonl` | **Event Records** |
| `states.jsonl` | **State Sequence** |
| `tool_calls.jsonl` | **Tool Call Records** |
| `final_state.json` | **Final State** - State at run completion |
| `override_state.json` | **Override State** - State override configuration |
| `value_parameters.json` | **Value Parameters** - Value system parameter snapshot |
| `evolution_archives/` | **Evolution Archives** - Evolution history |
| `evolution_instances/` | **Evolution Instances** - Evolution run instances |

Run examples:
- `run_20260223_110305_42/`
- `run_20260223_110330_42/`
- `run_20260223_110503_42/`

### 24.3 Test Run Data

| Directory | Function |
|-----------|----------|
| `test_chat/` | Chat test data |
| `test_chat_5dim/` | 5-dimensional value test data |
| `test_chat_debug/` | Debug test data |
| `test_chat_debug2/` | Debug test data 2 |
| `test_chat_final/` | Final test data |
| `test_chat_fix/` | Fix test data |
| `test_chat_fix2/` | Fix test data 2 |
| `test_chat_full/` | Full test data |
| `test_chat_llm/` | LLM test data |
| `test_chat_outcome/` | Outcome test data |
| `test_chat_success/` | Success test data |
| `test_chat_user_msg/` | User message test data |
| `test_context/` | Context test data |
| `test_llm_features/` | LLM feature test data |
| `test_run/` ~ `test_run8/` | Run test data 1-8 |
| `web_run/` | Web run data |

### 24.4 Dynamically Generated Limbs

| Directory | Function |
|-----------|----------|
| `limbs/v32_limb_*/` | **Dynamic Limbs** - Runtime-generated limb modules |
| `limbs/v32_limb_*/__init__.py` | Limb module implementation |

---

## 25. Cache Directories (Auto-generated)

### __pycache__/

Each Python module directory has this directory, storing `.pyc` compiled files.

### .pytest_cache/

| File | Function |
|------|----------|
| `.gitignore` | Git ignore configuration |
| `CACHEDIR.TAG` | Cache directory marker |
| `README.md` | Cache description |
| `v/cache/lastfailed` | Last failed test |
| `v/cache/nodeids` | Test node ID cache |

---

## Appendix A: 5-Dimensional Value System

### Value Dimension Definitions

| Dimension | English | Setpoint | Weight Bias | Description |
|-----------|---------|----------|-------------|-------------|
| Homeostasis | HOMEOSTASIS | 0.70 | 1.0 | Resource balance, stress management, system stability |
| Attachment | ATTACHMENT | 0.70 | 0.8 | Social connection, trust building, neglect avoidance |
| Curiosity | CURIOSITY | 0.60 | 0.7 | Novel exploration, information gain, pattern discovery |
| Competence | COMPETENCE | 0.75 | 1.0 | Task success, skill growth, sense of efficacy |
| Safety | SAFETY | 0.80 | 1.2 | Risk avoidance, loss prevention, safety margin |

### Compensation Mechanism (Plan B)

Removed dimensions are implemented through compensation mechanisms:

| Removed Dimension | Compensation Method | Core Class |
|-------------------|---------------------|------------|
| INTEGRITY | Hard constraint check | `IntegrityConstraintChecker` |
| CONTRACT | External signal weight boost | `ContractSignalBooster` |
| EFFICIENCY | Merged into HOMEOSTASIS | `EfficiencyMonitor` |
| MEANING | Merged into CURIOSITY | `MeaningTracker` |

---

## Appendix B: Autonomous Capabilities (V32 Style)

Implemented through `core/growth/limb_generator.py`:

| Capability | Method | Value System Linkage |
|------------|--------|---------------------|
| Devour | `devour(target_path)` | CURIOSITY driven |
| Grow | `grow_limb_v32(task, llm_func)` | COMPETENCE driven |
| Flex | `flex_limb_v32(filepath)` | SAFETY constrained |
| Autonomous | `autonomous_action(dopamine, stress, curiosity)` | Condition triggered |

---

## Appendix C: System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        GenesisX Digital Life                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                ┌─────────────┐│
│  │  perception │ ──→ Input Processing           │    tools    ││
│  │  Perception │                                │    Tools    ││
│  │   System    │                                │   System    ││
│  └──────┬──────┘                                └──────┬──────┘│
│         │                                              │       │
│         ▼                                              ▼       │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│  │  cognition  │ ←──→ │    core     │ ←──→ │   organs    │    │
│  │  Cognitive  │      │    Core     │      │    Organ    │    │
│  │   System    │      │   System    │      │   System    │    │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘    │
│         │                    │                    │           │
│         └────────────────────┼────────────────────┘           │
│                              │                                 │
│                              ▼                                 │
│                    ┌─────────────────┐                        │
│                    │     memory      │                        │
│                    │     Memory      │                        │
│                    │     System      │                        │
│                    └────────┬────────┘                        │
│                             │                                  │
│         ┌───────────────────┼───────────────────┐             │
│         │                   │                   │             │
│         ▼                   ▼                   ▼             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     │
│  │  axiology   │     │   affect    │     │  metabolism │     │
│  │   Value     │     │   Affect    │     │  Metabolism │     │
│  │   System    │     │   System    │     │   System    │     │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     │
│         │                   │                   │             │
│         └───────────────────┼───────────────────┘             │
│                             │                                  │
│                             ▼                                  │
│                    ┌─────────────────┐                        │
│                    │     safety      │                        │
│                    │     Safety      │                        │
│                    │     System      │                        │
│                    └────────┬────────┘                        │
│                             │                                  │
│                             ▼                                  │
│                    ┌─────────────────┐                        │
│                    │  persistence    │                        │
│                    │  Persistence    │                        │
│                    │     System      │                        │
│                    └─────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Entry Points

| Function | Command |
|----------|---------|
| Run System | `python run.py` |
| Interactive Chat | `python chat_interactive.py` |
| Web Interface | `python web/app.py` |
| Run Tests | `python run_tests.py` or `pytest` |
| Daemon Mode | `python daemon.py` |

---

**Documentation Version**: v1.3.0
**Last Updated**: 2026-03-04
