#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import typer

from argilla.cli.callback import init_callback

app = typer.Typer(invoke_without_command=True)


@app.callback(help="Displays information about the Argilla client and server")
def info() -> None:
    from rich.console import Console
    from rich.markdown import Markdown

    from argilla._version import version
    from argilla.cli.rich import get_argilla_themed_panel
    from argilla.client.api import active_client
    from argilla.client.apis.status import Status

    init_callback()

    server_info = Status(active_client().client).get_status()

    elasticsearch_version = (
        f"{server_info.elasticsearch.version.number} ({server_info.elasticsearch.version.distribution})"
        if server_info.elasticsearch.version.distribution
        else server_info.elasticsearch.version.number
    )

    panel = get_argilla_themed_panel(
        Markdown(
            f"- **Client version:** {version}\n"
            f"- **Server version:** {server_info.version}\n"
            f"- **ElasticSearch version:** {elasticsearch_version}\n"
        ),
        title="Argilla Info",
        title_align="left",
    )

    Console().print(panel)


if __name__ == "__main__":
    app()
