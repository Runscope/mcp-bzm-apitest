"""
Unit tests for UsageManager (team/bucket/test usage tools) — MOB-53921.

src.tools.usage_manager does not exist yet; the module-level import below is
wrapped so a missing module fails each test by assertion (not by collection
error), per TDD convention. Mirrors the TestResultManager / TestTeamManager
patterns in this test suite: mock api_request via unittest.mock.patch on the
manager-module's imported symbol.
"""

from unittest.mock import patch

import pytest

from src.models import BaseResult

try:
    from src.tools.usage_manager import UsageManager
except ImportError:
    UsageManager = None

TEAM_UUID = "team-uuid-1234"
BUCKET_KEY = "bucket-key-1234"
TEST_UUID = "test-uuid-1234"
OTHER_TEST_UUID = "other-test-uuid-9999"


def _assert_implemented():
    assert UsageManager is not None, (
        "src.tools.usage_manager.UsageManager not implemented yet "
        "(spec FR-001; see specs/mob-53921/spec.md)"
    )


@pytest.mark.asyncio
class TestUsageManagerTeamUsage:
    """S1 (happy, T005, FR-001/FR-003/SC-001)."""

    async def test_team_usage_returns_api_count(self, mock_token, mock_context):
        """Covers T005. Scenario: api_request mocked to 42; team usage tool reports exactly 42
        and echoes the requested team_uuid."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 42,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result = await manager.get_team_usage(TEAM_UUID)

        assert result.error is None
        assert result.result[0]["requests_count"] == 42
        assert result.result[0]["team_uuid"] == TEAM_UUID


@pytest.mark.asyncio
class TestUsageManagerBucketUsage:
    """S2 (happy, T006, FR-001/FR-003/SC-001)."""

    async def test_bucket_usage_returns_api_count(self, mock_token, mock_context):
        """Covers T006. Scenario: api_request mocked to 17; bucket usage tool reports exactly 17
        and echoes the requested bucket_key."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "bucket_key": BUCKET_KEY,
                        "requests_count": 17,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result = await manager.get_bucket_usage(BUCKET_KEY)

        assert result.error is None
        assert result.result[0]["requests_count"] == 17
        assert result.result[0]["bucket_key"] == BUCKET_KEY


@pytest.mark.asyncio
class TestUsageManagerTestUsage:
    """S3 (happy, T007, FR-001/FR-003/SC-001)."""

    async def test_test_usage_returns_api_count(self, mock_token, mock_context):
        """Covers T007. Scenario: api_request mocked to 8; test usage tool reports exactly 8
        for the requested bucket_key + test_uuid."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "test_uuid": TEST_UUID,
                        "requests_count": 8,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result = await manager.get_test_usage(BUCKET_KEY, TEST_UUID)

        assert result.error is None
        assert result.result[0]["requests_count"] == 8
        assert result.result[0]["test_uuid"] == TEST_UUID


@pytest.mark.asyncio
class TestUsageManagerResponseShape:
    """S4 (contract, T008, FR-007/SC-002)."""

    async def test_usage_response_shape(self, mock_token, mock_context):
        """Covers T008. Scenario: each usage tool's result carries exactly
        requests_count/from_date/to_date + identifier — no fabricated fields; no
        tests_count/result.requests conflation (those belong to different domains per
        spec.md Field Semantics)."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 1,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result = await manager.get_team_usage(TEAM_UUID)

        item = result.result[0]
        assert set(item.keys()) == {"team_uuid", "requests_count", "from_date", "to_date"}
        assert "tests_count" not in item
        assert "requests" not in item


