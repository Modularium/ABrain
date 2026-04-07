# Maintenance Guide

This document outlines recommended maintenance and security practices for running ABrain in production.

## Backup Strategy

- Regularly back up configuration files, session data and routing models.
- Store backups off-site and encrypt sensitive information.

## Update Cycle

- Check dependencies for security patches at least monthly.
- Apply updates in a staging environment before rolling out to production.
- Keep Docker base images up to date.

## Rollback & Staging

- Use `docker-compose` or Kubernetes to deploy new versions alongside the current release.
- Validate functionality with health checks before switching traffic.
- Keep previous images for quick rollback if issues arise.

## Access Control

- Enable authentication with `AUTH_ENABLED=true` and `API_AUTH_ENABLED=true`.
- Manage API keys via environment variables and rotate them regularly.
- Apply rate limiting on public routes to mitigate abuse.

## Log Retention

- Logs are written to `/data/logs/` per service with daily rotation.
- Monitor log volume and archive or purge files older than 30 days.
