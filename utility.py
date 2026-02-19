#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# utility.py - Helper functions

def userChoice(options: list) -> str:
    """Display a numbered menu and return the element chosen by the user (1-indexed input)."""
    madeValidChoice = False
    print(" -=-= Choose One =-=- ")
    for i in range(len(options)):
        print("[{}] : {}".format(i+1, options[i]))
    while not madeValidChoice:
        j = input("Your selection: ")
        j = int(j)
        if j <= len(options):
            madeValidChoice = True
            break
        else:
            pass
    # Return the user's integer choice (1-N)
    # but subtract one because options[] is zero-indexed.
    return options[j-1]