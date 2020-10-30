#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# utility.py - Helper functions

def userChoice(options):
    madeValidChoice = False
    print(" == Choose One == ")
    for i in range(len(options)):
        print("[{}] : {}".format(i+1, options[i]))
    while not madeValidChoice:
        j = input("Your selection: ")
        if int(j) <= len(options):
            madeValidChoice = True
            break
        else:
            pass
    return options[j]