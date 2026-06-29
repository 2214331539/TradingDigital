"""Auth seam for the LLM module.

Routes depend on these wrappers rather than importing the platform IAM module
directly, so the auth provider can be swapped when the module is extracted.
"""

from tradedigital.platform.iam.deps import require_permission

__all__ = ["require_permission"]
