# predictions/utils/param_utils.py
def parse_int(value, default=None, minimum=None, maximum=None):
    try:
        i = int(value)
        if minimum is not None and i < minimum:
            i = minimum
        if maximum is not None and i > maximum:
            i = maximum
        return i
    except (TypeError, ValueError):
        return default
