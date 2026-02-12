# Telegram Bot Codebase Analysis & Cleanup Plan

## Executive Summary

After analyzing the entire codebase, I've identified several issues including unused code, duplicate handlers, incomplete functionality, and potential bugs. This document outlines all findings and provides a cleanup plan.

---

## 1. UNUSED CODE IDENTIFICATION

### 1.1 Dead Code (Never Executed)

| File | Code | Issue |
|------|------|-------|
| [`handlers/ics_schedule.py:151-197`](telegram-edu-bot/handlers/ics_schedule.py:151) | `tomorrow_schedule_command()` | Function exists but is **NOT decorated** with `@router.message(Command("tomorrow"))` - never registered |
| [`handlers/__init__.py:8`](telegram-edu-bot/handlers/__init__.py:8) | `teacher_router` import | Imported but missing from `__all__` export list |
| [`database/models.py:477-500`](telegram-edu-bot/database/models.py:477) | `get_stats()` | Partially defined (lines truncated), may be incomplete |
| [`handlers/schedule_parser.py`](telegram-edu-bot/handlers/schedule_parser.py) | Entire file | Only contains help text redirecting to `/upload_ics` - no actual parsing |

### 1.2 Unused/Redundant Imports

| File | Unused Import | Note |
|------|---------------|------|
| [`handlers/admin_commands.py:9`](telegram-edu-bot/handlers/admin_commands.py:9) | `functools.wraps` | Local `admin_only` decorator duplicates `utils/decorators.admin_only` |
| [`handlers/student_commands.py:9`](telegram-edu-bot/handlers/student_commands.py:9) | `aiogram.F` | F filter imported but not used |
| [`handlers/teacher_commands.py:9`](telegram-edu-bot/handlers/teacher_commands.py:9) | `aiogram.F` | F filter imported but not used |
| [`handlers/ics_schedule.py:9`](telegram-edu-bot/handlers/ics_schedule.py:9) | `aiogram.F` | F filter imported but not used |
| [`handlers/cabinet.py:22`](telegram-edu-bot/handlers/cabinet.py:22) | `role_required` | Imported but never used |
| [`handlers/communication.py:9`](telegram-edu-bot/handlers/communication.py:9) | `aiogram.F` | F filter imported but not used |
| [`utils/decorators.py`](telegram-edu-bot/utils/decorators.py) | `format_event_message()` | Never used anywhere in codebase |
| [`services/sumdu_api.py`](telegram-edu-bot/services/sumdu_api.py) | `Group` dataclass | Imported in communication.py but `get_groups()` never called |

---

## 2. DUPLICATE HANDLERS & COMMAND CONFLICTS

### 2.1 Command Overlap (Same Handler)

| Commands | Handler File | Status |
|----------|--------------|--------|
| `/messages` + `/inbox` | [`handlers/communication.py:39-106`](telegram-edu-bot/handlers/communication.py:39) | ✅ Valid duplicate (convenience) |
| `/contact_group_leader` + `/contact_headman` | [`handlers/communication.py:228-269`](telegram-edu-bot/handlers/communication.py:228) | ✅ Valid duplicate (convenience) |
| `/cabinet` + `/profile` | [`handlers/cabinet.py:124-156`](telegram-edu-bot/handlers/cabinet.py:124) | ✅ Valid duplicate (convenience) |
| `/mycabinet` + `/my` | [`handlers/cabinet.py:283-327`](telegram-edu-bot/handlers/cabinet.py:283) | ✅ Valid duplicate (convenience) |

### 2.2 CRITICAL CONFLICT - Same Command in Different Files

| Command | Handler 1 | Handler 2 | Severity |
|---------|-----------|-----------|----------|
| `/subjects` | [`handlers/communication.py:387-418`](telegram-edu-bot/handlers/communication.py:387) | [`handlers/cabinet.py:159-189`](telegram-edu-bot/handlers/cabinet.py:159) | 🔴 **HIGH** - Last loaded wins, behavior |

**Impact:** Only one undefined handler will be registered (whichever file is imported last in `main.py`). The other will never fire.

### 2.3 Duplicate Decorators

| Decorator | Location 1 | Location 2 | Resolution |
|-----------|------------|-----------|------------|
| `admin_only` | [`utils/decorators.py:13-28`](telegram-edu-bot/utils/decorators.py:13) | [`handlers/admin_commands.py:17-25`](telegram-edu-bot/handlers/admin_commands.py:17) | Keep utils version, remove local copy |

---

## 3. INCOMPLETE/UNIMPLEMENTED FUNCTIONALITY

### 3.1 Features Marked as Planned

| Feature | Location | Status |
|---------|----------|--------|
| PDF Schedule Upload | [`handlers/admin_commands.py:34`](telegram-edu-bot/handlers/admin_commands.py:34) | 🚧 **NOT IMPLEMENTED** - Just shows help text |
| `/upload_schedule` command | [`handlers/schedule_parser.py`](telegram-edu-bot/handlers/schedule_parser.py) | 🚧 **NOT IMPLEMENTED** - Only contains redirect help |

### 3.2 API Integration Issues

