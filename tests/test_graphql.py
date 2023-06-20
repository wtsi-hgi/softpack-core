"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


from softpack_core.graphql import GraphQL


def test_environment_build_command(service_thread, cli) -> None:
    response = cli.invoke(GraphQL.command("query"))
    assert response.stdout == "GraphQL Query\n"