@pytest.mark.asyncio
class TestUsageManagerFaithfulPassthrough:
    """S5 (negative/falsification, T009, FR-003/SC-001) — mandatory Field/Metric
    Provenance hard-gate scenario."""

    async def test_usage_faithful_passthrough(self, mock_token, mock_context):
        """Covers T009. Scenario (FALSIFICATION): api_request mocked to return
        requests_count=7; the tool MUST report exactly 7 (not a placeholder / non-empty-only
        assertion). A second mock with a DIFFERENT value (123) MUST produce exactly 123 — the
        tool must not re-aggregate or fabricate a fixed/cached value."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 7,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result_a = await manager.get_team_usage(TEAM_UUID)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 123,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result_b = await manager.get_team_usage(TEAM_UUID)

        assert result_a.result[0]["requests_count"] == 7
        assert result_b.result[0]["requests_count"] == 123


@pytest.mark.asyncio
class TestUsageManagerDefaultWindow:
    """S6 (edge, T010, FR-004)."""

    async def test_usage_default_window_today(self, mock_token, mock_context):
        """Covers T010. Scenario: with no date args, the tool does NOT force any from/to/days/date
        param into the api_request call (api itself defaults to today — the tool must not
        second-guess api's default)."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 1,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            await manager.get_team_usage(TEAM_UUID)

        _, call_kwargs = mock_api.call_args
        params = call_kwargs.get("params") or {}
        assert not any(params.get(k) for k in ("from", "to", "days", "date"))

    async def test_usage_default_window_custom_from_to(self, mock_token, mock_context):
        """Covers T010. Scenario: from/to args are passed through to api_request's params
        unchanged."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 1,
                        "from_date": "2026-01-01",
                        "to_date": "2026-01-08",
                    }
                ],
                total=1,
            )
            await manager.get_team_usage(TEAM_UUID, from_date="2026-01-01", to_date="2026-01-08")

        _, call_kwargs = mock_api.call_args
        params = call_kwargs.get("params") or {}
        assert params.get("from") == "2026-01-01"
        assert params.get("to") == "2026-01-08"


@pytest.mark.asyncio
class TestUsageManagerTokenNoNewAuth:
    """S7 (happy, T011, FR-006)."""

    async def test_usage_passes_token_no_new_auth(self, mock_token, mock_context):
        """Covers T011. Scenario: the tool passes the provided BzmApimToken straight through
        to api_request and adds no auth header/logic of its own."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 1,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            await manager.get_team_usage(TEAM_UUID)

        call_args, _ = mock_api.call_args
        assert call_args[0] is mock_token


@pytest.mark.asyncio
class TestUsageManagerErrorSurfacing:
    """S8 (negative, T016, FR-008/SC-003)."""

    async def test_usage_api_error_surfaces_message(self, mock_token, mock_context):
        """Covers T016. Scenario: api_request raises/returns an error; the tool returns a
        BaseResult with a clear error (via http_error_message), never a fabricated/zero count
        masking the failure."""
        _assert_implemented()
        import httpx

        manager = UsageManager(mock_token, mock_context)

        request = httpx.Request("GET", "https://api.runscope.com/team/{}/requests".format(TEAM_UUID))
        response = httpx.Response(500, request=request)
        error = httpx.HTTPStatusError("server error", request=request, response=response)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.side_effect = error
            try:
                result = await manager.get_team_usage(TEAM_UUID)
            except httpx.HTTPStatusError:
                pytest.fail(
                    "UsageManager.get_team_usage must catch upstream HTTP errors and return a "
                    "BaseResult(error=...) — not let the exception propagate uncaught"
                )

        assert result.error is not None
        assert not result.result


@pytest.mark.asyncio
class TestUsageManagerNoDataReturnsZero:
    """S9 (edge, T017, FR-008/SC-003)."""

    async def test_usage_no_data_returns_zero(self, mock_token, mock_context):
        """Covers T017. Scenario: api returns requests_count=0 (no data in window); the tool
        treats this as a legitimate success value, NOT an error."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "team_uuid": TEAM_UUID,
                        "requests_count": 0,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result = await manager.get_team_usage(TEAM_UUID)

        assert result.error is None
        assert result.result[0]["requests_count"] == 0


class TestUsageToolsReadOnly:
    """S10 (negative, T019, FR-002)."""

    def test_usage_tools_are_read_only(self):
        """Covers T019. Scenario: the three usage tools expose only a 'read' action — no
        create/update/delete/start — via UsageManager's public method surface."""
        _assert_implemented()
        public_methods = {
            name
            for name in dir(UsageManager)
            if not name.startswith("_") and callable(getattr(UsageManager, name))
        }
        mutating_prefixes = ("create", "update", "delete", "start", "write", "put", "post")
        mutating = {m for m in public_methods if m.startswith(mutating_prefixes)}
        assert not mutating, "UsageManager must not expose mutating methods: {}".format(mutating)


@pytest.mark.asyncio
class TestUsageManagerStaticApiContract:
    """S11 (static contract, mandatory hard-gate) — endpoint constants and response-shape
    assumptions match the checked-in api Dependency Contract Facts (no live api call)."""

    async def test_usage_endpoint_constants_match_static_api_contract(self, mock_token, mock_context):
        """Covers T004. Scenario (static contract): the three endpoint constants in
        src.config.defaults match the api route paths documented in
        specs/mob-53921/spec.md's Dependency Contract Facts — no live api call is made
        (api_request is mocked in every test in this file)."""
        from src.config import defaults

        team_endpoint = getattr(defaults, "TEAM_USAGE_ENDPOINT", None)
        bucket_endpoint = getattr(defaults, "BUCKET_USAGE_ENDPOINT", None)
        test_endpoint = getattr(defaults, "TEST_USAGE_ENDPOINT", None)

        assert team_endpoint == "/team/{}/requests", (
            "src.config.defaults.TEAM_USAGE_ENDPOINT not implemented yet or does not match "
            "the api route path (spec Dependency Contract Facts)"
        )
        assert bucket_endpoint == "/buckets/{}/requests", (
            "src.config.defaults.BUCKET_USAGE_ENDPOINT not implemented yet or does not match "
            "the api route path (spec Dependency Contract Facts)"
        )
        assert test_endpoint == "/buckets/{}/tests/{}/requests", (
            "src.config.defaults.TEST_USAGE_ENDPOINT not implemented yet or does not match "
            "the api route path (spec Dependency Contract Facts)"
        )

    async def test_usage_test_tool_maps_response_to_requested_test_only(self, mock_token, mock_context):
        """Covers T007. Scenario (boundary compatibility): the test-usage tool's formatter
        consumes the producer-shaped api response envelope ({test_uuid, requests_count,
        from_date, to_date}) for the SPECIFIC requested test_uuid/bucket_key, not a
        different/other resource's identifier echoed back."""
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {
                        "test_uuid": TEST_UUID,
                        "requests_count": 3,
                        "from_date": "2026-10-06",
                        "to_date": "2026-10-06",
                    }
                ],
                total=1,
            )
            result = await manager.get_test_usage(BUCKET_KEY, TEST_UUID)

        assert result.result[0]["test_uuid"] == TEST_UUID
        assert result.result[0]["test_uuid"] != OTHER_TEST_UUID


