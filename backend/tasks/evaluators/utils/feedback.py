"""Compatibility shim — delegates to evaluation_core for a single source of truth."""

from evaluation_core.utils.feedback import (  # noqa: F401
    detail_feedback_lines,
    generate_feedback,
)
