import csv
import sys
import logging
from logging import handlers

positions = ['overall', 'qb', 'rb', 'wr', 'te', 'dst', 'k']

def initialize_logging(logFile):
    """
    setup the root logger to print to the console and log to file
    :param logFile: string log file to write to
    """
    formatter = logging.Formatter("[%(asctime)s] [%(filename)30s:%(lineno)4s - %(funcName)30s()]\
         [%(threadName)5s] [%(name)10.10s] [%(levelname)8s] %(message)s")  # The format for the logs
    logger = logging.getLogger()  # Grab the root logger
    logger.setLevel(logging.DEBUG)  # Set the root logger logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh.setLevel(logging.DEBUG)
    rh = logging.handlers.RotatingFileHandler(logFile, mode='a', maxBytes=10485760)
    rh.setFormatter(formatter)
    rh.setLevel(logging.DEBUG)
    logger.addHandler(sh)  # Add the handlers to the root logger
    logger.addHandler(rh)


def dictionary_from_csv():
    pass


def playerids_from_html(full_file_name):
    """
    converts old xls to csv using this roundabout method
    :param full_file_name: downloaded xls file name
    """
    logger = logging.getLogger()
    logger.debug("Opening html file and csv files for read/write...")
    try:
        with open(full_file_name, 'r', newline="\n") as htmlfile, open('/Users/joel8641/Dropbox/Projects/FF Tiers/fftiers-python/src/data/fantasypros-playerids/fantasypros_playerids.csv', 'a', newline="\n", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            html_content = htmlfile.readlines()
            for line in html_content:
                if '<td class="player-label">' in line:
                    print(line.split('class="fp-player-link '))
                    player_details = line.split('class="fp-player-link ')[1].split()
                    player_id = int(player_details[0].split('-')[2][:-1])
                    print(str(player_details))
                    player_name = str("{} {}".format(player_details[1], player_details[2]).split('\"')[1])
                    tuple = [player_id, player_name]
                    logger.debug("Log wrote for: {}".format(tuple))
                    csv_writer.writerow(tuple)
            logger.debug("Conversion succeeded for: {}...".format(full_file_name))
    except Exception as e:
        logger.info("Conversion failed with: {}".format(e))


if __name__ == "__main__":    # get all of the commandline arguments
    initialize_logging("logfile.txt")
    for position in positions:
        playerids_from_html('/Users/joel8641/Dropbox/Projects/FF Tiers/fftiers-python/src/data/fantasypros-playerids/ros-{}.html'.format(position))