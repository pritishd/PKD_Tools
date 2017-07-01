'''
@package PKD_Tools.libMath
@brief Some maths related functions
'''

from fractions import Fraction

def normalise_range(originalVals, newNormal, roundValue=3):
    """
    normalize a list to fit a specific range, eg [-5,5],[0,1],[1,1].
    @param originalVals: The orginal list of number eg [8,4,2]
    @param newNormal: The new desired range  eg 1
    @param roundValue: What value should it rounded off to
    @return Return the normalised list [1,.5,.25]
    """
    # get max absolute value
    originalMax = max([abs(val) for val in originalVals])

    # normalize to desired range size
    return [round(float(val) / originalMax * newNormal, roundValue) for val in originalVals]


def calculate_proportions(proportionList, value, roundValue=3):
    """
    Calculate proportion of a value according to the list of number as weight
    @param proportionList: List of number eg [3,2]
    @param value: The value that needs to be proportioned eg 10
    @param roundValue: What value should it rounded off to
    @return: Redistrbuted number eg [6,4]
    """
    # Return the normalised list
    return [round(float(val) / sum(proportionList) * value, roundValue) for val in proportionList]


def redistribute_value(targetList, targetIndex, roundValue=3):
    """
    Zero out a value in the for target number in the list and give it to the rest of the value
    @param targetList: The list with the values
    @param targetIndex: The value that needs to the zeroed out
    @param roundValue: What value should it rounded off to
    @return: The new list with the redistributed value
    """
    # Grab the value
    targetValue = targetList[targetIndex]
    targetList[targetIndex] = 0
    redistributeList = calculate_proportions(targetList, targetValue, roundValue)
    return [round(x + y, roundValue) for x, y in zip(redistributeList, targetList)]


def digit_type(number):
    """
    Check if the number is odd, even of add
    @param number: Number that is being checked
    @return: String which describes the number
    """
    if number % 2 == 0:
        return "even"
    elif number % 2 == 1:
        return "odd"
    else:
        return "fraction"


def spread(start, end, count, mode=3):
    """
    Yield a sequence of evenly-spaced numbers between start and end.

    @param start: (int) The start of the sequence
    @param end: (int) The last frame in the sequence
    @param count: (int) How many section to divide into
    @param mode: (int) Whether the ends are included or not
    @return generator which is spread across

    Taken from
    http://code.activestate.com/recipes/577878/

    alternative solution
    http://code.activestate.com/recipes/579000-equally-spaced-numbers-linspace/

    spread(start, end, count [, mode]) -> generator

    The range start...end is divided into count evenly-spaced (or as close to
    evenly-spaced as possible) intervals. The end-points of each interval are
    then yielded, optionally including or excluding start and end themselves.
    By default, start is included and end is excluded.

    For example, with start=0, end=2.1 and count=3, the range is divided into
    three intervals:

        (0.0)-----(0.7)-----(1.4)-----(2.1)

    resulting in:

        list(spread(0.0, 2.1, 3))
        [0.0, 0.7, 1.4,2.1]

    Optional argument mode controls whether spread() includes the start and
    end values. mode must be an int. Bit zero of mode controls whether start
    is included (on) or excluded (off); bit one does the same for end. Hence:

        0 -> open interval (start and end both excluded)
        1 -> half-open (start included, end excluded)
        2 -> half open (start excluded, end included)
        3 -> closed (start and end both included)

    By default, mode=1 and only start is included in the output.

    (Note: depending on mode, the number of values returned can be count,
    count-1 or count+1.)
    """
    if not isinstance(mode, int):
        raise TypeError('mode must be an int')
    if count != int(count):
        raise ValueError('count must be an integer')
    if count <= 0:
        raise ValueError('count must be positive')
    if mode & 1:
        yield start
    width = Fraction(end - start)
    start = Fraction(start)
    for i in range(1, count):
        yield float(start + i * width / count)
    if mode & 2:
        yield end
