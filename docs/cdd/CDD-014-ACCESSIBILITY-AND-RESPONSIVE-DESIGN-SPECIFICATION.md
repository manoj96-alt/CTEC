# CDD-014 — Accessibility and Responsive-Design Specification

Version: 1.0

Target: WCAG 2.2 AA.

- All actions and routes operate by keyboard with logical DOM/focus order, visible focus, skip link,
  landmark structure, and no keyboard trap except a correctly managed modal.
- Navigation places focus on the new page heading; dialogs focus their heading/first field and
  restore focus to the launcher. Error submission focuses an error summary linked to invalid fields.
- Inputs have persistent labels, descriptions, required indication, and programmatic errors. Status
  changes use a polite live region; urgent session loss uses assertive announcement sparingly.
- Color is never the sole status cue. Icons have text labels. Normal text meets 4.5:1 contrast,
  large text 3:1, and interactive/non-text boundaries 3:1.
- Stage progress is an ordered list/timeline with textual state; recommendations separately state
  standing and actionability. Tables have captions and headers; cards preserve the same reading
  order on narrow screens.
- Respect `prefers-reduced-motion`; no essential information depends on animation. Touch targets
  meet WCAG 2.2 target-size expectations.
- Layout supports 320 CSS px through wide desktop, 200% zoom, text reflow, long identifiers, and
  localized-length labels without horizontal page scrolling. Dense tables may use accessible
  responsive cards rather than clipped columns.
- Automated axe-style checks, semantic queries, keyboard tests, and contrast checks supplement—not
  replace—manual keyboard, VoiceOver/NVDA, zoom/reflow, reduced-motion, and mobile viewport review.
