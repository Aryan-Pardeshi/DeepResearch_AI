# Design Spec: DeepSearch Approval & Workspace Backlight Glow

## Overview
Extend the purple ambient plasma backlight and glowing card halo effects into DeepSearch Mode's **Approval Console** (`#approval-panel`) and **Execution Workspace** (`#workspace-panel`).

## UI Component Glow Enhancements

### 1. Ambient Plasma Backlight Orbs in Approval & Workspace Views
- Insert `<div class="hero-plasma-container">` into `#approval-panel` and `#workspace-panel`.
- Positioned relative to section containers to project ambient floating plasma orbs behind cards and reports.

### 2. DeepSearch Card Backlight Halo (`.rm-glow-card`)
- Apply `.rm-glow-card` to:
  - Approval Panel Cards (`Problem Statement`, `Proposed Research Plan`, `Revisions Console`)
  - Workspace Report Container (`.report-workspace`)
  - Parallel Researchers Sidebar (`.workers-sidebar`)

### 3. Active Execution Workspace Pulse
- During active DeepSearch SSE streaming (`handlePlanResearch`, worker streams, report synthesis), `.active-execution` class is toggled on `.report-workspace` and `.workers-sidebar` to produce a glowing backlight aura.
