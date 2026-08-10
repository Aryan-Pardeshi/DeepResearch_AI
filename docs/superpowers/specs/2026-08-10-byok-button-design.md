# Technical Specification: Bring Your Own Key (BYOK) Button Update

## Overview
This specification details the design for updating the frontend header settings button into a key button with the label "Bring your own key".

## Requirements
1. **Button Icon & Text**:
   - Change settings icon (`settings`) to key icon (`key`).
   - Add adjacent text label: `Bring your own key`.
2. **Button Styling**:
   - Styled as a sleek indigo/purple pill button (`.btn-byok`) with glassmorphism and subtle hover glow.
3. **Functionality**:
   - Clicking the button opens the existing System Settings configuration modal (`settings-modal`).

## File Changes
- `research-bot/frontend/index.html`: Replace `<button id="settings-btn">` icon content with key icon + text span.
- `research-bot/frontend/style.css`: Add `.btn-byok` CSS classes for light and dark modes.
