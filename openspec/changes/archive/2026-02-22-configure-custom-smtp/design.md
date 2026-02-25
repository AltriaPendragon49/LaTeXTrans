# Design: Configure Custom SMTP

## Architecture & Configuration
This change does not require any code modifications in the backend or frontend repositories. It is purely a configuration change operated in the Supabase Dashboard. 

### SpaceMail SMTP Configuration Details
The following configuration parameters will be applied in **Supabase Dashboard → Authentication → Emails → SMTP Settings**:

- **Enable Custom SMTP**: ON
- **Sender email**: `tomato@latextrans.online`
- **Sender name**: LaTeXTrans (or similar project name)
- **Host**: `mail.spacemail.com`
- **Port**: `465`
- **Username**: `tomato@latextrans.online`
- **Password**: The provided application/account password
- **Encryption**: SSL (handled via port 465 implicitly by Supabase)

## Reasoning and Trade-offs
Using a custom SMTP provider (SpaceMail) on a custom domain (`latextrans.online`) significantly improves user trust and email deliverability compared to the generic Supabase `noreply` addresses, and crucially, bypassing regional blocks that require VPN access during development.

It comes with the trade-off of maintaining custom DNS records (SPF, DKIM, DMARC) on the domain provider's side to ensure emails avoid spam folders.
