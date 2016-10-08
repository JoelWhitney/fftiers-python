__author__ = 'joelwhitney'
'''
A clustering program that uses FantasyPros data inspired by Boris Chen (http://www.borischen.co/)
This program utilizes unsupervised machine learning by flat clustering with KMeans -- a simple way
to uncover like tiers within the player data mined from FantasyPros (http://www.fantasypros.com/)

To Do's
-Output to CSV with tiers
-Add sms alert when graph updated (pass/fail)
-Make the script run continuously once a day
  -cPanel in cgi?
  -from Raspberry Pi
    -upload to site from here?
  -Add local v auto run option
    -once v timed runtime
-Make this program work with NHL data for Fantasy Hockey
'''
import argparse
import requests
from lxml import html
import traceback
import os
import logging
import logging.handlers
import datetime
import sys
import csv
from collections import OrderedDict
from threading import Timer
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from matplotlib import style
style.use("ggplot")
import time


def initialize_logging(logFile):
    """
    setup the root logger to print to the console and log to file
    :param logFile: string log file to write to
    """
    formatter = logging.Formatter("[%(asctime)s] [%(filename)30s:%(lineno)4s - %(funcName)30s()]\
         [%(threadName)5s] [%(name)10.10s] [%(levelname)8s] %(message)s")  # The format for the logs
    logger = logging.getLogger()  # Grab the root logger
    logger.setLevel(logging.DEBUG)  # Set the root logger logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    # Create a handler to print to the console
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh.setLevel(logging.DEBUG)
    # Create a handler to log to the specified file
    rh = logging.handlers.RotatingFileHandler(logFile, mode='a', maxBytes=10485760)
    rh.setFormatter(formatter)
    rh.setLevel(logging.DEBUG)
    # Add the handlers to the root logger
    logger.addHandler(sh)
    logger.addHandler(rh)


def verify_file_path(filePath):
    """
    verify file exists
    :param filePath: the joined directory and file name
    :return: Boolean: True if file exists
    """
    logger = logging.getLogger()
    ospath = os.path.abspath(filePath)
    ospath = ospath.replace("\\","\\\\")
    logger.debug("Evaluating if {} exists...".format(ospath))
    if not os.path.isfile(str(ospath)):
        logger.info("File not found: {}".format(filePath))
        return False
    else:
        return True


def csv_from_excel(full_file_name):
    """
    converts old xls to csv using this roundabout method
    :param full_file_name: downloaded xls file name
    """
    logger = logging.getLogger()
    logger.debug("Opening xls and csv files for conversion...")
    try:
        if verify_file_path(full_file_name):
            with open(full_file_name, 'r') as xlsfile, open(full_file_name[:-4] + '.csv', 'w', newline="\n", encoding="utf-8") as csv_file:
                xls_reader = csv.reader(xlsfile, delimiter='\t')
                csv_writer = csv.writer(csv_file)
                # skip first five lines
                for i in range(5):
                    next(xls_reader, None)
                # write subsequent rows to csv file
                for row in xls_reader:
                    csv_writer.writerow(row)
                logger.debug("Conversion succeeded...")
        else:
            logger.info("XLS file not found for: {} Skipping file...".format(full_file_name))
    except Exception as e:
        logger.info("Conversion failed with: {}".format(e))


def get_nfl_week(start_week_date):
    """
    get the nfl_week
    :param start_week_date: date object for Tuesday before 1st Thursday game
    :return: week: integer
    """
    week = 0
    today_date = datetime.datetime.now().date()
    if today_date >= start_week_date:
        # get days passed start date as date object
        difference_days = today_date - start_week_date
        # calculate week
        week = int((difference_days.days / 7) + 1)
        return week
    else:
        return week


