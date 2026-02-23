## ADDED Requirements

### Requirement: CJK Font Compatibility Fix
The system MUST be capable of compiling translated Chinese LaTeX source code when the original document class or local style files load incompatible pdfLaTeX-specific font packages.

#### Scenario: Custom class loads T1 fontenc
A user translates a project where the document class (e.g., `atlasdoc.cls`) loads `\RequirePackage[T1]{fontenc}`, `newtxtext`, `newtxmath`, or `txfonts`. The system MUST dynamically scan and neutralize these conflicting font commands across the main `.tex` file and all sibling `.cls` and `.sty` files to ensure XeLaTeX and `ctex` can correctly render CJK Unicode characters.
