import logging
from app.core.config import get_settings


def configure_telemetry() -> None:
    settings = get_settings()

    if not settings.applicationinsights_connection_string:
        logging.info("Application Insights not configured.")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string
        )

        logging.info("Application Insights telemetry configured.")

    except Exception as exc:
        logging.warning("Failed to configure Application Insights: %s", exc)