def perform_session_download(args, url, full_file_name):
    """
    creates a session that allows the user to log in to FantasyPros and use the tokens
    :param args: list of parameters can be used to get data directories
    :param url: string of the export xls url
    :param full_file_name: string of the full file path and name of file to be saved
    """
    logger = logging.getLogger()
    try:
        # get payload values from command line parameters
        username, password, token = args.username, args.password, args.token
        payload = {"username": username,
                   "password": password,
                   "csrfmiddlewaretoken": token}
        # start session
        logger.debug("Starting download session...")
        session_requests = requests.session()
        login_url = "https://secure.fantasypros.com/accounts/login/?"
        result = session_requests.get(login_url)
        # refresh token on new request
        tree = html.fromstring(result.text)
        logger.debug("Updating token...")
        authenticity_token = list(set(tree.xpath("//input[@name='csrfmiddlewaretoken']/@value")))[0]
        payload["csrfmiddlewaretoken"] = authenticity_token
        session_requests.post(login_url,
                              data=payload,
                              headers=dict(referer=login_url))
        # prepare to write data to file
        logger.debug("Opening xls file to write data...")
        with open(full_file_name, 'wb') as handle:
            response = session_requests.get(url)
            if not response.ok:
                logger.info("Writing to xls failed...")
            for block in response.iter_content(1024):
                handle.write(block)
            logger.info("Writing to xls succeeded...")
    except Exception as e:
        logger.info("Session download failed with: {}".format(e))


def download_nhl_data(args, week, position_list):
    """
    download xls file from fantasy pros to the data_directory specified in args
    :param args: list of parameters can be used to get data directories
    :param week: integer week to be used when building file names
    :param position_list: list of positions to download, also used to build file names
    """
    logger = logging.getLogger()
    try:
        download_data = args.download_data
        if download_data == "True":
            # get data directory from command line parameters
            data_directory = args.data_directory
            # if preseason
            if week == 0:
                preseason_rankings = ['https://www.fantasypros.com/nhl/rankings/overall.php?export=xls',
                                      'https://www.fantasypros.com/nhl/rankings/c.php?export=xls',
                                      'https://www.fantasypros.com/nhl/rankings/lw.php?export=xls',
                                      'https://www.fantasypros.com/nhl/rankings/rw.php?export=xls',
                                      'https://www.fantasypros.com/nhl/rankings/d.php?export=xls',
                                      'https://www.fantasypros.com/nhl/rankings/g.php?export=xls']
                preseason_rankings_names = ['week-0-preseason-overall-raw.xls',
                                            'week-0-preseason-c-raw.xls', 'week-0-preseason-lw-raw.xls',
                                            'week-0-preseason-rw-raw.xls', 'week-0-preseason-d-raw.xls',
                                            'week-0-preseason-g-raw.xls']
                # download each link separately
                for item_position in range(len(preseason_rankings)):
                    # prepare link and path/filename
                    full_file_name = os.path.join(data_directory, preseason_rankings_names[item_position])
                    url = preseason_rankings[item_position]
                    # download using sessions
                    logger.debug("Starting session download...")
                    perform_session_download(args, url, full_file_name)
                    # convert the xls to csv
                    logger.debug("Starting xls conversion...")
                    csv_from_excel(full_file_name)
            # if not preseason
            else:
                # download each position from the position list
                for position in position_list:
                    # prepare link and path/filename
                    filename = 'week-' + str(week) + '-' + position + '-raw.xls'
                    full_file_name = os.path.join(data_directory, filename)
                    url = 'http://www.fantasypros.com/nfl/rankings/' + position + '.php?export=xls'
                    # download using sessions
                    logger.debug("Starting session download...")
                    perform_session_download(args, url, full_file_name)
                    # convert the xls to csv
                    logger.debug("Starting xls conversion...")
                    csv_from_excel(full_file_name)
                # download ros data
                # add ros-overall to position list?? What's the url like
    except Exception as e:
        logger.info("Generic download and conversion failed with: {}".format(e))


def get_position_setting(position, settings):
    """
    returns the max number of players to show and the k-value for position
    TODO's: comment, build in preseason stuff here (see plot() TODO)
    :param position: string position of setting you want
    :param settings: list of dictionaries of settings
    :returns: max_num, k_val: positional settings for plotting
    """
    logger = logging.getLogger()
    # iterate over dictionaries until dictionary for position is found
    for dict in settings:
        if str(dict.get('pos')).lower() == str(position).lower():
            max_num = dict.get('max_num')
            k_val = dict.get('k_val')
    return max_num, k_val


