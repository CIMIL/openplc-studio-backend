from datetime import datetime
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from plc_platform_backend.runs.runs_models import RunStatus
from plc_platform_backend.runs.runs_repository import RunsRepository


class RunsRepositoryInvalidIdTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = RunsRepository.__new__(RunsRepository)
        self.repository.collection = SimpleNamespace(
            find_one=AsyncMock(),
            find_one_and_update=AsyncMock(),
            delete_one=AsyncMock(),
        )

    async def test_invalid_id_is_not_found(self) -> None:
        self.assertIsNone(await self.repository.get_run("invalid"))
        self.repository.collection.find_one.assert_not_awaited()

    async def test_invalid_id_is_not_deleted(self) -> None:
        self.assertFalse(await self.repository.delete_run("invalid"))
        self.repository.collection.delete_one.assert_not_awaited()

    async def test_invalid_id_status_is_not_transitioned(self) -> None:
        self.assertIsNone(
            await self.repository.transition_status(
                "invalid", RunStatus.CREATED, RunStatus.QUEUED
            )
        )
        self.repository.collection.find_one_and_update.assert_not_awaited()

    async def test_dashboard_snapshot_uses_recent_window_and_bounded_lists(self) -> None:
        cutoff = datetime(2026, 1, 1, 12, 0, 0)
        expected = {
            "active_counts": [{"_id": "running", "count": 2}],
            "recent_terminal_counts": [{"_id": "completed", "count": 3}],
            "active_runs": [],
            "recent_runs": [],
            "failed_runs": [],
        }

        class AggregateCursor:
            async def to_list(self, length: int):
                self.length = length
                return [expected]

        pipeline_holder = {}

        def aggregate(pipeline):
            pipeline_holder["value"] = pipeline
            return AggregateCursor()

        self.repository.collection = SimpleNamespace(aggregate=aggregate)

        result = await self.repository.get_dashboard_snapshot(cutoff, 5)

        self.assertEqual(result, expected)
        facets = pipeline_holder["value"][0]["$facet"]
        self.assertEqual(facets["active_runs"][-1], {"$limit": 5})
        self.assertEqual(facets["recent_runs"][-1], {"$limit": 5})
        self.assertEqual(facets["failed_runs"][-1], {"$limit": 5})
        self.assertEqual(
            facets["recent_terminal_counts"][0]["$match"]["updated"],
            {"$gte": cutoff},
        )
        self.assertEqual(
            facets["active_runs"][1],
            {"$sort": {"updated": -1, "_id": -1}},
        )

    async def test_dashboard_snapshot_normalizes_an_empty_aggregation(self) -> None:
        cursor = SimpleNamespace(to_list=AsyncMock(return_value=[]))
        self.repository.collection = SimpleNamespace(
            aggregate=lambda pipeline: cursor
        )

        result = await self.repository.get_dashboard_snapshot(datetime.utcnow(), 5)

        self.assertEqual(
            result,
            {
                "active_counts": [],
                "recent_terminal_counts": [],
                "active_runs": [],
                "recent_runs": [],
                "failed_runs": [],
            },
        )

    def test_page_filter_escapes_search_and_filters_statuses(self) -> None:
        query = self.repository._build_page_filter(
            "run.*", [RunStatus.RUNNING, RunStatus.COMPLETED]
        )

        self.assertEqual(
            query,
            {
                "$or": [
                    {"name": {"$regex": r"run\.\*", "$options": "i"}},
                    {"author": {"$regex": r"run\.\*", "$options": "i"}},
                ],
                "status": {"$in": ["running", "completed"]},
            },
        )
