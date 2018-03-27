print('Hello, chap3, sec2.')

from . import sec1


def print_dict_as_table(d):
    '''Print dictionary as table.'''
    key_col_width = 20
    print('key'.rjust(key_col_width), '|', 'value')
    print('-' * key_col_width, '|', '--------')
    for key, val in d.items():
        print(key.rjust(key_col_width), '|', val)

def print_pub():
    '''Print publication from sec2 as table.'''
    print_dict_as_table(sec1.pub)