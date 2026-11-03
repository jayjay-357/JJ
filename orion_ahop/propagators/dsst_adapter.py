"""DSST adapter boundary; solver and mean-element initialization not included."""
class DSSTNotImplementedError(NotImplementedError):
    pass

def propagate(*args, **kwargs):
    raise DSSTNotImplementedError(
        "DSST is not implemented in this milestone. A validated DSST solver, "
        "compatible mean elements, and configured force models are required."
    )
