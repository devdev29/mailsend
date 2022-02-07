import sys
import pandas as pd

msg = sys.stdin.readlines()
msg = ''.join([line for line in msg])
var_dict = dict()
in_cols = ['Name', 'Address']
df = pd.read_csv('./sample.csv', usecols=in_cols)
for i, word in enumerate(msg.split()):
    if word.startswith('@'):
        msg = msg.replace(word, f'variable{i}')
print(msg)
# print(df['Address'])
