class ComdabException(Exception):
    """The root class of exceptions raised by comdab."""


class UnhandledTypeError(ComdabException):
    """A SQL type not handled by comdab was encountered.

    Consider passing `allow_unknown_types=True`, or opening a feature request!"""


class OverlappingPathsError(ComdabException):
    """Several constraint paths overlap."""


class ComdabInternalError(ComdabException):
    """Something unexpected happened!

    If it escapes comdab internals, please report a bug."""
