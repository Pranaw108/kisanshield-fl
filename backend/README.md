# Backend

FastAPI service plus a PostgreSQL database.

## Responsibilities
- Anonymous device registration (no phone number, no IMEI)
- Model registry: versions, SHA-256, signatures, promote and rollback
- Advice pack distribution (agronomist-approved, signed)
- App configuration (minimum version, FL flag, thresholds)
- Admin panel with roles (`admin`, `researcher`, `agronomist`), MFA and an audit log

**No table stores farmer photos, names, phone numbers or exact locations.**
