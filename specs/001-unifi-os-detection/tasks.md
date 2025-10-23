# Tasks: UniFi API Path Detection and Adaptation

**Input**: Design documents from `/specs/001-unifi-os-detection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/detection-api.md

**Tests**: Unit and integration tests are included as this is infrastructure-critical code.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (as per plan.md)
- Primary modification: `src/managers/connection_manager.py`
- Supporting changes: `src/bootstrap.py`, `src/config/config.yaml`, `devtools/dev_console.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for detection feature

- [X] T001 Review existing `src/managers/connection_manager.py` to understand current connection flow
- [X] T002 Review existing `src/bootstrap.py` to understand configuration loading
- [X] T003 [P] Create test directory structure `tests/unit/` and `tests/integration/` if not exists
- [X] T004 [P] Install test dependencies: `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`, `aioresponses>=0.7.0`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Add `UNIFI_CONTROLLER_TYPE` environment variable parsing in `src/bootstrap.py`
- [X] T006 Add controller type validation logic in `src/bootstrap.py` (valid values: auto, proxy, direct)
- [X] T007 [P] Add controller_type configuration section to `src/config/config.yaml`
- [X] T008 Add `_unifi_os_override` attribute to ConnectionManager `__init__()` in `src/managers/connection_manager.py`

**Checkpoint**: Configuration foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic UniFi OS Detection (Priority: P1) 🎯 MVP

**Goal**: Automatically detect which API path structure the controller requires by testing both patterns, eliminating 404 errors on UniFi OS controllers without manual configuration.

**Independent Test**: Connect to a UniFi OS controller (UDM-Pro, Cloud Gateway, self-hosted UniFi OS 4.x) and verify that API calls succeed without setting `UNIFI_CONTROLLER_TYPE`. Also test with a standard controller to verify direct path detection works.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Create unit test for UniFi OS detection in `tests/unit/test_path_detection.py` - test_detects_unifi_os_correctly
- [X] T010 [P] [US1] Create unit test for standard controller detection in `tests/unit/test_path_detection.py` - test_detects_standard_controller
- [X] T011 [P] [US1] Create unit test for detection failure in `tests/unit/test_path_detection.py` - test_detection_failure_returns_none
- [X] T012 [P] [US1] Create integration test for path interception in `tests/integration/test_path_interceptor.py` - test_path_interception_applies_correctly
- [X] T013 [P] [US1] Create integration test for UniFi OS requests in `tests/integration/test_path_interceptor.py` - test_unifi_os_requests_use_proxy_paths

### Implementation for User Story 1

- [X] T014 [US1] Implement `detect_unifi_os_proactively()` method in `src/managers/connection_manager.py` (probe-based detection logic)
- [X] T015 [US1] Add detection result logging in `detect_unifi_os_proactively()` in `src/managers/connection_manager.py`
- [X] T016 [US1] Modify `ConnectionManager.initialize()` to call detection when `UNIFI_CONTROLLER_TYPE=auto` in `src/managers/connection_manager.py`
- [X] T017 [US1] Modify `ConnectionManager.request()` to apply `_unifi_os_override` flag in `src/managers/connection_manager.py`
- [X] T018 [US1] Add try/finally block in `ConnectionManager.request()` to restore original `is_unifi_os` flag in `src/managers/connection_manager.py`
- [X] T019 [US1] Add detection result display to `devtools/dev_console.py` connection initialization output
- [X] T020 [US1] Verify unit tests pass: `pytest tests/unit/test_path_detection.py -v`
- [X] T021 [US1] Verify integration tests pass: `pytest tests/integration/test_path_interceptor.py -v`

**Checkpoint**: At this point, automatic detection should work for both UniFi OS and standard controllers. Test independently with both controller types.

---

## Phase 4: User Story 2 - Manual Override Configuration (Priority: P2)

**Goal**: Provide explicit configuration to force specific path structures for edge cases, custom setups, or detection failures.

