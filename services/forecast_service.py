import pandas as pd

from database import save_external_signal_log
from integrations.base import LocalEvent, SocialTrendSignal
from logic import get_integrated_forecast
from services.demand_adjuster import build_external_context
from services.forecast_context import ExternalForecastContext
from services.signal_service import signals_to_json


def build_forecast(
    target_date_str: str,
    store_id: str,
    weather_label: str,
    temp: float,
    humidity: float,
    rainfall: float,
    is_rainy: int,
    engine,
    trends: list[SocialTrendSignal],
    events: list[LocalEvent],
) -> pd.DataFrame:
    ctx = build_external_context(trends, events)
    df = get_integrated_forecast(
        target_date_str=target_date_str,
        store_id=store_id,
        weather_label=weather_label,
        temp=temp,
        humidity=humidity,
        rainfall=rainfall,
        is_rainy=is_rainy,
        engine=engine,
        external_context=ctx,
    )
    save_external_signal_log(
        date_str=target_date_str,
        store_id=store_id,
        payload_json=signals_to_json(trends, events),
        total_sns_uplift=ctx.total_sns_uplift,
        total_event_uplift=ctx.total_event_uplift,
    )
    return df
