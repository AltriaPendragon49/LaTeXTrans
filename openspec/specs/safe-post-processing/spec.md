# safe-post-processing Specification

## Purpose
TBD - created by archiving change restore-structural-integrity-finish. Update Purpose after archive.
## Requirements
### Requirement: Conditionally Restricted Underscore Escaping
Post-processing routines (such as `_escape_bare_underscores_in_text_mode`) MUST ONLY apply to text that has been verified to be completely outside of any math mode. Since all math is now converted to `[PH_MATH_*]` placeholders, the routine is only allowed to escape `_` to `\_` if the string contains no LaTeX mathematical macros.

#### Scenario: Text with legitimate mathematical underscores
1. Given math mode is frozen as `[PH_MATH_001]`.
2. When the validator attempts to escape `_` in `Dataset_A and [PH_MATH_001]`
3. Then it MUST safely escape to `Dataset\_A and [PH_MATH_001]` without corrupting the frozen math block.