**Independent Test**: Set `UNIFI_CONTROLLER_TYPE=proxy` and verify system uses proxy paths without detection. Set `UNIFI_CONTROLLER_TYPE=direct` and verify system uses direct paths without detection. Set invalid value and verify fallback to auto-detection with warning.

### Tests for User Story 2

- [X] T022 [P] [US2] Create unit test for manual proxy override in `tests/unit/test_path_detection.py` - test_manual_override_proxy
- [X] T023 [P] [US2] Create unit test for manual direct override in `tests/unit/test_path_detection.py` - test_manual_override_direct
- [X] T024 [P] [US2] Create unit test for invalid config value in `tests/unit/test_path_detection.py` - test_invalid_controller_type_falls_back_to_auto
- [X] T025 [P] [US2] Create integration test for forced proxy mode in `tests/integration/test_path_interceptor.py` - test_manual_proxy_mode_skips_detection

### Implementation for User Story 2

- [X] T026 [US2] Add manual override handling in `ConnectionManager.initialize()` for `UNIFI_CONTROLLER_TYPE=proxy` in `src/managers/connection_manager.py`
- [X] T027 [US2] Add manual override handling in `ConnectionManager.initialize()` for `UNIFI_CONTROLLER_TYPE=direct` in `src/managers/connection_manager.py`
- [X] T028 [US2] Add logging for manual override mode in `ConnectionManager.initialize()` in `src/managers/connection_manager.py`
- [X] T029 [US2] Add invalid value handling with warning log in `src/bootstrap.py`
- [X] T030 [US2] Update README.md with configuration section documenting UNIFI_CONTROLLER_TYPE usage
- [X] T031 [US2] Verify unit tests pass: `pytest tests/unit/test_path_detection.py::test_manual_override_proxy -v`
- [X] T032 [US2] Verify unit tests pass: `pytest tests/unit/test_path_detection.py::test_manual_override_direct -v`
- [X] T033 [US2] Verify integration test passes: `pytest tests/integration/test_path_interceptor.py::test_manual_proxy_mode_skips_detection -v`

**Checkpoint**: Manual override should work for both proxy and direct modes. Test independently with each configuration value.

---

## Phase 5: User Story 3 - Graceful Failure and Retry (Priority: P3)

**Goal**: Implement retry logic with exponential backoff and provide clear error messages when detection fails, directing users to manual override configuration.

**Independent Test**: Simulate detection failures (mock offline controller, timeout, or both endpoints returning errors) and verify system retries with exponential backoff, then provides clear error message with troubleshooting guidance.

### Tests for User Story 3

- [X] T034 [P] [US3] Create unit test for retry logic in `tests/unit/test_path_detection.py` - test_detection_retries_with_exponential_backoff
- [X] T035 [P] [US3] Create unit test for timeout handling in `tests/unit/test_path_detection.py` - test_detection_timeout_retries_then_fails
- [X] T036 [P] [US3] Create unit test for both endpoints failing in `tests/unit/test_path_detection.py` - test_both_endpoints_fail_returns_none_with_error
- [X] T037 [P] [US3] Create unit test for ambiguous detection in `tests/unit/test_path_detection.py` - test_both_paths_succeed_prefers_direct
- [X] T038 [P] [US3] Create unit test for detection caching in `tests/unit/test_path_detection.py` - test_detection_result_cached_for_session

### Implementation for User Story 3