def lists_from_csv(position, week, data_directory):
    """
    builds lists from the csv to be used in the graphing
    :param position: string position used for building csv name
    :param week: integer week used for building csv name
    :param data_directory: string data directory used for building csv name
    :returns: rank_list, name_list, position_list, average_rank_list, standard_deviation_list, vs_adp_list: lists of data
    """
    logger = logging.getLogger()
    try:
        # set up empty lists for data storing
        rank_list = []
        name_list = []
        position_list = []
        average_rank_list = []
        standard_deviation_list = []
        vs_adp_list = []
        # build path/filename for csv file
        filename = 'week-' + str(week) + '-' + position + '-raw.csv'
        full_file_name = os.path.join(data_directory, filename)
        logger.debug("Trying to find csv file: {}...".format(full_file_name))
        # verify can find file before trying to process data
        if verify_file_path(full_file_name):
            # set up csv file to read
            with open(full_file_name, 'r') as csv_file:
                csv_reader = csv.reader(csv_file)
                # iterate over each row adding column to appropriate list
                for row in csv_reader:
                    logger.debug(row[:-1])
                    # preseason-overall includes position column, this accounts for it
                    if (position == 'preseason-overall' or position == 'flex') and (row[0]!= '' or row[6] != ''):
                        rank_list.append(int(row[0]))
                        name_list.append(str(row[1]))
                        position_list.append(str(row[2]))
                        average_rank_list.append(float(row[6]))
                        standard_deviation_list.append(float(row[7]))
                        # if row[9] != '' and row[0] != '':
                        #     vADP = int(row[9]) - int(row[0])
                        #     vs_adp_list.append(vADP)
                        # else: vs_adp_list.append('')
                    # all other positions will use this
                    elif (row[0] != '' or row[5] != ''):
                        rank_list.append(int(row[0]))
                        name_list.append(str(row[1]))
                        position_list.append(str(position))
                        average_rank_list.append(float(row[5]))
                        standard_deviation_list.append(float(row[6]))
            list_of_lists = [rank_list, name_list, position_list, average_rank_list, standard_deviation_list]
            return list_of_lists
        else:
            logger.info("CSV file not found for: {} - Week {}. Skipping position...".format(position, week))
    except Exception as e:
        logger.info("Building lists from csv failed with: {}".format(e))


def get_cluster_settings(week):
    """
    helper function for getting the parameters needed for plotting
    TODO's: comment, rethink this piece (maybe just return based on position instead of whole list
    :param week: int week used for getting right settings
    :returns: type_cluster_settings and ros_settings: list of dictionaries with the appropiate settings
    """
    logger = logging.getLogger()
    # preseason clustering settings
    preseason_cluster_settings = [{'pos': 'preseason-overall', 'plot1': 60, 'k_val_1': 10, 'plot2': 60, 'k_val_2': 7, 'plot3': 80, 'k_val_3': 6},
                                  {'pos': 'preseason-c', 'max_num': 24, 'k_val': 8},
                                  {'pos': 'preseason-lw', 'max_num': 40, 'k_val': 9},
                                  {'pos': 'preseason-rw', 'max_num': 60, 'k_val': 12},
                                  {'pos': 'preseason-d', 'max_num': 24, 'k_val': 8},
                                  {'pos': 'preseason-g', 'max_num': 24, 'k_val': 5}]
    # positional clustering settings
    weekly_pos_cluster_settings = [{'pos': 'qb', 'max_num': 24, 'k_val': 8},
                                   {'pos': 'rb', 'max_num': 40, 'k_val': 9},
                                   {'pos': 'wr', 'max_num': 60, 'k_val': 12},
                                   {'pos': 'te', 'max_num': 24, 'k_val': 8},
                                   {'pos': 'flex', 'max_num': 70, 'k_val': 13},
                                   {'pos': 'k', 'max_num': 24, 'k_val': 5},
                                   {'pos': 'dst', 'max_num': 24, 'k_val': 6}]
    # rest of season clustering settings
    ros_pos_cluster_settings = [{'pos': 'ros-overall', 'plot1': 60, 'k_val_1': 10, 'plot2': 60, 'k_val_2': 8, 'plot3': 80, 'k_val_3': 8},
                                {'pos': 'ros-qb', 'max_num': 32, 'k_val': 7},
                                {'pos': 'ros-rb', 'max_num': 50, 'k_val': 12},
                                {'pos': 'ros-wr', 'max_num': 64, 'k_val': 65/5},
                                {'pos': 'ros-te', 'max_num': 30, 'k_val': 7},
                                {'pos': 'ros-k', 'max_num': 20, 'k_val': 5},
                                {'pos': 'ros-dst', 'max_num': 25, 'k_val': 5}]
    # get cluster settings
    if week == 0:
        type_cluster_settings = preseason_cluster_settings
        ros_settings = ros_pos_cluster_settings
    else:
        type_cluster_settings = weekly_pos_cluster_settings
        ros_settings = ros_pos_cluster_settings
    return type_cluster_settings, ros_settings


