#!/usr/bin/env bash

# # 
# Author: Trevor Brindle (https://github.com/tabrindle)
# Source: https://gist.github.com/tabrindle/ed9f77b4e96f4c98b49b
# #

PARAMS=('-m 6 -q 70 -mt -af -progress')

if [ $# -ne 0 ]; then
	PARAMS=$@;
fi

cd $(pwd)

shopt -s nullglob nocaseglob extglob

for FILE in *.@(jpg|jpeg|tif|tiff|png); do 
    cwebp $PARAMS "$FILE" -o "${FILE%.*}".webp;
done