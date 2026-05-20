---
applyTo: "**/*test*.py, **/tests/**/*.py, **/py/**"
---

# Testing guidelines for Python
Essential to your coding tasks is the process of testing. **Whenever thinking about tests, revisit these guidelines and consider their application to your task at hand** to ensure your tests are effective, maintainable, and aligned with our best practices.

## Your testing objectives
When writing tests, optimize for two high-level objectives:

- **Executable documentation**:

  Tests expressively encode and ensure stability of durable public contracts, expectations, and invariants.

  - Tests serve as sentinels against behavior drift at meaningful scales—from unit tests that freeze a single function's behavior to end-to-end tests that lock in entire scenarios, and all scales in between where scenarios need to be locked in. Configure tests so that *any* change to expected behavior triggers a failure, signaling whether code changes inadvertently broke an existing expectation and flagging the need for review.
  - Tests use clear arrange/act/assert structure with obvious inputs and expected outputs, making cause-and-effect relationships immediately apparent.
  - Tests have a high signal-to-noise ratio, efficiently communicating intent and scenario details with minimal cognitive overhead, redundant documentation, and boilerplate.
  - Related tests are logically grouped together, with shared test logic unified, rather than scattered across isolated functions that dilute clarity.
  - Each test should provide unique coverage—avoid writing tests that effectively duplicate what another test already verifies.
  - Each test should own a clear boundary of responsibility—verify behavior at that boundary without re-testing logic already covered by dependencies or testing so broadly that failures become hard to diagnose.
  - Tests easily scale to many test cases as new requirements, edge cases, and expectations are discovered, without excessive duplication or brittleness.

  **Litmus tests to keep in mind:**
  - What specific behaviors do I want to lock in? What arrangements, actions, and assertions will serve as sentinels for my expectations?
  - Does the test suite guard against behavior drift at the right boundary? Will it fail usefully if behavior changes?
  - Are inputs and expected outputs clearly paired so cause-and-effect is obvious?
  - Are related test cases grouped cohesively, or scattered across isolated functions with duplicated logic?
  - Are there tests that exercise the same behavior under the same conditions? If so, can they be consolidated, rescoped to clarify distinct boundaries, or is one redundant?
  - Do my tests validate durable expectations rather than coupling to incidental implementation details?
  - As new requirements are discovered, can we easily scale the test suite without excessive boilerplate or duplication?

- **Design pressure**:

  The act of writing tests pressures code toward better design. When tests are hard to write, it often signals that the code under test lacks clean boundaries, proper encapsulation, or sufficient modularity.

  - Tests expose natural seams where behavior can be isolated and verified, guiding factorization decisions.
  - Difficulty testing a module often indicates it is doing too much or has unclear responsibilities.
  - If mocking deep internals is required, consider introducing abstractions (interfaces, ports/adapters, dependency injection) to create testable boundaries.
  - Well-designed code is easy to test; hard-to-test code is a design smell worth investigating.

  **Litmus tests to keep in mind:**
  - If I imagine the ideal test for the behavior I need to verify, what public boundary would make it trivial to write? If that boundary doesn't exist, is that a design smell?
  - Can I test a module once generically and reuse it via composition, or do I need multiple similar tests differing only in internal details?
  - Are multiple tests exercising the same underlying logic (even if asserting different outcomes)? Repeated exercise of the same logic paths is design pressure to factor that logic into a module that's tested once and composed into consumers.
  - Am I patching or mocking deep internals? Could introducing a seam (interface, DI, adapter) make this cleaner?
  - What friction am I experiencing writing this test, and what does it reveal about shortcomings in the code's design?
---

## Durable expectations vs. implementation details

Tests should encode *what the code is supposed to do*, not *how it happens to work today*.

**Test durable behaviors:**
Consider locking in concerns like:
- Contract-defined outputs and return values
- State transitions and side effects that matter to correctness
- Business rules and validation logic

**Avoid testing incidental implementation details:**
Avoid coupling tests to:
- Internal helper calls or private method invocations
- Exact call counts or call ordering (unless order is a contract requirement)
- Logging specifics or debug output
- How a result is computed rather than what it is

**Prefer observable outcomes over introspecting internal mechanics.** Use mocks to assert meaningful contract-level effects, not to verify incidental implementation choices.