def plot(position, week, args):
    """
    the first stage of the plotting that prepares the data to then be cluster_and_plotted
    TODO's: logging, utilize get_position_settings for preseason data, merge ros/preseason preparation
    :param position: string position used for getting data and position settings for the plotting
    :param week: integer week used for getting data
    :param args: list of parameters can be used to get data and plot directories
    """
    logger = logging.getLogger()
    logger.info("Plotting {} for Week {}".format(position.upper(), week))
    plot_filename = 'week-' + str(week) + '-' + position + '-raw.png'
    title = "Preseason - {} Tiers - {}".format(position[10:].upper(), time.strftime("%Y-%m-%d %H:%M")) if week == 0 else \
        "Week {} - {} Tiers - {}".format(week, position.upper(), time.strftime("%Y-%m-%d %H:%M"))
    data_directory = args.data_directory
    # get the cluster settings
    type_cluster_settings, ros_cluster_settings = get_cluster_settings(week)
    # get preseason settings
    if week == 0:
        list_of_lists = lists_from_csv(position, week, data_directory)
        # split lists for pos == overall
        if position == 'preseason-overall':
            for dict in type_cluster_settings:
                if dict.get('pos') == 'preseason-overall':
                    start1, stop1 = 0, dict.get('plot1')
                    start2 = stop1
                    stop2 = start2 + dict.get('plot2')
                    start3 = stop2
                    stop3 = start3 + dict.get('plot3')
                    sub_plot_1, sub_plot_2, sub_plot_3 = [], [], []
                    for list in list_of_lists: sub_plot_1.append(list[start1:stop1])
                    for list in list_of_lists: sub_plot_2.append(list[start2:stop2])
                    for list in list_of_lists: sub_plot_3.append(list[start3:stop3])
                    k_value_1, k_value_2, k_value_3 = dict.get('k_val_1'), \
                                                      dict.get('k_val_2'), \
                                                      dict.get('k_val_3')
                    sub_plot_1.append(k_value_1)
                    sub_plot_2.append(k_value_2)
                    sub_plot_3.append(k_value_3)
                    plot_list_of_lists = [sub_plot_1, sub_plot_2, sub_plot_3]
                    logger.debug("Getting ready to cluster and plot for {}".format(position.upper()))
                    labels = cluster_and_plot(plot_list_of_lists, plot_filename, title, args)
                    # create draft sheet
                    unordered_labels = [labels[start1:stop1], labels[start2:stop2], labels[start3:stop3]]
                    ordered_labels = reorder_labels(unordered_labels)
                    # truncate lists for website
                    web_list_of_lists = []
                    for list in list_of_lists: web_list_of_lists.append(list[start1:stop3])
                    web_list_of_lists.append(ordered_labels[start1:stop3])
                    logger.debug(web_list_of_lists)
                    fh_draft_sheet(args, web_list_of_lists)
        else:
            max_number, k_value = get_position_setting(position, type_cluster_settings)
            plot_1 = []
            for list in list_of_lists: plot_1.append(list[0:max_number])
            plot_1.append(k_value)
            plot_list_of_lists = [plot_1]
            cluster_and_plot(plot_list_of_lists, plot_filename, title, args)
    else:
        list_of_lists = lists_from_csv(position, week, data_directory)
        if position == 'ros-overall':
            for dict in type_cluster_settings:
                if dict.get('pos') == 'ros-overall':
                    start1, stop1 = 0, dict.get('plot1')
                    start2 = stop1
                    stop2 = start2 + dict.get('plot2')
                    start3 = stop2
                    stop3 = start3 + dict.get('plot3')
                    sub_plot_1, sub_plot_2, sub_plot_3 = [], [], []
                    for list in list_of_lists: sub_plot_1.append(list[start1:stop1])
                    for list in list_of_lists: sub_plot_2.append(list[start2:stop2])
                    for list in list_of_lists: sub_plot_3.append(list[start3:stop3])
                    k_value_1, k_value_2, k_value_3 = dict.get('k_val_1'), \
                                                      dict.get('k_val_2'), \
                                                      dict.get('k_val_3')
                    sub_plot_1.append(k_value_1)
                    sub_plot_2.append(k_value_2)
                    sub_plot_3.append(k_value_3)
                    plot_list_of_lists = [sub_plot_1, sub_plot_2, sub_plot_3]
                    logger.debug("Getting ready to cluster and plot for {}".format(position.upper()))
                    labels = cluster_and_plot(plot_list_of_lists, plot_filename, title, args)
                    # create draft sheet
                    unordered_labels = [labels[start1:stop1], labels[start2:stop2], labels[start3:stop3]]
                    ordered_labels = reorder_labels(unordered_labels)
                    # truncate lists for website
                    web_list_of_lists = []
                    for list in list_of_lists: web_list_of_lists.append(list[start1:stop3])
                    web_list_of_lists.append(ordered_labels[start1:stop3])
                    # ffb_weekly_sheet(args, web_list_of_lists)  # need the data to build this and delete 420/421
        else:
            max_number, k_value = get_position_setting(position, type_cluster_settings)
            plot_1 = []
            for list in list_of_lists: plot_1.append(list[0:max_number])
            plot_1.append(k_value)
            plot_list_of_lists = [plot_1]
            cluster_and_plot(plot_list_of_lists, plot_filename, title, args)
        web_list_of_lists = [[],[],[],[],[]]
        ffb_weekly_sheet(args, web_list_of_lists)