- [X] T039 [US3] Add `detect_with_retry()` wrapper function with exponential backoff logic in `src/managers/connection_manager.py`
- [X] T040 [US3] Modify `detect_unifi_os_proactively()` to be called by `detect_with_retry()` with retry_attempts parameter in `src/managers/connection_manager.py`
- [X] T041 [US3] Add timeout handling with `asyncio.TimeoutError` in `detect_unifi_os_proactively()` in `src/managers/connection_manager.py`
- [X] T042 [US3] Add clear error message generation for detection failures in `src/managers/connection_manager.py`
- [X] T043 [US3] Add preference for direct paths when both succeed (per FR-012) in `detect_unifi_os_proactively()` in `src/managers/connection_manager.py`
- [X] T044 [US3] Add detection result caching logic in `ConnectionManager.initialize()` in `src/managers/connection_manager.py`
- [X] T045 [US3] Add diagnostic logging for retry attempts in `detect_with_retry()` in `src/managers/connection_manager.py`
- [X] T046 [US3] Verify retry logic tests pass: `pytest tests/unit/test_path_detection.py::test_detection_retries_with_exponential_backoff -v`
- [X] T047 [US3] Verify timeout tests pass: `pytest tests/unit/test_path_detection.py::test_detection_timeout_retries_then_fails -v`
- [X] T048 [US3] Verify caching test passes: `pytest tests/unit/test_path_detection.py::test_detection_result_cached_for_session -v`

**Checkpoint**: Retry logic, error messages, and caching should all work correctly. All user stories (US1, US2, US3) should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [X] T049 [P] Add comprehensive docstrings to all new methods in `src/managers/connection_manager.py`
- [X] T050 [P] Add type hints validation - ensure all functions have proper type annotations
- [X] T051 [P] Update `.env.example` with `UNIFI_CONTROLLER_TYPE` documentation
- [ ] T052 Add troubleshooting section to README.md for detection failures
- [ ] T053 [P] Run full test suite and ensure >90% coverage: `pytest tests/ --cov=src/managers/connection_manager --cov-report=term-missing`
- [ ] T054 Perform manual testing with real UniFi OS controller (UDM-Pro or Cloud Gateway)
- [ ] T055 Perform manual testing with real standard controller (standalone UniFi)
- [ ] T056 Run quickstart.md validation checklist from `specs/001-unifi-os-detection/quickstart.md`
- [ ] T057 [P] Code cleanup and refactoring for idiomatic Python 3.13+
- [ ] T058 [P] Add performance measurement logging (detection duration) in `detect_unifi_os_proactively()`
- [ ] T059 Verify all acceptance scenarios from spec.md are met
- [ ] T060 Update CHANGELOG.md with feature description and issue #19 closure reference

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Automatic Detection**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2) - Manual Override**: Can start after Foundational (Phase 2) - Independent of US1, but US1 provides detection baseline for comparison
- **User Story 3 (P3) - Graceful Failure**: Depends on US1 detection logic being implemented - Enhances US1 with retry and error handling

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Detection logic (T014-T015) before connection manager integration (T016-T018)
- Core implementation before integration with dev_console (T019)
- Unit tests before integration tests
- Story complete and validated before moving to next priority

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T003 and T004 can run in parallel (directory structure vs dependencies)

**Foundational Phase (Phase 2)**:
- T007 (config.yaml) can run parallel to T005-T006 (bootstrap.py)
- T008 (connection_manager init) can run parallel to T005-T007

**User Story 1 (Phase 3)**:
- All test tasks (T009-T013) can run in parallel (different test functions)
- T015 (logging) can run parallel to T014 (detection logic) if written in different parts of the function

**User Story 2 (Phase 4)**:
- All test tasks (T022-T025) can run in parallel
- T026 and T027 can run in parallel (handling different enum values)

**User Story 3 (Phase 5)**:
- All test tasks (T034-T038) can run in parallel
- T039 and T041 can run in parallel (retry wrapper vs timeout handling)
- T042 and T045 can run in parallel (error messages vs logging)