**Litmus test:** A well-targeted test should:
- **Fail** if expected external behavior changes (it's a sentinel for durable expectations)
- **Pass** after refactoring internals without changing correctness (it doesn't couple to implementation details)
- **Answer clearly:** *What expectation am I encoding?* If you can't articulate the durable expectation as a valuable sentinel, reconsider the assertion.

**Example — same requirement, different approaches:**

Given a requirement "payment transactions must be auditable":
- ✅ **Durable:** Assert that `audit_log` contains an entry after `payment_processor.process_payment()` completes—tests the observable outcome.
- ❌ **Brittle:** Assert that `payment_processor._write_audit_record()` was called with specific arguments—couples to internal implementation.

---

## Test self-documentation

Test names should encode semantic expectations so the test is self-documenting.
Good test names clearly express:
- The module or object under test
- The conditions being tested
- The expected outcome or invariant

**Avoid redundant docstrings** that simply repeat what is obvious from the code or test name. They dilute clarity and add maintenance overhead.

- ❌ `test_parse_date_1` — opaque; reveals nothing about what's being tested.
- ✅ `test_parse_date_returns_tuple_for_valid_iso_format` — encodes the subject, condition, and expectation.

- ❌ Worthless comments:
  ```python
  def test_parse_date_returns_tuple_for_valid_iso_format():
      """Test that parse_date returns a tuple for valid ISO format."""
  ```
- ✅ No docstring. Fully captured in the test name already.

---

## Illustrative patterns

### Parametrized tests
Parametrized tests are a powerful pattern to express a class of related behavior with shared test logic, while clearly documenting individual scenarios via test case IDs. This pattern minimizes boilerplate and repetition of test logic, maximizes clarity of inputs and expected outputs, and adapts easily as requirements evolve.

```python
import pytest

from my_code_under_test import BalanceInput
from my_code_under_test import BalanceResult
from my_code_under_test import InvalidUserIdError
from my_code_under_test import UserNotFoundError


@pytest.mark.parametrize(
    ("balance", "expected"),
    [
        pytest.param(
            BalanceInput(user_id="u-001"),
            BalanceResult(amount=125.75, currency="USD"),
            id="basic USD balance",
        ),
        pytest.param(
            BalanceInput(user_id="u-002"),
            BalanceResult(amount=0.0, currency="USD"),
            id="zero-balance account",
        ),
    ],
)
def test_balance_returns_expected(
    ledger_client,
    balance: BalanceInput,
    expected: BalanceResult,
):
    # Arrange
    # Act
    result = ledger_client.get_balance(user_id=balance.user_id)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("balance", "expected_error"),
    [
        pytest.param(
            BalanceInput(user_id="missing"),
            UserNotFoundError,
            id="user not found",
        ),
        pytest.param(
            BalanceInput(user_id=""),
            InvalidUserIdError,
            id="empty user ID",
        ),
    ],
)
def test_balance_raises_for_invalid_input(
    ledger_client,
    balance: BalanceInput,
    expected_error: type[Exception],
):
    # Arrange
    # Act & Assert
    with pytest.raises(expected_error):
        ledger_client.get_balance(user_id=balance.user_id)
```

Note how in the above example:
- The test function names describe a _class_ of related behavior and shared test logic.
- Test case IDs document the story of individual scenarios.
- Test cases are extremely high signal-to-noise.
  - Clear pairing of inputs and expected outputs for easy cause/effect understanding.
- Minimal boilerplate. No repetition of test logic.
- Input/expected output pattern effortlessly drives code design via public contracts.
- There is no coupling to internal implementation details, allowing refactoring without test breakage.
- Tests easily adapt and scale as new requirements and edge cases are discovered.
- **The test code is fully self-documenting; no redundant comments needed.**

### Snapshot tests
Snapshot tests are ideal when outputs are **representations** (JSON, text, prompts, context windows) where their full structure and evolution should be visible and reviewable. They capture complex outputs as normalized text artifacts, making changes easy to inspect in code review.

**When to prefer snapshots over asserts:**
- Serialization payloads, rendered prompts sent to LLMs, context packages, error report text.
- When fields, formatting, or order may evolve and changes should trigger intentional review.

**Best practices:**
- Normalize first: canonical JSON with sorted keys; redact volatile fields (timestamps, IDs) and secrets/PII.
- Optimize for intuitive diffing and readability for holistic review of changes.
- Store under `tests/snapshots/` with descriptive IDs.

```python
import json
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.amber import AmberSnapshotExtension


class JSONSnapshotExtension(AmberSnapshotExtension):
    def serialize(self, data, **kwargs) -> str:
        if isinstance(data, (dict, list)):
            return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
        return str(data)


@pytest.fixture
def json_snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest.mark.parametrize(
    ("config", "snapshot_name"),
    [
        pytest.param(ContextConfig(...), "context_with_history", id="with history"),
        pytest.param(ContextConfig(...), "context_minimal", id="minimal"),
    ],
)
def test_context_window_structure(json_snapshot, config, snapshot_name):
    # Arrange
    # Act
    context = build_context_window(config)
    # Assert
    assert context == json_snapshot(name=snapshot_name)
```

The resulting `.ambr` snapshot file captures the full structure:

```ambr
# name: test_context_window_structure[with history]
  {
    "messages": [...],
    "model": "gpt-4",
    "max_tokens": 4096
  }
# ---
# name: test_context_window_structure[minimal]
  {
    "messages": [...],
    "model": "gpt-4",
    "max_tokens": 1024
  }
# ---
```

The snapshot captures the **full representation** of what gets sent (e.g., to an LLM), making prompt engineering changes easily reviewable in their final form. When structure evolves, the diff is immediately visible in code review.

**Why snapshots are better sentinels than field-by-field assertions:**

```python
# ❌ Field-by-field assertions only catch what you thought to check
def test_context_window_fields(config):
    context = build_context_window(config)
    assert context["model"] == "gpt-4"
    assert context["max_tokens"] == 4096
    # If build_context_window() starts including a new "temperature" field
    # or changes "messages" structure, this test won't catch it.

# ✅ Snapshot captures the full structure—any change triggers review
def test_context_window_structure(json_snapshot, config):
    context = build_context_window(config)
    assert context == json_snapshot(name="context_with_history")
    # If any field is added, removed, or changed, the snapshot diff
    # surfaces it in code review for intentional approval.
```

Snapshots act as comprehensive sentinels: they flag *any* structural change for review, not just the fields you remembered to assert. This makes them ideal for outputs where the full shape matters and evolution should be intentional.

### Shared test doubles for infrastructure dependencies
When common dependencies are used across many modules, a shared fake can replace scattered mock setups:

- **Minimal working behavior**: trivially correct implementation, not just return values
- **One contract to extend**: add methods once, all tests leverage immediately
- **Tightly bounded tests**: test *your* logic, not the dependency's behavior—fakes represent already-tested boundaries, so tests using them should verify their own logic without re-testing the fake's internals
- **Design pressure**: wanting repeatable faking can signal a common utility worth factoring out
- **Assertion clarity**: fakes can provide higher-order assertion APIs to make tests clearer

**The problem with scattered mocks:**
```python
# Repeated in 20 files, each with subtly different setup
mock_redis = MagicMock()
mock_redis.get.return_value = b'{"cached": true}'
mock_redis.incr.return_value = 5
# No shared contract. Update mocks in 20 places when requirements change.
```

**The solution: a shared contract and fake:**

```python
# tests/fakes/kv_store.py
from typing import Protocol  # or ABC, interface, etc.


class KVStoreContract(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes, ex: int | None = None) -> bool: ...
    def incr(self, key: str) -> int: ...
    def delete(self, key: str) -> bool: ...


class InMemoryKVStore:
    """Minimal working implementation backed by a dict."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._data.get(key)

    def set(self, key: str, value: bytes, ex: int | None = None) -> bool:
        self._data[key] = value
        return True

    def incr(self, key: str) -> int:
        current = int(self._data.get(key, b"0"))
        self._data[key] = str(current + 1).encode()
        return current + 1

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def seed(self, data: dict[str, bytes]) -> "InMemoryKVStore":
        self._data.update(data)
        return self
```

**Tests own their data setup:**

Fixtures can provide fresh fake instances to reduce boilerplate, but each test should visibly arrange its own data so readers can understand the scenario without jumping to fixture definitions:

```python
def test_cache_returns_stored_value(kv_store: InMemoryKVStore):
    # Arrange
    kv_store.seed({"user:123": b'{"name": "Alice", "role": "admin"}'})
    cache = CacheService(store=kv_store)
    # Act
    user = cache.get_user(123)
    # Assert
    assert user.name == "Alice"


def test_rate_limiter_blocks_after_threshold(kv_store: InMemoryKVStore):
    # Arrange
    limiter = RateLimiter(store=kv_store, max_requests=3)

    # Act & Assert
    for _ in range(3):
        assert limiter.allow("client-1") is True
    assert limiter.allow("client-1") is False
```

Note how in the above example:
- The fake provides real semantics with better parity to production logic, without reimplementing that logic in every test:
  - `incr()` really increments
  - `get()` returns what `set()` stored
- The resulting tests have an extremely high signal-to-noise ratio:
  - Minimal setup
  - Clear intent
  - No mock configuration clutter

**When to use fakes vs. mocks:**
- **Fakes**: Best when methods have interconnected logic simple enough to implement correctly (in-memory stores, queues, caches). Provides real semantics with better parity to production behavior.
- **Mocks**: Best for black-box request/response stubbing when calls have independent or extremely complex behavior. Easier to sequence stubbed responses than to reimplement intricate logic. Useful for external APIs where you only care about specific request/response pairs.

```python
mock_llm = MagicMock()
mock_llm.complete.return_value = CompletionResponse(content="mocked response")
```

For complex mock setup or assertion logic that repeats, consider wrapping in a helper class, but often a simple `MagicMock` is sufficient.

**Best practices:**
- Define contracts and fakes in `tests/fakes/` for reuse.
- Fixtures can provide fresh fake instances, but tests should own their data setup for cohesion and readability.
- Use dependency injection at public seams; avoid patching internals. Lean into the design pressure to create testable boundaries.
- No need to unit test fakes.