def cluster_and_plot(list_of_lists, raw_plot_filename, title, args):
    """
    the second stage of the plotting that clusters and plots the data
    TODO's: format graph
    :param list_of_lists: list of lists that has the pertinent plotting data
    :param plot_full_file_name: the file name of the plot to be saved
    """
    logger = logging.getLogger()
    logger.debug("Starting cluster and plotting...")

    list_count = 1  # count for appending to file names (necessary for split plots)
    # iterate over lists -- needed if plot is split into multiple
    # logger.debug("Iterating over plot #{} of {} subplot".format(list_count), len(list_of_lists))
    for list in list_of_lists:
        plot_filename = raw_plot_filename[:-4]  # strip .png off file name so adjustments can be made
        # plots to save
        plot_filename += '-{}.png'.format(list_count)
        plots_directory = args.plots_directory
        plot_full_file_name = os.path.join(plots_directory, plot_filename)
        # plots for website
        webplot_filename_split = plot_filename.split('-')
        webplot_filename = '-'.join(webplot_filename_split[2:])
        webplots_directory = args.ffbdraft_directory + "images/" if webplot_filename_split[1] == '0' else args.ffbweekly_directory + "images/"
        webplot_full_file_name = os.path.join(webplots_directory, webplot_filename)
        # assign lists
        rank_list, name_list, position_list, average_rank_list, standard_deviation_list, k_value = list[0], list[1], list[2], list[3], list[4], list[5]
        # empty list that will be converted into array
        average_rank_array = []
        for n in range(len(average_rank_list)):
            # build list from item and append the list to the list of lists
            item_list = [average_rank_list[n]]
            average_rank_array.append(item_list)
        rank_array = []
        for n in range(len(rank_list)):
            # build list from item and append the list to the list of lists
            item_list = [rank_list[n]]
            rank_array.append(item_list)
        # convert the list of lists to an array
        X = np.array(average_rank_array)
        Y = np.array(rank_list)
        # initialize KMeans and fit over the array
        kmeans = KMeans(n_clusters=k_value)
        kmeans.fit(X, Y)
        centroids = kmeans.cluster_centers_  # not used here
        # array of labels where a cluster value is assigned to each item
        labels = kmeans.labels_
        if list_count == 1:
            labels_copy = labels
        else:
            labels_copy = np.concatenate((labels_copy, labels))
            print(len(labels_copy))
        # color list that will automatically generate based on number of clusters
        colors = []
        color_cycle = iter(cm.rainbow(np.linspace(0, 5, len(labels))))
        for i in range(len(labels)):
            c = next(color_cycle)
            colors.append(c)
        # iterate over array and plot values, standard deviation, and color by clusters
        for i in range(len(X)):
            plt.errorbar(X[i][0], rank_list[i], xerr=standard_deviation_list[i], marker='.', markersize=4, color=colors[labels[i]], ecolor=colors[labels[i]])
            position = position_list[i][10:].upper() if len(position_list[i]) > 10 else position_list[i].upper()
            plt.text(X[i][0] + standard_deviation_list[i] + 1, rank_list[i], "{} {} ({})".format(name_list[i], position, rank_list[i]), size=6, color=colors[labels[i]],
                     ha="left", va="center")
        axes = plt.gca()
        axes.set_axis_bgcolor('#3A3A3A')

        plt.rcParams['savefig.facecolor'] = '#151515'
        plt.xlim(0,)
        plt.title(title, color='white')
        plt.xlabel('Average Ranking', color='white')
        plt.ylabel('Expert Consensus Ranking', color='white')

        plt.gca().invert_yaxis()  # top-left of graph should start at 1
        # plt.show()
        plt.savefig(plot_full_file_name, bbox_inches='tight')  # save the png file
        plt.savefig(webplot_full_file_name, bbox_inches='tight')  # save the png file
        plt.clf()  # clear plot after use otherwise subsequent iterations
        list_count += 1
    return labels_copy
    # except Exception as e:
    #     logger.info("Clustering and plotting failed with: {}".format(e))


