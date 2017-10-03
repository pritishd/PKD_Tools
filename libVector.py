"""
@package PKD_Tools.libVector
Package dealing with vector maths
"""""

import operator

import maya.mel as mm
import math

from PKD_Tools import libMath, libUtilities


class vector:
    """ Vector class to do basic vector maths"""

    def __init__(self, data):
        self.data = data
        self.data[0] = round(data[0], 3)
        self.data[1] = round(data[1], 3)
        self.data[2] = round(data[2], 3)

    def __repr__(self):
        return repr(self.data)

    def __add__(self, other):
        return vector(map(lambda x, y: x + y, self, other))

    def __sub__(self, other):
        return vector(map(lambda x, y: x - y, self, other))

    def __mul__(self, other):
        return vector(map(lambda x, y: x * y, self, other))

    def __div__(self, other):
        return vector(map(lambda x, y: x / y, self, other))

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, item):
        self.data[index] = item

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        if (isinstance(other, vector)):
            vectorSelfNormal = self.normalise()
            vectorOther = other.normalise()
            return (vectorSelfNormal[0] == vectorOther[0]) and (vectorSelfNormal[1] == vectorOther[1]) and (
                vectorSelfNormal[2] == vectorOther[2])
        else:
            return NotImplemented

    def __ne__(self, other):
        equal_result = self.__eq__(other)
        if (equal_result is not NotImplemented): return not equal_result
        return NotImplemented

    def extend(self, other, factor):
        ##Find the Vector
        vec = vector(map(lambda x, y: y - x, self, other))
        ##Normalise the Vector
        vec = vec.normalise()
        ## Direction With Factor
        dirFac = vec * [factor, factor, factor]
        ##Return Final Position
        return vector([(other[0] + dirFac[0]), (other[1] + dirFac[1]), (other[2] + dirFac[2])])

    def normalise(self):
        return vector(list(mm.eval("unit <<%f,%f,%f>>" % (self.data[0], self.data[1], self.data[2]))))


def average(vecList, factor=0):
    """
    Average out list of vertices
    @param vecList: List of vectors
    @param factor: In case you want a customised ratio. Otherwise this is return the mid point.
    """
    if not factor:
        factor = len(vecList)
    return vector(
        [sum(map(operator.itemgetter(0), vecList)) / factor,
         sum(map(operator.itemgetter(1), vecList)) / factor,
         sum(map(operator.itemgetter(2), vecList)) / factor])


def distanceBetween(pointA, pointB):
    """
    Calculation to return the distance between 2 point positions
    """
    return math.sqrt(math.pow((pointA[0] - pointB[0]), 2) +
                     math.pow((pointA[1] - pointB[1]), 2) +
                     math.pow((pointA[2] - pointB[2]), 2))


def spread_vector(pointA, pointB, sections):
    """
    Break up a group of vertices into further sections
    @param pointA:
    @param pointB:
    @param sections: How many vectors do you want to spread this vector
    @return: The vector delineated each vector
    """
    positions = []
    for i in range(3):
        positions.append(libMath.spread(pointA[i], pointB[i], sections))

    return libUtilities.transpose(positions)

