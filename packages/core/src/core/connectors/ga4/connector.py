from collections.abc import AsyncIterator
from typing import Any

from google.analytics.data_v1beta import BetaAnalyticsDataAsyncClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    GetMetadataRequest,
    Metric,
    RunReportRequest,
)

from core.connectors.base import BaseConnector, CanonicalMapping, ConnectorConfig, SchemaField
from core.connectors.ga4.schema_map import GA4_CANONICAL_HINTS
from core.registry import ConnectorRegistry

_PAGE_SIZE = 10_000


class GA4Connector(BaseConnector):
    connector_type = "ga4"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._property_id: str = config.config["property_id"]
        # credentials dict should contain Google service account JSON or be empty
        # (falls back to ADC when empty)
        self._client: BetaAnalyticsDataAsyncClient | None = None

    def _get_client(self) -> BetaAnalyticsDataAsyncClient:
        if self._client is None:
            creds = self.config.credentials or {}
            if creds:
                from google.oauth2 import service_account
                sa_creds = service_account.Credentials.from_service_account_info(
                    creds,
                    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
                )
                self._client = BetaAnalyticsDataAsyncClient(credentials=sa_creds)
            else:
                self._client = BetaAnalyticsDataAsyncClient()
        return self._client

    async def test_connection(self) -> bool:
        try:
            client = self._get_client()
            req = GetMetadataRequest(name=f"properties/{self._property_id}/metadata")
            await client.get_metadata(req)
            return True
        except Exception:
            return False

    async def list_schema_fields(self) -> list[SchemaField]:
        client = self._get_client()
        req = GetMetadataRequest(name=f"properties/{self._property_id}/metadata")
        metadata = await client.get_metadata(req)

        fields: list[SchemaField] = []
        for dim in metadata.dimensions:
            fields.append(SchemaField(
                raw_name=dim.api_name,
                raw_type="STRING",
                description=dim.description or None,
                ui_name=dim.ui_name or None,
            ))
        for metric in metadata.metrics:
            fields.append(SchemaField(
                raw_name=metric.api_name,
                raw_type=metric.type_.name if hasattr(metric.type_, "name") else "FLOAT",
                description=metric.description or None,
                ui_name=metric.ui_name or None,
            ))
        return fields

    async def fetch_data(
        self,
        start_date: str,
        end_date: str,
        fields: list[str],
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._get_client()
        metadata = await client.get_metadata(
            GetMetadataRequest(name=f"properties/{self._property_id}/metadata")
        )
        dim_names = {d.api_name for d in metadata.dimensions}
        metric_names = {m.api_name for m in metadata.metrics}

        dimensions = [Dimension(name=f) for f in fields if f in dim_names]
        metrics = [Metric(name=f) for f in fields if f in metric_names]

        offset = 0
        while True:
            req = RunReportRequest(
                property=f"properties/{self._property_id}",
                dimensions=dimensions,
                metrics=metrics,
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                offset=offset,
                limit=_PAGE_SIZE,
            )
            response = await client.run_report(req)
            if not response.rows:
                break

            dim_headers = [h.name for h in response.dimension_headers]
            met_headers = [h.name for h in response.metric_headers]

            for row in response.rows:
                record: dict[str, Any] = {}
                for i, val in enumerate(row.dimension_values):
                    record[dim_headers[i]] = val.value
                for i, val in enumerate(row.metric_values):
                    record[met_headers[i]] = val.value
                yield record

            offset += len(response.rows)
            if offset >= response.row_count:
                break

    def get_canonical_hints(self) -> dict[str, str]:
        return GA4_CANONICAL_HINTS

    @staticmethod
    def build_default_mappings(fields: list[SchemaField]) -> list[CanonicalMapping]:
        mappings = []
        for field in fields:
            if field.raw_name in GA4_CANONICAL_HINTS:
                mappings.append(CanonicalMapping(
                    raw_field=field.raw_name,
                    canonical_field=GA4_CANONICAL_HINTS[field.raw_name],
                ))
        return mappings


ConnectorRegistry.register(GA4Connector)