def clustering_program(args, start_week_date, position_list):
    """
    adjusts the position list based on if preseason or not then runs program
    :param args: list of parameters can be used to get data and plot directories
    :param start_week_date: date object for start of season
    :param position_list: list of positions to be used
    """
    # week = get_nfl_week(start_week_date)
    # if week == 0:
    #     position_list.remove('flex') & position_list.insert(0, 'overall')
    #     download_nfl_data(args, week, position_list)
    #     for pos in position_list:
    #         preseason_pos = 'preseason-{}'.format(pos)
    #         plot(preseason_pos, week, args)
    # else:
    #     download_nfl_data(args, week, position_list)
    #     for pos in position_list:
    #         plot(pos, week, args)
    logger = logging.getLogger()
    week = get_nfl_week(start_week_date)
    adjust_position_list = position_list
    if week == 0:
        adjust_position_list.insert(0, 'overall')
        download_nhl_data(args, week, position_list)
        for pos in position_list:
            preseason_pos = 'preseason-{}'.format(pos)
            plot(preseason_pos, week, args)
    else:
        download_nhl_data(args, week, position_list)
        for pos in position_list:
            plot(pos, week, args)


def reorder_labels(unordered_labels):
    """
    orders the unordered labels from clustering algorithm
    :param unordered_labels: list of arrays
    :return: ordered_labels: list of integers that match pattern of before
    """
    starting_label = 0
    ordered_labels = []
    # for each array go through items
    for array in unordered_labels:
        print(len(array))
        starting_label += 1
        array_dictionary = {}
        item_values = list(OrderedDict.fromkeys(array))
        print(item_values)
        for i in range(len(item_values)):
            current_label = starting_label + i
            array_dictionary[item_values[i]] = current_label
        print(array_dictionary)
        starting_label = current_label
        # for each item in array
        for label in array:
            ordered_labels.append(array_dictionary.get(label))
    print(len(ordered_labels))
    return ordered_labels


