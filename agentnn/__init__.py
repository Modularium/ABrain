"""ABrain package wrapper.

The import path remains ``agentnn`` for compatibility during the rename migration.
"""

import sdk as sdk
from sdk import *  # re-export sdk components  # noqa: F403,F401
from sdk.__version__ import __version__

__all__ = [*sdk.__all__, "__version__"]  # noqa: F405
