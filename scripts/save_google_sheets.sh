#!/bin/bash

sheet_id=""

if [ -n "$sheet_id" ]; then
    echo "Please add the sheet id before running!"
    exit
fi

python /code/scripts/save_google_sheets.py --sheet_id $sheet_id --days 1 --save
