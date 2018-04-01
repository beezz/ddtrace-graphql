"""
Tracing for the graphql-core library.

https://github.com/graphql-python/graphql-core
"""

import logging
import os

import graphql
import wrapt
from ddtrace.util import unwrap

from ddtrace_graphql.base import traced_graphql_wrapped

logger = logging.getLogger(__name__)


def patch(span_kwargs=None):
    """
    Monkeypatches graphql-core library to trace graphql calls execution.
    """
    logger.debug('Patching `graphql.graphql` function.')

    def wrapper(func, _, args, kwargs):
        return traced_graphql_wrapped(
            func, args, kwargs, span_kwargs=span_kwargs)

    wrapt.wrap_function_wrapper(graphql, 'graphql', wrapper)


def unpatch():
    logger.debug('Unpatching `graphql.graphql` function.')
    unwrap(graphql, 'graphql')
