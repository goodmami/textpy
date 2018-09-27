
def identity(x):
    return x

def constant(x):
    def constant_value(_):
        return x
    return constant_value
