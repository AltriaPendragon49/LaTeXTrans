# Proposal: Configure Custom SMTP

## Context
Currently, the system uses Supabase's default built-in email service for Auth (sending confirmation emails). However, due to Supabase's policy changes and network access issues (requiring VPN to reliably use the default service), there is a need to migrate to a custom SMTP server. The chosen provider is SpaceMail (Spaceship).

## Proposed Change
Configure the SpaceMail custom SMTP server in the Supabase Dashboard, overriding the default email service. Ensure that all system authentication emails are reliably sent via `tomato@latextrans.online`.

## Capabilities and Requirements
- Modified Capability: `user-auth` - Update the operational requirement to clarify that system emails are delivered via a custom SMTP provider (Spaceship) rather than the default Supabase generic emailer, which resolves VPN/network blocking issues.