def fh_draft_sheet(args, list_of_lists):
    """
    
    :param args: 
    :param list_of_lists: 
    :return: 
    """
    logger = logging.getLogger()
    tophalf_html = args.ffbdraft_directory + "_tophalf_draft_html.text"
    bottomhalf_html = args.ffbdraft_directory + "_bottomhalf_draft_html.text"
    destination_html = args.ffbdraft_directory + "FantasyHockeyDraftSheet.html"
    with open(tophalf_html, 'r') as tophalf_html_file, open(bottomhalf_html, 'r') as bottomhalf_html_file, open(destination_html, 'w') as destination_html_file:
        # write top half stuff
        tophalf_html_contents = tophalf_html_file.read()
        destination_html_file.write(tophalf_html_contents)

        position_images = {'C': "images/centerbt.png", 'LW': "images/leftwingbt.png", 'RW' : "images/rightwingbt.png",
                           'D': "images/defensebt.png", 'G': "images/goaliebt.png"}

        # do other stuff
        div_start = '\t\t\t\t<div class="col-xs-12 col-lg-2 rowpadsmall"> \n\t\t\t\t\t <ul class="list1"> \n'
        div_stop = '\t\t\t\t\t </ul> \n\t\t\t </div> \n'

        num_players = len(list_of_lists[0])
        players_per_column = 35
        starts = []
        for e in range(6): starts.append(int(e * players_per_column))
        stops = []
        for f in range(6): stops.append(starts[f] + players_per_column)

        for i in range(6):
            destination_html_file.write(div_start)
            rank_list, name_list, position_list, average_rank_list, std_dev, ordered_labels = list_of_lists[0][starts[i]:stops[i]], \
                                                                                              list_of_lists[1][starts[i]:stops[i]], \
                                                                                              list_of_lists[2][starts[i]:stops[i]], \
                                                                                              list_of_lists[3][starts[i]:stops[i]], \
                                                                                              list_of_lists[4][starts[i]:stops[i]], \
                                                                                              list_of_lists[5][starts[i]:stops[i]]

            print(name_list)
            for n in range(len(rank_list)):
                formatted_ranking = float("{0:.2f}".format(average_rank_list[n]))
                formatted_stdDev = float("{0:.2f}".format(std_dev[n]))
                position_image = position_images.get(position_list[n])
                # if vs_adp_list[n] == 0:
                #     vs_adp_str = '0'
                # elif vs_adp_list[n] != '':
                #     vs_adp_str = '-' + str(abs(vs_adp_list[n])) if vs_adp_list[n] < 0 else '+' + str(vs_adp_list[n])
                # else:
                #     vs_adp_str = ''
                player_info = '\t\t\t\t\t\t\t\t<li class="listitem1"><img src={} height=20px><small class="grey"> (T{}) {}&nbsp;</small><a style=' \
                              '"cursor: pointer;"> {}</a><small class="grey"> {} (stdDev: {})</small> <a href="#" class="" fp-player-name="{}"></a></li>\n'.format(position_image, ordered_labels[n], formatted_ranking, name_list[n], position_list[n], formatted_stdDev, name_list[n])
                destination_html_file.write(player_info)
                logger.debug(player_info)
            destination_html_file.write(div_stop)
        # write bottom half
        bottomhalf_html_contents = bottomhalf_html_file.read()
        destination_html_file.write(bottomhalf_html_contents)


