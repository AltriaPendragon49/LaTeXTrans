# Design System Specification: The Scholarly Monolith

## 1. Overview & Creative North Star: "The Digital Curator"
This design system rejects the cluttered, hyper-dense aesthetic of traditional academic repositories. Our Creative North Star is **The Digital Curator**—an interface that feels like a high-end, quiet library wing where the architecture disappears to let the knowledge breathe. 

We achieve a "Signature" look by moving away from standard grid-based templates. Instead, we utilize **intentional asymmetry**, **layered tonal depth**, and **oversized radiuses** to create a fluid, editorial experience. By replacing rigid borders with soft transitions in the `surface-container` spectrum, we ensure the platform feels precise and modern, moving far beyond the utility-first red schemes of competitors.

---

## 2. Colors & Surface Architecture
The palette is rooted in a professional blue (`primary`: #1D4ED8), balanced by a sophisticated neutral base that leans into cool, scholarly tones.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to define sections or containers. 
- Separation must be achieved through **Background Color Shifts**. For example, a `surface-container-low` sidebar sitting atop a `surface` background.
- Use the `surface-container` tiers (Lowest to Highest) to create "nested" depth. Treat the UI as physical layers of fine vellum paper.

### Surface Hierarchy & Nesting
- **Base Layer:** `surface` (#faf8ff) – The expansive "white space."
- **Navigation/Sidebars:** `surface-container-low` (#f3f2fe) – For secondary structural elements.
- **Primary Content Cards:** `surface-container-lowest` (#ffffff) – Used for high-contrast legibility of text.
- **Interactions/Overlays:** `surface-container-high` (#e8e7f3) – For subtle emphasis.

### The "Glass & Gradient" Rule
To elevate the primary blue beyond a "flat brand color," apply subtle linear gradients (e.g., `primary` to `primary-container`) on hero buttons and primary CTAs. For floating navigation or modal overlays, use **Glassmorphism**: 
- **Backdrop Blur:** 20px - 40px.
- **Fill:** `surface` at 70% opacity.
- This creates a "frosted glass" effect that allows background content to bleed through, softening the layout's edges.

---

## 3. Typography: Editorial Precision
We utilize **Inter** exclusively, but we treat it with editorial weight to convey authority.

- **Display Scales (`display-lg` to `display-sm`):** Reserved for landing pages and major section headers. Use -0.02em letter spacing to maintain "tight" academic precision.
- **Headline & Title Scales:** Use `on-surface` (#1a1b23) for maximum contrast. These define the hierarchy of a paper or abstract.
- **Body Scales:** `body-lg` (1rem) is our workhorse for readability. Use `on-surface-variant` (#434655) for long-form secondary text to reduce eye strain.
- **Labels:** Small, all-caps treatments with +0.05em tracking for metadata (e.g., "PUBLISHED DATE" or "DOI").

---

## 4. Elevation & Depth: Tonal Layering
Traditional shadows are too "tech-startup." We use **Tonal Layering** to define importance.

- **The Layering Principle:** Place a `surface-container-lowest` (pure white) card on a `surface-container-low` (pale lilac-white) section. This creates a soft, natural lift without a single pixel of shadow.
- **Ambient Shadows:** Only use shadows for floating elements (Modals, Hovered Cards). 
  - **Blur:** 48px to 64px.
  - **Color:** `on-surface` at 4% opacity. 
  - This mimics natural, ambient light in a gallery setting.
- **The "Ghost Border" Fallback:** If accessibility requires a container boundary, use `outline-variant` (#c4c5d7) at **15% opacity**. Never 100%.

---

## 5. Components & Primitives

### Cards & Containers
- **Corner Radius:** All primary containers must use `xl` (32px / 2rem). Secondary elements (buttons, inputs) use `md` (1.5rem).
- **No Dividers:** Forbid the use of `<hr>` or divider lines. Use `spacing-8` (2.75rem) or a shift in `surface-container` color to separate list items.

### Buttons
- **Primary:** `primary` (#0037b0) background with `on-primary` text. Use a subtle 5% gradient transition to `primary-container`.
- **Secondary:** `secondary-container` (#b0befe) background. No border.
- **Tertiary:** `surface` background with `primary` text. Focus states use a `surface-variant` wash.

### Input Fields
- **Styling:** Use `surface-container-lowest` for the field background to ensure it "pops" against the `surface` background.
- **States:** Error states use `error` (#ba1a1a) text labels but keep the container background `error-container` (#ffdad6) at 40% opacity for a soft, integrated look.

### The "Abstract" Chip
- A specialized component for scholarly tags. Use `surface-container-highest` with `label-md` typography. The radius must be `full` (9999px) to contrast with the `xl` radius of the parent cards.

---

## 6. Do’s and Don'ts

### Do:
- **Do** use generous whitespace (`spacing-12` and `spacing-16`) to separate distinct thoughts or sections.
- **Do** use `primary` sparingly. It is a "surgical" accent for navigation and critical actions.
- **Do** lean into asymmetry. A wider left margin for body text creates an "annotated" editorial feel.

### Don’t:
- **Don’t** use 1px borders. Ever.
- **Don’t** use pure black (#000000). Always use `on-surface` (#1a1b23) for text to maintain a premium, ink-on-paper feel.
- **Don’t** use tight corner radiuses. Small corners feel "standard"; 32px corners feel "designed."
- **Don’t** use drop shadows as a default. If the hierarchy isn't clear through background colors, rethink the layout.