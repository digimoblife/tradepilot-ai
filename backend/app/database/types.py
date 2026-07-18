from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Numeric, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        return value


def pg_uuid() -> PG_UUID:  # type: ignore[type-arg]
    return PG_UUID(as_uuid=True)


def utc_datetime() -> UTCDateTime:
    return UTCDateTime()


def price_numeric() -> Numeric:  # type: ignore[type-arg]
    return Numeric(precision=20, scale=6, asdecimal=True)


def monetary_numeric() -> Numeric:  # type: ignore[type-arg]
    return Numeric(precision=24, scale=6, asdecimal=True)


def quantity_numeric() -> Numeric:  # type: ignore[type-arg]
    return Numeric(precision=24, scale=6, asdecimal=True)


def percentage_numeric() -> Numeric:  # type: ignore[type-arg]
    return Numeric(precision=7, scale=4, asdecimal=True)


def return_pct_numeric() -> Numeric:  # type: ignore[type-arg]
    return Numeric(precision=12, scale=6, asdecimal=True)


def probability_numeric() -> Numeric:  # type: ignore[type-arg]
    return Numeric(precision=7, scale=4, asdecimal=True)
