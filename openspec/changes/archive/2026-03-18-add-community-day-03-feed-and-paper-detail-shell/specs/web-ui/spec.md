## MODIFIED Requirements
### Requirement: Responsive Web Dashboard
The system MUST provide a responsive web-based translation workspace while allowing the product homepage to become a community browse surface.

#### Scenario: User navigates to the translation workspace
Given the backend server is running
When the user accesses `/translate`
Then the Dashboard page should be displayed
And a prominent input field for ArXiv ID should be visible
And shared sidebar navigation should remain available
