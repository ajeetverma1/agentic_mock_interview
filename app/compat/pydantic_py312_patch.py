# Python 3.12 compatibility patch for pydantic v1
# Handles all ForwardRef._evaluate call signatures

import sys

if sys.version_info >= (3, 12):
    from typing import ForwardRef

    _orig_evaluate = ForwardRef._evaluate

    def _evaluate(self, *args, **kwargs):
        """
        Compatible with:
        - Pydantic v1 calls
        - Python 3.12 typing calls
        """

        # If recursive_guard not provided, ensure it exists
        if "recursive_guard" not in kwargs:
            kwargs["recursive_guard"] = set()

        try:
            return _orig_evaluate(self, *args, **kwargs)
        except TypeError:
            # Fallback for older call patterns
            if len(args) >= 2:
                return _orig_evaluate(
                    self,
                    args[0],
                    args[1],
                    kwargs.get("recursive_guard", set()),
                )
            raise

    ForwardRef._evaluate = _evaluate
