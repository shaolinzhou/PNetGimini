# PNetGimini Test Suite (`tests/`)

This directory contains the automated test suite for validating **PNetGimini**'s core subsystems, vendor adapters, diff-based rollback logic, and async concurrency engine.

---

## 🧪 Test Suite Structure

```
tests/
├── README.md              # Test documentation (this file)
└── test_core.py           # Core unit tests (Adapters, Diff Rollback, Async Engine)
```

### Coverage Areas:
1. **`TestAdapters`**:
   - Tests `AdapterFactory` vendor resolution (`cisco_ios_telnet`, `cisco_ios_ssh`, `huawei_router_telnet`, `huawei_router_ssh`).
   - Validates pagination command output (`terminal length 0` vs `screen-length 0 temporary`).
   - Validates snapshot commands and negation prefixes (`no ` vs `undo `).
   - Validates comment and header cleaning (`clean_raw_config`) for Cisco and Huawei configs.
2. **`TestDiffRollback`**:
   - Validates precision reversal patch generation for newly introduced process blocks (e.g. `router ospf 1` -> `no router ospf 1`).
   - Validates interface attribute restoration (reverting IP addresses, resetting `shutdown` state).
   - Validates Huawei native syntax reversal (`undo ospf 1`, `undo ip address`, `shutdown`, `quit`).
3. **`TestAsyncEngine`**:
   - Validates `AsyncDeploymentEngine` coroutine scheduling.
   - Tests semaphore concurrency limiting.
   - Mocks physical transport calls via `unittest.mock.patch` to guarantee fast, zero-dependency offline test runs.

---

## 🚀 Running the Tests

### 1. Run All Tests
Execute discovery from the project root:

```bash
# Standard unittest discovery
python -m unittest discover -s tests -p "test_*.py"
```

Expected output:
```text
........
----------------------------------------------------------------------
Ran 8 tests in 0.011s

OK
```

### 2. Run a Specific Test Class
```bash
python -m unittest tests.test_core.TestDiffRollback
```

### 3. Run a Specific Test Method
```bash
python -m unittest tests.test_core.TestDiffRollback.test_cisco_diff_reversal_new_block
```

### 4. Running with Verbose Output
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🔒 Safety & Mocking Philosophy
All unit tests in this directory are **100% non-destructive and offline-safe**. They do not connect to real devices or network sockets. Netmiko connections are mocked using `unittest.mock.patch`, ensuring tests can run in any CI/CD runner or offline developer workstation in under 1 second.
