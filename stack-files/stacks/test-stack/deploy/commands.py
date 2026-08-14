# Copyright © 2022, 2023 Vulcanize
# Copyright © 2026 Bozeman Pass, Inc.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http:#www.gnu.org/licenses/>.

"""Deploy hooks for the test stack.

These exist to be observed rather than to do anything useful: they are how the
stack tool's own tests check that a stack's `deploy/commands.py` is found and
called.  Each hook leaves a side effect a shell test can assert on, so keep the
strings below in step with the assertions in bozemanpass/stack.

Previously written against the `stack_orchestrator` package and its hook
signatures, which left them unimportable and uncallable; see issue #8 there and
bozemanpass/stack#232 for why nothing noticed.
"""

from stack.deploy.deploy_types import DeployCommandContext
from stack.deploy.deployment_context import DeploymentContext
from stack.deploy.spec import Spec

CREATE_FILE_NAME = "create-file"
CREATE_FILE_CONTENT = "create-command-output-data"


def init(command_context: DeployCommandContext, spec: Spec) -> Spec:
    """Add a config variable to the spec `stack init` is generating.

    The tool passes the spec it has built so far and uses what comes back, so
    amend it rather than returning a fresh one.
    """
    config = spec.get("config", {})
    config["test-variable-1"] = "test-value-1"
    spec["config"] = config
    return spec


def create(
    command_context: DeployCommandContext,
    deployment_context: DeploymentContext,
    stack,
):
    """Write a known string to a known file in the deployment directory."""
    output_file_path = deployment_context.deployment_dir.joinpath(CREATE_FILE_NAME)
    with open(output_file_path, "w") as output_file:
        output_file.write(CREATE_FILE_CONTENT)
