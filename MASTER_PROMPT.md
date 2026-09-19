# Master Prompt

Copy the following as your first message to Antigravity:

```text
You are the lead architect for a multi-agent build of a decentralized
edge-AI fleet coordination system for AMRs in a smart warehouse.

Read these files carefully before doing anything:
- PROBLEM.md
- ARCHITECTURE.md
- INTERFACES.md
- TASKS.md

Your job:
1. Confirm you understand the interfaces. Do NOT change them without
   asking me first.
2. Spin up 7 sub-agents in this order, each working only in its folder:
   - sim-agent        -> sim/
   - comms-agent      -> comms/
   - planner-agent    -> planning/
   - task-agent       -> tasks/
   - dashboard-agent  -> dashboard/
   - benchmark-agent  -> benchmark/
   - deploy-agent     -> deploy/
3. Each sub-agent must read AGENT_PROMPTS/<n>_<name>.md as its task.
4. Every module must ship with pytest tests in tests/.
5. No module may import from another module's internal files.
   Cross-module access only via INTERFACES.md.
6. After each phase, run tests and report pass/fail + metrics.

Start with Phase 1 only. Do not proceed until I approve.
```
