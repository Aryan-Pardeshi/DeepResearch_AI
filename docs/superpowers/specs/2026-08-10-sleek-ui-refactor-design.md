# Design Spec: Sleek Vercel/Linear Style Minimalist UI Refactor

## Overview
Refactor the UI to eliminate visual noise, bloated plasma orbs, multi-colored neon borders, and duplicate metric strips. Implement a clean, high-end Vercel/Linear-style dark aesthetic.

## Visual Design Improvements

### 1. Unified Minimalist Ambient Background
- Remove all `.hero-plasma-container`, `.plasma-orb`, `.rm-ambient-aura`, and `.hero-card-gradient-border` elements.
- Apply a single, top-level ambient radial background spotlight to `body`:
  `background: #09090b radial-gradient(circle at 50% -10%, rgba(99, 102, 241, 0.15), transparent 50%) no-repeat;`

### 2. Crisp Glassmorphism Input Cards
- Clean input cards (`.search-box-container`, `.rm-input-card`, `.card`) with subtle borders:
  - `background: rgba(18, 18, 22, 0.75)`
  - `border: 1px solid rgba(255, 255, 255, 0.08)`
  - `box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4)`
- Hover/Focus: Crisp subtle indigo accent border (`border-color: rgba(99, 102, 241, 0.4)`).

### 3. Streamlined Quick Prompt Template Chips
- Replace bulky template card blocks with a horizontal row of sleek quick-prompt pills (`.template-prompt-chip`):
  - Compact icon + label pill
  - Subtle hover transition
