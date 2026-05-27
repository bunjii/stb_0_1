
class StbError(Exception):
    pass


class StbParseError(StbError):
    """Input text could not be parsed into a model."""
    pass


class StbSolveError(StbError):
    """Static analysis failed."""
    pass
