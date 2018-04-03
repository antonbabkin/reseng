one = 'keep'
two = 'it'
three = 'simple,'
four = 'stupid'

def make_list(*args):
    return list(args)

def make_sentence(words):
    return ' '.join(words)

def print_sentence(sentence):
    print(sentence)
    
def print_acronym(sentence):
    acronym = [word[0].upper() for word in sentence.split(' ')]
    print(*acronym, sep='')

all_four = make_list(one, two, three, four)
principle = make_sentence(all_four)
print_sentence(principle)
print_acronym(principle)