# Design System Specification

## 1. Overview & Creative North Star: "The Academic Curator"
This design system is built to transform a technical utility into a high-end editorial experience. Moving away from the cluttered, utilitarian aesthetic of traditional LaTeX editors, this system adopts the **"Academic Curator"** persona. 

The experience should feel like a premium digital monograph: precise, airy, and authoritative. We achieve this through **Organic Minimalism**—balancing the rigid logic of code with the soft, human touch of oversized radiuses and a warm, off-white canvas. By prioritizing intentional asymmetry and deep breathing room (whitespace), we ensure that the user’s focus remains entirely on the intellectual content.

---

## 2. Colors: Tonal Depth over Structural Lines
The palette is rooted in a warm, sophisticated neutral base, punctuated by a scholarly "Oxblood" red.

### Palette Highlights
*   **Primary (`#b61722`):** Used for critical actions and brand presence.
*   **Surface (`#fcf9f8`):** Our foundation. It is a soft, warm white that reduces eye strain compared to pure `#FFFFFF`.
*   **Tertiary/Neutrals (`#5b5c5c`):** Used for secondary information to maintain a muted, high-contrast hierarchy.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders to section off the UI. Standard dividers are strictly prohibited. Instead:
*   **Background Shifts:** Define areas by placing a `surface-container-low` sidebar against a `surface` main content area.
*   **Nesting:** Treat the UI as layers of fine stationery. An inner container (e.g., a code editor) should use `surface-container-highest` to sit "inside" a `surface-container` page.

### Signature Textures
To avoid a "flat" or "bootstrapped" look, apply a subtle linear gradient to primary CTA buttons: from `primary` (`#b61722`) to `primary-container` (`#da3437`). This provides a physical, tactile soul to the interaction points.

---

## 3. Typography: The Editorial Hierarchy
We utilize **Inter** across the entire system. Its mathematical precision complements the LaTeX subject matter while remaining highly legible in dense technical contexts.

*   **Display Scales:** Use `display-lg` (3.5rem) with tightened letter-spacing (-0.02em) for empty states or hero headers to create an editorial, magazine-like feel.
*   **The Narrative Flow:** Headlines (`headline-md`) should always have ample `margin-bottom` (using Spacing Scale `8` or `10`) to let the section "breathe" before the body text begins.
*   **Functional Labels:** Use `label-sm` (0.6875rem) in all-caps with increased letter-spacing (+0.05em) for metadata or small UI hints to distinguish them from reading text.

---

## 4. Elevation & Depth: Tonal Layering
In this system, depth is a matter of light and material, not artificial lines.

*   **The Layering Principle:** Hierarchy is achieved by stacking. A card component should be `surface-container-lowest` (pure white) placed on a `surface-container` (soft grey) background. This creates a "lift" through natural contrast.
*   **Ambient Shadows:** For floating elements like tooltips or modals, use extreme diffusion. 
    *   *Shadow:* `0 20px 40px rgba(27, 28, 28, 0.06)`. 
    *   *Note:* The shadow color is a tint of our `on-surface` color, never pure black.
*   **The "Ghost Border" Fallback:** If high-contrast accessibility is required, use the `outline-variant` token at **15% opacity**. It should be felt, not seen.
*   **Glassmorphism:** For the side navigation or top headers, apply a `backdrop-filter: blur(20px)` combined with a semi-transparent `surface` color. This allows the document content to bleed through softly as the user scrolls, creating a sense of environmental depth.

---

## 5. Components: The Primitive Set

### Cards & Containers
*   **Radius:** Always use `xl` (3rem/48px) for main content cards and `lg` (2rem/32px) for nested elements.
*   **Spacing:** Use a minimum padding of `8` (2.75rem) for large cards to maintain the "Academic Curator" whitespace standards.

### Buttons
*   **Primary:** High-pill shape (`full` rounding), gradient-filled, with `on-primary` text.
*   **Secondary:** No background, no border. Use `primary` text color with a `surface-container-high` hover state.
*   **Tertiary:** `surface-variant` background with `on-surface-variant` text for low-priority utility actions.

### Input Fields (The Translation Cells)
*   **Styling:** Remove the traditional bottom line or box. Use a `surface-container-low` filled background with `md` (1.5rem) rounding.
*   **Focus State:** Instead of a heavy border, the background should shift to `surface-container-highest` with a subtle `primary` glow (ambient shadow).

### Side Navigation
*   **Layout:** Clean, vertical list with no dividers. 
*   **Active State:** Use a soft "pill" highlight (Primary Container at 10% opacity) with a `primary` vertical indicator bar on the left, but keep the bar's ends rounded.

### Additional Specialty Components
*   **LaTeX Preview Bubbles:** Small, `surface-container-lowest` floating tiles with `md` rounding that appear when hovering over complex formulas.
*   **Progress Steppers:** Use a thin line using `outline-variant` (20% opacity) with `primary` dots to show translation stages.

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical layouts (e.g., a wide left column for translation and a narrow right column for metadata).
*   **Do** leverage the `surface-container` tiers to create hierarchy.
*   **Do** use "Ghost Borders" for inputs to maintain accessibility without breaking the minimalist flow.
*   **Do** allow LaTeX formulas to have their own "breathing room" container with `xl` rounding.

### Don't
*   **Don't** use 1px solid dividers or borders between list items. Use vertical spacing (Scale `4`).
*   **Don't** use sharp corners. Everything must feel approachable and organic.
*   **Don't** use pure black (`#000000`) for text; use `on-surface` (`#1b1c1c`) to maintain the premium, muted tone.
*   **Don't** cram information. If a screen feels full, increase the page height and use more whitespace.