'''
This script collects block json files using the blockchain.com data api and saves them locally

inputs:     a date range (specified using a start date and end date) to collect blocks from

outputs:    json files for all blocks added from the start date up to and including the end date
'''
from time import perf_counter
from datetime import datetime
from dateutil import tz
from dateutil.relativedelta import *
from urllib.request import urlopen
import json
import logging
import os
import re


def get_days(start_day, end_day):
    """
    inputs:     two datetime objects

    returns:    datetime objects for every day from start_day up to, but not including end_day
    """
    days = []

    current_day = start_day
    while current_day <= end_day:
        days.append(current_day)
        current_day += relativedelta(days=+1)

    return days


def get_block_summaries(day):
    """
    inputs:     a datetime object

    returns:    basic information about each block added to the blockchain on the given day
                including the block hash and block height
    """
    timestamp = int(day.timestamp() * 1000)

    url = f'https://blockchain.info/blocks/{str(timestamp)}?format=json'
    response = urlopen(url)

    block_summaries = json.load(response)
    return block_summaries


def get_block(block_hash):
    """
    inputs:     a block hash

    returns:    a dictionary containg all information related to the specifed block
                including header information and a list of transactions contained within the block
    """

    url = f'https://blockchain.info/rawblock/{block_hash}'
    response = urlopen(url)

    block_data = json.load(response)
    return block_data


def load_json(filepath):
    with open(filepath, 'r') as fp:
        data = json.load(fp)
    return data


def save_json(filepath, data):
    with open(filepath, 'w') as output_file:
        json.dump(data, output_file)


# configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')

logging.basicConfig(
    filename='logs/collect_blocks.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s: %(message)s',
    level=logging.DEBUG)

program_start = perf_counter()

# set start and end days, and create datetime objects for all days in range
# time_period_days = 90
# end_day = datetime(year=2021, month=6, day=28, tzinfo = tz.gettz('Etc/GMT'))
# start_day = end_day - relativedelta(days=time_period_days)

start_day = datetime(year=2021, month=5, day=30, tzinfo=tz.gettz('Etc/GMT'))
end_day = datetime(year=2021, month=6, day=30, tzinfo=tz.gettz('Etc/GMT'))

days = get_days(start_day, end_day)

# create a directory to store the block json files
try:
    if not os.path.exists('../block_data'):
        os.mkdir('../block_data')
except BaseException:
    message = 'could not create block_data directory'
    logging.critical(message)
    raise

# used to keep track of errors that occur
failed_days = set()
failed_blocks = {}

for day in days:
    day_start = perf_counter()

    day_string = day.strftime("%Y-%m-%d")
    day_directory = f'../block_data/{day_string}'

    logging.info(f'collecting blocks from {day_string}\n')

    summary_file_exists = False

    # create a sub-directory for each day to help keep things organized
    if os.path.exists(day_directory):
        logging.debug(f'found pre-existing sub-directory for {day_string}')

        # check to see if block summaries have already been collected for this
        # day
        sfile_name_pattern = re.compile("^blocks*")
        for file in os.listdir(day_directory):
            if sfile_name_pattern.match(file):
                summary_file_exists = True

    else:
        try:
            os.mkdir(day_directory)
        except BaseException:
            failed_days.add(day_string)

            message = f'could not create directory for day {day_string}'
            logging.critical(message)
            raise

    # collect block summaries for the current day
    # either from the blockchain.com data api, or a local file, if one exists
    if summary_file_exists:
        block_summaries = load_json(
            f'{day_directory}/blocks_{day_string}.json')
        num_blocks = len(block_summaries)
        logging.debug(
            f'found pre-exisiting block summary file for {day_string} containing {num_blocks} blocks')

    else:
        try:
            block_summaries = get_block_summaries(day)
            num_blocks = len(block_summaries)

            logging.info(
                f'collected block summary file containing {num_blocks} blocks')

            file_name = f'../block_data/{day_string}/blocks_{day_string}.json'
            save_json(file_name, block_summaries)

        except BaseException:
            failed_days.add(day_string)
            logging.error(f'failed to load block summaries for {day_string}')

            continue

    # colllect all blocks added on the current day
    # either from the blockchain.com data api, or a local file, if one exists
    current_block_num = 1
    for block in block_summaries:
        block_start = perf_counter()

        block_hash = block.get('hash')

        # check to see if the block already exists locally
        block_exists = False
        for file in os.listdir(day_directory):
            if file == f'{block_hash}.json':
                block_exists = True
                logging.info(
                    f'block {block_hash} ({current_block_num}/{num_blocks}) already collected')
                current_block_num += 1
                break

        if block_exists:
            continue

        try:
            block_data = get_block(block_hash)

        except BaseException:
            if day_string in failed_blocks:
                failed_blocks[day_string].add(block_hash)

            else:
                failed_blocks[day_string] = {block_hash}

            logging.error(f'failed to load block {block_hash}')
            continue

        filename = f'../block_data/{day_string}/{block_hash}.json'
        save_json(filename, block_data)

        block_end = perf_counter()
        block_time = block_end - block_start
        logging.info(
            f'collected block {block_hash} ({current_block_num}/{num_blocks}) - block processing time: {block_time:.2f}s')
        current_block_num += 1

    day_end = perf_counter()
    day_time = (day_end - day_start) / 60
    logging.info(
        f'collected {num_blocks} blocks from {day_string} - day processing time: {day_time:.2f} minutes\n')

# report errors that occured

num_failed_days = len(failed_days)
failed_days_message = f'all blocks added on the following {num_failed_days} days could not be retrieved:\n\n'

for day in failed_days:
    failed_days_message += f'    {day}\n'
failed_days_message += '\n'

logging.error(failed_days_message)

num_failed_blocks = len(failed_blocks)
failed_blocks_message = f'the following {num_failed_blocks} individual blocks could not be retrieved:\n\n'

for day in failed_blocks:
    failed_blocks_message += f'    {day}\n'

    for hash in failed_blocks.get(day):
        failed_blocks_message += f'        {hash}\n'
failed_blocks_message += '\n'

logging.error(failed_blocks_message)

program_end = perf_counter()
execution_time = (program_end - program_start) / 60 / 60
logging.info(f'execution finished in {execution_time:.2f} hours\n')