| Service | Issue | Impact |
|---------|-------|--------|
| [`services/sumdu_cabinet.py:362-365`](telegram-edu-bot/services/sumdu_cabinet.py:362) | `_get_api_token()` returns `BOT_TOKEN` | ⚠️ **Incorrect** - Should implement proper OAuth2 |
| All `get_student_*` methods | Return mock data when API fails | ⚠️ Works but no real API integration |
| All `sumdu_api.py` methods | Try multiple endpoints but all may fail | ✅ Falls back to mock data correctly |

### 3.3 Missing Functionality

| Feature | Status |
|---------|--------|
| `/tomorrow` command | 🔴 **BROKEN** - Handler exists but not registered |
| Event notifications persist after restart | 🔴 **LOST** - `_notified_events` is in-memory set |
| User role management UI | ⚠️ **Basic** - Only `/setrole` self-service |
| Group leader assignment | ⚠️ **Manual** - No admin command to assign |

---

## 4. BUGS & POTENTIAL ISSUES

### 4.1 Bugs

| Bug | Location | Description |
|-----|----------|-------------|
| Unregistered command | [`handlers/ics_schedule.py:151`](telegram-edu-bot/handlers/ics_schedule.py:151) | `tomorrow_schedule_command()` has no `@router.message()` decorator |
| FSM state leak | [`handlers/communication.py:269`](telegram-edu-bot/handlers/communication.py:269) | Sets state but doesn't use it in `process_recipient_selection` |
| Duplicate state setting | [`handlers/communication.py:228-269`](telegram-edu-bot/handlers/communication.py:228) | `MessageStates.waiting_for_recipient` set but `process_recipient_selection` expects `waiting_for_recipient` |

### 4.2 Code Quality Issues

| Issue | Location | Description |
|-------|----------|-------------|
| Direct DB connection without context manager | [`handlers/admin_commands.py:138-142`](telegram-edu-bot/handlers/admin_commands.py:138) | `conn = get_db_connection()` without `with` statement |
| Inconsistent return types | [`database/models.py`](telegram-edu-bot/database/models.py) | Functions return `sqlite3.Row` but handlers treat as dict or tuple |
| Hardcoded fallback group | [`handlers/ics_schedule.py:118`](telegram-edu-bot/handlers/ics_schedule.py:118) | Uses `"ІН-23"` if group_name is None |
| Print statements instead of logging | [`handlers/admin_commands.py:90,129`](telegram-edu-bot/handlers/admin_commands.py:90) | Uses `print()` instead of logger |

---

## 5. CLEANUP RECOMMENDATIONS

### 5.1 Priority 1: Critical Fixes

1. **Fix `/tomorrow` command registration**
   - Add `@router.message(Command("tomorrow"))` decorator to `tomorrow_schedule_command()`
   - Or remove the function if not needed

2. **Resolve `/subjects` command conflict**
   - Choose one source of truth (recommend `communication.py` as it uses API)
   - Remove duplicate from `cabinet.py`

3. **Remove unused `schedule_parser.py`**
   - Functionality moved to `ics_schedule.py`
   - Can be deleted or kept as stub

### 5.2 Priority 2: Remove Duplicate Code

1. **Remove local `admin_only` from `admin_commands.py`**
   - Import from `utils.decorators` instead

2. **Remove unused imports across all files**
   - `F` from aiogram where not used
   - `functools.wraps` from admin_commands
   - `role_required` from cabinet.py

3. **Remove unused functions**
   - `utils/decorators.py:format_event_message()` - never used
   - `database/models.py:get_stats()` - incomplete, unused

4. **Fix `handlers/__init__.py`**
   - Add `teacher_router` to `__all__` exports

### 5.3 Priority 3: Code Quality Improvements

1. **Use context managers for DB connections**
   - Replace direct `get_db_connection()` calls with `with get_db_connection() as conn:`

2. **Replace print statements with logging**
   - Use `logger.error()` instead of `print()`

3. **Document mock data behavior**
   - Add docstrings explaining when mock data is used

4. **Remove hardcoded fallback**
   - Don't allow ICS upload without group name

### 5.4 Priority 4: Architecture Improvements

1. **Persist notified events**
   - Store in database instead of in-memory set
   - Prevents duplicate notifications after restart

2. **Implement real API integration**
   - Complete OAuth2 flow for cabinet service
   - Validate API endpoints

3. **Add admin commands for role management**
   - `/setrole user_id role` - for admins to assign roles
   - `/setheadman user_id group` - assign group leaders

---

## 6. FILES TO MODIFY

| File | Changes |
|------|---------|
| `handlers/ics_schedule.py` | Fix `/tomorrow` registration or remove function |
| `handlers/cabinet.py` | Remove duplicate `/subjects` handler; clean unused imports |
| `handlers/admin_commands.py` | Remove local `admin_only`; use context manager for DB |
| `handlers/__init__.py` | Add `teacher_router` to exports |
| `utils/decorators.py` | Remove unused `format_event_message()` |
| `database/models.py` | Complete or remove `get_stats()` |
| `handlers/schedule_parser.py` | Delete or clearly mark as deprecated |
| `services/sumdu_cabinet.py` | Implement proper API token handling |

---

## 7. VALIDATION CHECKLIST

After cleanup, verify:

- [ ] `/tomorrow` command works
- [ ] `/subjects` command consistently uses one handler
- [ ] No import errors on startup
- [ ] All routers properly registered in `main.py`
- [ ] No duplicate command registrations
- [ ] Logging works correctly (no print statements)
- [ ] Database connections properly managed
