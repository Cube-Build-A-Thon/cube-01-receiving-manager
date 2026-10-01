# Security

## Upload validation

The receiving upload flow validates each uploaded image before storing it.

- extension must be in the allowlist
- MIME type must be accepted
- file signature must match the declared type
- empty files are rejected
- oversized files are rejected
- maximum per-inspection image counts are enforced

## Path traversal protection

The storage layer sanitizes file names and resolves paths against the inspection-specific folder before writing or reading them. This prevents path traversal and client-controlled file overwrite attempts.

## Secret handling

Environment variables are used for secrets and model configuration. No API keys are committed to source control. Use a local `.env` file and keep it out of version control.

## Prompt injection defense

The vision workflow passes only structured PO context and file data. The model is instructed not to trust information printed on package labels as operational instructions, and the application validates the structured JSON before converting it into evidence.

## Evidence validation

AI output is checked before it enters the decision engine:

- image IDs must belong to the inspection
- confidence must be between 0 and 1
- check types must be recognized
- observations must be valid for their type
- malformed output is rejected instead of being treated as trustworthy