**Polish Phase (Phase 6)**:
- T049, T050, T051, T057, T058 can all run in parallel (different files/concerns)
- T053 depends on all implementation being complete
- T054-T055 can run in parallel (different controller types)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create unit test for UniFi OS detection in tests/unit/test_path_detection.py"
Task: "Create unit test for standard controller detection in tests/unit/test_path_detection.py"
Task: "Create unit test for detection failure in tests/unit/test_path_detection.py"
Task: "Create integration test for path interception in tests/integration/test_path_interceptor.py"
Task: "Create integration test for UniFi OS requests in tests/integration/test_path_interceptor.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~15 minutes)
2. Complete Phase 2: Foundational (~15 minutes) - CRITICAL
3. Complete Phase 3: User Story 1 (~2-3 hours)
4. **STOP and VALIDATE**: Test US1 independently with both controller types
5. Deploy/demo if ready - **Users on UniFi OS can now connect without manual config!**

**Estimated MVP Time**: 3-4 hours

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (~30 minutes)
2. Add User Story 1 → Test independently → **MVP DELIVERED** (automatic detection works)
3. Add User Story 2 → Test independently → Deploy/Demo (manual override available)
4. Add User Story 3 → Test independently → Deploy/Demo (production-ready with retry logic)
5. Add Polish → Final validation → **FEATURE COMPLETE**

**Total Estimated Time**: 4-6 hours (as documented in quickstart.md)

### Parallel Team Strategy

With 2-3 developers:

1. **Together**: Complete Setup + Foundational (~30 minutes)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (automatic detection) - Priority 1
   - **Developer B**: User Story 2 (manual override) - Can start in parallel
   - **Developer C**: User Story 3 (retry logic) - Starts after Developer A completes US1
3. Stories complete and integrate independently
4. **Together**: Polish phase and final validation

**Team Estimated Time**: 2-3 hours with parallelization

---

## Validation Checklist

After all tasks complete, verify:

- [ ] **US1**: Detection works on UniFi OS controllers (Cloud Gateway, UDM-Pro)
- [ ] **US1**: Detection works on standard controllers (standalone)
- [ ] **US1**: All existing MCP tools work without modification
- [ ] **US1**: Detection adds ≤2 seconds to connection time
- [ ] **US2**: Manual override `UNIFI_CONTROLLER_TYPE=proxy` works
- [ ] **US2**: Manual override `UNIFI_CONTROLLER_TYPE=direct` works
- [ ] **US2**: Invalid values fall back to auto with warning
- [ ] **US3**: Detection retries 3 times with exponential backoff on failure
- [ ] **US3**: Clear error messages provided on detection failure
- [ ] **US3**: Detection result cached for session lifetime
- [ ] **All**: Unit tests achieve >90% coverage
- [ ] **All**: Integration tests pass on both controller types
- [ ] **All**: No regressions in existing functionality
- [ ] **All**: Performance targets met (SC-002, SC-005 from spec.md)
- [ ] **All**: Issue #19 resolved (UniFi OS 404 errors eliminated)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Primary file modification: `src/managers/connection_manager.py` (~330 lines total across all stories)
- Supporting modifications: 5 additional files (~90 lines total)

---

## Success Metrics (from spec.md)

After implementation, measure:

- **SC-001**: Zero 404 errors on UniFi OS controllers without manual config ✅
- **SC-002**: Detection completes within 5 seconds ✅
- **SC-003**: 100% correct path usage after detection ✅
- **SC-004**: Issue #19 support tickets reduced to zero ✅
- **SC-005**: ≤2s connection time overhead ✅
- **SC-006**: Manual override works 100% of test cases ✅
- **SC-007**: aiounifi upgrade compatibility maintained ✅
- **SC-008**: Actionable error messages on all failures ✅
- **SC-009**: Detection visible in dev_console.py output ✅
- **SC-010**: Ambiguous detection handles correctly (prefers direct) ✅

---

**Total Tasks**: 60
**User Story 1 Tasks**: 13 (T009-T021)
**User Story 2 Tasks**: 12 (T022-T033)
**User Story 3 Tasks**: 15 (T034-T048)
**Setup/Foundational Tasks**: 8 (T001-T008)
**Polish Tasks**: 12 (T049-T060)

**Parallel Opportunities**: 27 tasks marked [P] can run in parallel
**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (Tasks T001-T021) = ~3-4 hours
