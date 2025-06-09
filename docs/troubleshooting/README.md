# Troubleshooting Guide

This directory contains scripts and documentation created during production troubleshooting sessions.

## Query Performance Issues

If queries are returning empty results, see:
- `FIX_QUERIES_NOW.md` - Quick fix guide
- `fix_queries_powershell.ps1` - PowerShell script for Windows users
- `URGENT_RUN_THIS_SQL.sql` - Direct SQL commands

## Database Issues

- `check_embeddings.sql` - SQL queries to diagnose embedding issues
- `fix_database_now.py` - Python script to fix database indexes

## Deployment Monitoring

- `monitor_deployment.sh` - Script to monitor Render deployments
- `CRITICAL_FIX_STATUS.md` - Production fix status tracking

## Note

These files were created during actual production troubleshooting and may contain specific fixes that have already been applied. They're kept here for reference and future similar issues.