def ffb_weekly_sheet(args, list_of_lists):
    """

    :param args:
    :param list_of_lists:
    :return:
    """
    tophalf_html = args.ffbweekly_directory + "_tophalf_weekly_html.text"
    bottomhalf_html = args.ffbweekly_directory + "_bottomhalf_weekly_html.text"
    destination_html = args.ffbweekly_directory + "FantasyFootballWeeklySheet.html"
    with open(tophalf_html, 'r') as tophalf_html_file, open(bottomhalf_html, 'r') as bottomhalf_html_file, open(destination_html, 'w') as destination_html_file:
        # write top half stuff
        tophalf_html_contents = tophalf_html_file.read()
        destination_html_file.write(tophalf_html_contents)

        position_images = {'QB': "images/quarterbackbt.png", 'RB': "images/runningbackbt.png", 'WR' : "images/receiverbt.png",
                           'TE': "images/tightendbt.png", 'DST': "images/defensebt.png", 'K': "images/kickerbt.png"}

        # do other stuff
        div_start = '\t\t\t\t<div class="col-xs-12 col-lg-2 rowpadsmall"> \n\t\t\t\t\t <ul class="list1"> \n'
        div_stop = '\t\t\t\t\t </ul> \n\t\t\t </div> \n'

        num_players = len(list_of_lists[0])
        players_per_column = 35
        starts = []
        for e in range(6): starts.append(int(e * players_per_column))
        stops = []
        for f in range(6): stops.append(starts[f] + players_per_column)

        for i in range(6):
            destination_html_file.write(div_start)
            rank_list, name_list, position_list, average_rank_list, ordered_labels = list_of_lists[0][starts[i]:stops[i]], \
                                                                                     list_of_lists[1][starts[i]:stops[i]], \
                                                                                     list_of_lists[2][starts[i]:stops[i]], \
                                                                                     list_of_lists[3][starts[i]:stops[i]], \
                                                                                     list_of_lists[4][starts[i]:stops[i]]
            print(name_list)
            for n in range(len(rank_list)):
                formatted_ranking = float("{0:.2f}".format(average_rank_list[n]))
                raw_position = ''.join([i for i in position_list[n] if not i.isdigit()])
                position_rank = ''.join([i for i in position_list[n] if i.isdigit()])
                position_image = position_images.get(raw_position)
                player_info = '\t\t\t\t\t\t\t\t<li class="listitem1"><img src={} height=20px><small class="grey"> (T{}) {}&nbsp;</small><a style=' \
                              '"cursor: pointer;"> {}</a><small class="grey"> {}-{}</small> <a href="#" class="" fp-player-name="{}"></a></li>\n'.format(position_image, ordered_labels[n], formatted_ranking, name_list[n],  raw_position, position_rank, name_list[n])
                destination_html_file.write(player_info)
            destination_html_file.write(div_stop)
        # write bottom half
        bottomhalf_html_contents = bottomhalf_html_file.read()
        destination_html_file.write(bottomhalf_html_contents)


def main(args):
    logger = logging.getLogger()
    # downloading settings
    position_list = ['c', 'lw', 'rw', 'd', 'g']
    start_week_date = datetime.date(2016, 12, 6)
    injured_player_list = []
    clustering_program(args, start_week_date, position_list)

    # # start loop
    # while True:
    #     # get timer components
    #     x = datetime.datetime.now()
    #     y = x.replace(day=x.day + 1, hour=23, minute=40, second=0, microsecond=0)
    #     delta_t = y - x
    #     secs = delta_t.seconds + 1
    #     print(secs)
    #     # after secs is up run the program
    #     t = Timer(secs, clustering_program(args, start_week_date, position_list))
    #     t.start()

# cd "/Users/joel8641/Downloads/fhtiers-python-master/src/ff-tiers.py" && py -3 "ff-tiers.py" -u "whitneyjb5" -p "999jbw" -t "reiHrx0n5o7YstOIFsZ5Gj29UVuuC80z"

if __name__ == "__main__":    # get all of the commandline arguments
    parser = argparse.ArgumentParser("FantasyPros clustering program")
    # required parameters
    parser.add_argument('-u', dest='username', help="FantasyPros username", required=True)
    parser.add_argument('-p', dest='password', help="FantasyPros password", required=True)
    parser.add_argument('-t', dest='token', help="FantasyPros token", required=True)
    # optional parameters
    parser.add_argument('-down', dest='download_data', help="Boolean for if script should download data", default="True")
    parser.add_argument('-dat', dest='data_directory', help="The directory where the data is downloaded", default="data/fhtiers/2016/")
    parser.add_argument('-plot', dest='plots_directory', help="The directory where the plots are saved", default="plots/fhtiers/2016/")
    parser.add_argument('-draft', dest='ffbdraft_directory', help="The directory where the draft html is saved", default="ffhdraft/")
    parser.add_argument('-weekly', dest='ffbweekly_directory', help="The directory where the weekly html is saved", default="ffhweekly/")
    # required for logging
    parser.add_argument('-logFile', dest='logFile', help='The log file to use', default="log.txt")
    args = parser.parse_args()
    initialize_logging(args.logFile)
    try:
        main(args)
    except Exception as e:
        logging.getLogger().critical("Exception detected, script exiting")
        print(e)
        logging.getLogger().critical(e)
        logging.getLogger().critical(traceback.format_exc().replace("\n"," | "))