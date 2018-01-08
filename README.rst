
===============
ddtrace-graphql
===============


.. image:: https://travis-ci.org/beezz/ddtrace-graphql.svg?branch=master
   :target: https://travis-ci.org/beezz/ddtrace-graphql


.. image:: https://pyup.io/repos/github/beezz/ddtrace-graphql/shield.svg
   :target: https://pyup.io/repos/github/beezz/ddtrace-graphql/


Python library to trace graphql calls with Datadog.

* `Datadog APM (Tracing) <https://docs.datadoghq.com/tracing/>`_

* `Datadog Trace Client <http://pypi.datadoghq.com/trace/docs/>`_


Installation
============

Using pip
---------

.. code-block:: bash

   $ pip install ddtrace-graphql


From source
------------

.. code-block:: bash

   $ git clone https://github.com/beezz/ddtrace-graphql.git
   $ cd ddtrace-graphql && python setup.py install


Usage
=====

To trace all GraphQL requests patch the library. Put this snippet to your
application main entry point.


.. code-block:: python

   __import__('ddtrace_graphql').patch()

   # OR

   from ddtrace_graphql import patch
   patch()


Check out the `datadog trace client <http://pypi.datadoghq.com/trace/docs/>`_
for all supported libraries and frameworks.

.. note:: For the patching to work properly, ``patch`` needs to be called
          before any other imports of the ``graphql`` function.

.. code-block:: python

    # from that point all calls to graphql are traced

    from graphql import graphql
    result = graphql(schema, query)


Trace only certain calls with ``traced_graphql`` function

.. code-block:: python

    from ddtrace_graphql import traced_graphql
    traced_graphql(schema, query)


Development
===========

Install from source in development mode
---------------------------------------

.. code-block:: bash

   $ git clone https://github.com/beezz/ddtrace-graphql.git
   $ pip install --editable ddtrace-graphql[test]


Run tests
---------

.. code-block:: bash

   $ tox