class TestUsageFormattersNoData:
    """Real formatters against the producer's actual payloads (api_request is mocked elsewhere
    in this file, so these are the only tests that exercise the formatters)."""

    def test_bucket_usage_null_payload_is_zero(self):
        """api returns null bucket_key/requests_count/dates for a bucket with no usage in the
        window; that must surface as a legitimate 0 for the requested bucket, not an error."""
        from src.formatters.usage import format_bucket_usage

        null_payload = {
            "bucket_key": None,
            "requests_count": None,
            "from_date": None,
            "to_date": None,
            "bucket_usage": {},
            "bucket_test_runs_summary": {},
        }
        result = format_bucket_usage([null_payload], {"bucket_key": BUCKET_KEY})

        assert result[0]["bucket_key"] == BUCKET_KEY
        assert result[0]["requests_count"] == 0

    def test_bucket_usage_populated_payload_unchanged(self):
        from src.formatters.usage import format_bucket_usage

        payload = {
            "bucket_key": BUCKET_KEY,
            "requests_count": 17,
            "from_date": "2026-10-06",
            "to_date": "2026-10-07",
            "bucket_usage": {},
            "bucket_test_runs_summary": {},
        }
        result = format_bucket_usage([payload], {"bucket_key": BUCKET_KEY})

        assert result[0] == {
            "bucket_key": BUCKET_KEY,
            "requests_count": 17,
            "from_date": "2026-10-06",
            "to_date": "2026-10-07",
        }

    def test_team_usage_ignores_extra_api_fields(self):
        from src.formatters.usage import format_team_usage

        payload = {
            "team_uuid": TEAM_UUID,
            "requests_count": 42,
            "from_date": "2026-10-06",
            "to_date": "2026-10-07",
            "creator_name": "x",
            "creator_email": "x@example.com",
            "creator_id": "y",
            "buckets": [],
        }
        result = format_team_usage([payload])

        assert set(result[0].keys()) == {"team_uuid", "requests_count", "from_date", "to_date"}


@pytest.mark.asyncio
class TestUsageManagerBucketFormatterParams:
    async def test_bucket_usage_passes_requested_key_to_formatter(self, mock_token, mock_context):
        _assert_implemented()
        manager = UsageManager(mock_token, mock_context)

        with patch("src.tools.usage_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(result=[], total=0)
            await manager.get_bucket_usage(BUCKET_KEY)

        _, call_kwargs = mock_api.call_args
        assert call_kwargs.get("result_formatter_params") == {"bucket_key": BUCKET_KEY}


class TestUsageToolDescriptions:
    def test_date_param_documented_as_from_date_through_today(self):
        """api treats `date` as 'from this date through today', not a single day."""
        import inspect

        from src.tools import usage_manager

        source = inspect.getsource(usage_manager.register)
        assert "A single day" not in source
        assert source.count("counts from this date through today") == 3
