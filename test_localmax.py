import numpy

def test_len_list():
    nlist = [1, 4, 5]
    assert len(nlist) == 5

def test_float_isseu():
    assert round(1.2 + 2.2,1) == 3.4

def test_numpy_array_add():
    x= numpy.array([1,1])
    y= numpy.array([2,2])
    z=numpy.array([3,3])
    assert (x+y==z).all()


def test_integer_sum():
    assert 1 + 3 == 4
