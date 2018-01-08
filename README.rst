
===============
ddtrace-graphql
===============


.. image:: https://travis-ci.org/beezz/ddtrace-graphql.svg?branch=master
   :target: https://travis-ci.org/beezz/ddtrace-graphql


.. image:: https://pyup.io/repos/github/beezz/ddtrace-graphql/shield.svg
   :target: https://pyup.io/repos/github/beezz/ddtrace-graphql/


Python library to trace graphql calls with Datadog.


Usage
=====

To trace all GraphQL requests, patch the library like so:

.. code-block:: python

    from ddtrace_graphql import patch
    patch()

    from graphql import graphql
    result = graphql(schema, query)


Trace only certain calls with ``traced_graphql`` function:

.. code-block:: python

    from ddtrace_graphql import traced_graphql
    traced_graphql(schema, query)
