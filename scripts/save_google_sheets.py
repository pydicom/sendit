#!/bin/env python

# Command line script to get GB/day from manager, then save to google sheet.
from som.api.google.sheets import Client
from datetime import datetime, timedelta
import subprocess
import argparse
import os
import sys


def get_parser():
    parser = argparse.ArgumentParser(
    description="Sendit: save GB-day to Google Sheets")

    parser.add_argument("--sheet_id", dest='sheet_id', 
                        help="alpha-numerical string that is id for sheet", 
                        type=str, required=True)

    parser.add_argument("--days", dest='days', 
                        help="number of days to ask for metric (default is 1)", 
                        type=int, default=1)

    # Compare two images (a similarity tree)
    parser.add_argument('--save', dest='save', 
                        help="required flag to save new row (otherwise prints sheet)", 
                        default=False, action='store_true')

    return parser


def main():

    parser = get_parser()

    try:
        args = parser.parse_args()
    except:
        sys.exit(0)

    command = ["python", "manage.py", "summary_metrics", "--days", str(args.days)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    result,error =  process.communicate()
    
    gb_day = result["gb_per_day"]

    secrets = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if secrets is None:
        print("Please export client secrets file name at GOOGLE_SHEETS_CREDENTIALS")
        sys.exit(1)

    cli = Client()

    # Define date range for metric
    start_date = (datetime.now() - timedelta(days=days)).strftime("%m/%d/%Y")
    end_date = datetime.now().strftime("%m/%d/%Y")

    # Get previous values
    values = cli.read_spreadsheet(sheet_id=args.sheet_id)

    # Create row, append
    # pipeline	start_date	end_date	duration (days)	G/day GetIt	G/day SendIt
    # Define new row, add

    row = [1,              # pipeline
           start_date,     # start_date
           end_date,       # end_date
           None,           # duration (days)
           None,           # G/day GetIt
           amount,         # G/day SendIt
           None,           
           None,
           None,
           None,
           None]

    values.append(row)

    print_table(values)

    # Update sheet
    if args.save is True:
        print("Saving result to sheet %s" %args.sheet_id)
        result = cli.write_spreadsheet(args.sheet_id, values)


def print_table(table):
    for row in table:
        print(" |".join(row))

if __name__ == '__main__':
    main()
