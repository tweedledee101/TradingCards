"""
Structured Logger - Runtime observability for the trading card platform

Logs to stdout (human-readable) and PostgreSQL error_log table (queryable).
Every log entry carries structured context so we can detect patterns
programmatically -- not just read text.

Usage:
    from backend.utils.logger import get_logger

    log = get_logger('opportunity_finder')

    # Simple message
    log.info('Starting scan', context={'players': 40})

    # Categorized warning (feeds pattern detection)
    log.warn('Reprint detected in results', category='reprint_match', context={
        'card': 'Mike Trout 2011 Topps Update #US175',
        'ebay_title': 'Die-Cut Replica Sticker',
        'buy_price': 3.95,
        'scp_price': 255.89
    })

    # Error with automatic stack trace capture
    log.error('SCP scraper failed', category='scraper_timeout', context={
        'player': 'Mike Trout',
        'url': 'https://sportscardspro.com/...'
    })

    # Attach a request_id for API request tracing
    log.set_request_id('abc-123')
    log.info('Request completed', context={'status': 200, 'duration_ms': 45})
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Optional


# Module-level request_id storage (per-thread via contextvars for async safety)
import contextvars
_request_id_var = contextvars.ContextVar('request_id', default=None)


def get_request_id() -> Optional[str]:
    return _request_id_var.get()


def set_request_id(rid: str):
    _request_id_var.set(rid)


def clear_request_id():
    _request_id_var.set(None)


class AppLogger:
    """Structured logger that writes to stdout and error_log table."""

    # Only persist these levels to DB (skip DEBUG/INFO noise in production)
    DB_LEVELS = {'WARN', 'ERROR', 'CRITICAL'}

    def __init__(self, source: str):
        self.source = source
        self._py_logger = logging.getLogger(f'ragnarok.{source}')
        if not self._py_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self._py_logger.addHandler(handler)
            self._py_logger.setLevel(logging.DEBUG)

    def debug(self, message: str, **kwargs):
        self._log('DEBUG', message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log('INFO', message, **kwargs)

    def warn(self, message: str, **kwargs):
        self._log('WARN', message, **kwargs)

    def error(self, message: str, **kwargs):
        kwargs.setdefault('stack_trace', traceback.format_exc())
        self._log('ERROR', message, **kwargs)

    def critical(self, message: str, **kwargs):
        kwargs.setdefault('stack_trace', traceback.format_exc())
        self._log('CRITICAL', message, **kwargs)

    def _log(self, level: str, message: str, category: str = None,
             context: dict = None, stack_trace: str = None):
        # Always log to stdout
        py_level = getattr(logging, level if level != 'WARN' else 'WARNING')
        extra = ''
        if category:
            extra += f' [{category}]'
        if context:
            extra += f' {json.dumps(context, default=str)}'
        self._py_logger.log(py_level, f'{message}{extra}')

        # Persist to DB for WARN and above
        if level in self.DB_LEVELS:
            self._persist(level, message, category, context, stack_trace)

    def _persist(self, level: str, message: str, category: str = None,
                 context: dict = None, stack_trace: str = None):
        """Write to error_log table. Fails silently -- logging should never crash the app."""
        try:
            from backend.utils.database import SessionLocal
            from backend.models import ErrorLog
            db = SessionLocal()
            try:
                # Clean up "NoneType: None" stack traces (no real exception)
                if stack_trace and stack_trace.strip() == 'NoneType: None':
                    stack_trace = None

                entry = ErrorLog(
                    timestamp=datetime.now(),
                    level=level,
                    category=category,
                    source=self.source,
                    message=message,
                    context=context,
                    request_id=get_request_id(),
                    stack_trace=stack_trace
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception:
            # Never let logging failures propagate
            pass


def get_logger(source: str) -> AppLogger:
    """Get a structured logger for a module.

    Args:
        source: Module or component name (e.g. 'opportunity_finder', 'api.opportunities')
    """
    return AppLogger(source)
