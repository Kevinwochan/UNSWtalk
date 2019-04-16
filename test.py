#!/usr/bin/python3.6
import sys, re, datetime,time

def text_to_markup ( text ) :
    # converts \n's to <br>
    new_text = re.sub (r'\\n','<br>',str(text))
    return new_text
for line in sys.stdin:
    print(text_to_markup(line))
