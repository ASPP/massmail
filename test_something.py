import numpy
import math

x = numpy.array([1,1])
y = numpy.array([2,2])
z = numpy.array([3,3])
def test_compare_array():
	assert all(x+y==z)

def test_arithmetic():
	assert 1==1
	assert 2*3 ==6
	assert 1+2==3
	assert math.isclose(1.1+2.2,3.3)

def test_len_list():
	lst = ['a','b','c']
	assert len(lst)==3

Newton =0
Leibniz =1
def test_Leibniz_better_than_Newton():
	assert Leibniz > Newton
	

