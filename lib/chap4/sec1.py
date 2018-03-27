print('Hello, chap4, sec1.')

from . import sec2

def mutate_sec2(new_name):
    sec2.my_name = new_name
    