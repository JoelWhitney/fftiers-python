import Datetime as Datetime

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
import ftplib
import argparse
import json
import requests
from lxml import html
import traceback
import time
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


class NFL(object):
    """
    NFL object for getting week, start date, etc.
    """

    def __int__(self):
        self._start_date = datetime.datetime(object)
        self._week = ''
        self.__get_week()

    def __get_start_date(self):
        """
        get the nfl_week
        :param start_week_date: date object for Tuesday before 1st Thursday game
        :return: week: integer
        """
        # do stuff
        start_date = datetime.datetime(object)
        self._start_date = start_date

    def __get_week(self):
        """
        get the nfl_week
        :param start_week_date: date object for Tuesday before 1st Thursday game
        :return: week: integer
        """
        week = 0
        today_date = datetime.datetime.now().date()
        if today_date >= self._start_date:
            difference_days = today_date - self._start_date
            week = int((difference_days.days / 7) + 1)
            self._week = week
        else:
            self._week = week

    @property
    def start_date(self):
        self.__get_start_date()
        return self._start_date

    @property
    def week(self):
        self.__get_week()
        return self._week


class FantasyPros(object):
    """
    FantasyPros Football object for getting data.
    """

    def __init__(self):
        pass

    def perform_session_download(league, url, save_file):
        """
        creates a session that allows the user to log in to FantasyPros and use the tokens
        :param args: list of parameters can be used to get data directories
        :param url: string of the export xls url
        :param save_file: string of the full file path and name of file to be saved
        """
        logger = logging.getLogger()
        try:
            login_url = "https://secure.fantasypros.com/accounts/login/?"
            payload = {"username": league.get('username'),
                       "password": league.get('password'),
                       "csrfmiddlewaretoken": league.get('token')}
            logger.debug("Starting download session...")
            session_requests = requests.session()
            result = session_requests.get(login_url)
            tree = html.fromstring(result.text)
            logger.debug("Updating token...")
            authenticity_token = list(set(tree.xpath("//input[@name='csrfmiddlewaretoken']/@value")))[0]
            payload["csrfmiddlewaretoken"] = authenticity_token
            session_requests.post(login_url,
                                  data=payload,
                                  headers=dict(referer=login_url))
            logger.debug("Opening file to write data...")
            with open(save_file, 'wb') as handle:
                response = session_requests.get(url)
                if not response.ok:
                    logger.info("Writing to xls failed...")
                for block in response.iter_content(1024):
                    handle.write(block)
                logger.debug("Writing to file succeeded for: {}...".format(save_file))
        except Exception as e:
            logger.info("Session download failed with: {}".format(e))

    def fantasy_football_download(self):
        pass

    def fantasy_hockey_download(self):
        pass


class FantasyProsFootball(object):
    """
    FantasyPros Football object for getting data.
    """

    def __init__(self):
        pass

    def download_nfl_data(self, args, week, position_list):
        """
        download xls file from fantasy pros to the data_directory specified in args
        TODO: should have list of players and their ID's from FP to join when calling csv_from_excel()
        TODO: two logins for each league in args. Iterate over both and download JSON to be parsed.; use position list not the ones below
        :param args: list of parameters can be used to get data directories
        :param week: integer week to be used when building file names
        :param position_list: list of positions to download, also used to build file names
        """
        logger = logging.getLogger()
        try:
            download_data = args.download_data
            if download_data == "True":
                if week == 0:
                    league = args.fp_credentials.get("league_1")
                    preseason_rankings = ["consensus", "qb", "rb", "wr", "te", "k", "dst"]
                    preseason_filename = ["overall", "qb", "rb", "wr", "te", "k", "dst"]
                    for item_position in range(len(preseason_rankings)):
                        save_file = os.path.join(args.data_directory,'week-0-preseason-{}-raw.xls'.format(preseason_filename[item_position]))
                        url = 'https://www.fantasypros.com/nfl/rankings/{}-cheatsheets.php?export=xls'.format(preseason_rankings[item_position])
                        logger.debug("Starting session download...")
                        perform_session_download(league, url, save_file)
                        logger.debug("Starting xls conversion...")
                        csv_from_excel(save_file)
                else:
                    for position in position_list:
                        filename = 'week-{}-{}-raw.xls'.format(str(week), position)
                        save_file = os.path.join(args.data_directory, filename)
                        url = 'http://www.fantasypros.com/nfl/rankings/{}.php?export=xls'.format(position)
                        logger.debug("Starting session download...")
                        perform_session_download(args, url, save_file)
                        logger.debug("Starting xls conversion...")
                        csv_from_excel(save_file)
                    logger.debug("Starting download for ROS positions...")
                    ros_rankings = ["overall", "qb", "rb", "wr", "te", "flex", "k", "dst"]
                    for position in ros_rankings:
                        ros_url = "https://www.fantasypros.com/nfl/rankings/ros-{}.php?export=xls".format(position)
                        filename = 'week-{}-{}-ros.xls'.format(str(week), position)
                        save_file = os.path.join(args.data_directory, filename)
                        logger.debug("Starting session download...")
                        perform_session_download(args.fp_credentials.get('league_{}'.format(index)), ros_url, save_file)
                    logger.debug("Starting download for JSONs...")
                    for index in range(len(args.fp_credentials)):
                        download_league_json = "https://partners.fantasypros.com/api/v1/mpb-leagues.php?callback=callback&sport=nfl&callback=jQuery2220588897147426499_1473771357333&_=1473771357334"
                        save_file_json = "week-{}-league-{}.json".format(week, index)
                        logger.debug("Starting session download for JSON...")
                        perform_session_download(args.fp_credentials.get('league_{}'.format(index)), download_league_json, save_file_json)

                        # add ros-overall to position list?? What's the url like
        except Exception as e:
            logger.info("Generic download and conversion failed with: {}".format(e))


class FantasyProsResults(object):

    def __init__(self):
        pass

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
                    # for headerLine in range(4):
                    #     next(xls_reader, None)
                    for headerLine in range(5):
                        next(xls_reader, None)

                    pos_headers = ["rank", "player name", "team", "matchup", "best rank", "worst rank", "avg rank", "std dev"]
                    flex_headers = ["rank", "player name", "pos", "team", "matchup", "best rank", "worst rank", "avg rank", "std dev"]
                    tup = flex_headers if "flex" in full_file_name.lower() else pos_headers
                    csv_writer.writerow(tup)

                    for tup in xls_reader:
                        csv_writer.writerow(tup)
                    logger.debug("Conversion succeeded for: {}...".format(full_file_name))
            else:
                logger.info("XLS file not found for: {}... Skipping file...".format(full_file_name))
        except Exception as e:
            logger.info("Conversion failed with: {}".format(e))


    def data_from_csv(position, week, data_directory):
        """
        **NEW - IN PROGRESS** builds dictionary of lists from the csv to be used in the graphing
        TODO: what about vADP I use in draft sheet (see lists_from_csv)
        :param position: string position used for building csv name
        :param week: integer week used for building csv name
        :param data_directory: string data directory used for building csv name
        :returns: rank_list, name_list, position_list, average_rank_list, standard_deviation_list, vs_adp_list: lists of data
        """
        logger = logging.getLogger()
        try:
            headers = {}
            data = {}
            filename = 'week-{}-{}-raw.csv'.format(str(week), position)
            csv_file = os.path.join(data_directory, filename)
            logger.debug("Trying to find csv file: {}...".format(csv_file))
            if verify_file_path(csv_file):
                with open(csv_file, 'r') as csv_file:
                    csv_file = csv.reader(csv_file)
                    for row in csv_file:
                        logger.debug("Row: {} Data: {}".format(csv_file.line_num, row))
                        if csv_file.line_num == 1:
                            for index in range(len(row)):
                                header = row[index]
                                print(str(header).lower().strip())
                                if str(header).lower().strip() != '': headers[str(header).lower().strip()] = index
                                if str(header).lower().strip() != '': data[str(header).lower().strip()] = []
                            logger.debug(headers)
                            logger.debug(data)
                        else:
                            for header in headers:
                                logger.debug("\t\tHeader: {}; Index: {}".format(header, headers.get(header)))
                                header_index = headers.get(header)
                                logger.debug("\t\tExisting Data: {}; Type: {}".format(data.get(header), type(data.get(header))))
                                logger.debug("\t\tData to Add: {}\n\n".format(row[header_index]))
                                data.get(header).append(row[header_index])
                        logger.debug(data)
                return headers, data
            else:
                logger.info("CSV file not found for: {} - Week {}. Skipping position...".format(position, week))
        except Exception as e:
            logger.info("Building data structure from csv failed with: {}".format(e))


    def get_position_setting(position, settings):
        """
        returns the max number of players to show and the k-value for position
        TODO's: comment, build in preseason stuff here (see plot() TODO)
        :param position: string position of setting you want
        :param settings: list of dictionaries of settings
        :returns: max_num, k_val: positional settings for plotting
        """
        logger = logging.getLogger()
        for dict in settings:
            if str(dict.get('pos')).lower() == str(position).lower():
                max_num = dict.get('max_num')
                k_val = dict.get('k_val')
        return max_num, k_val


    def get_cluster_settings(week):
        """
        helper function for getting the parameters needed for plotting
        TODO's: comment, rethink this piece (maybe just return based on position instead of whole list
        :param week: int week used for getting right settings
        :returns: type_cluster_settings and ros_settings: list of dictionaries with the appropiate settings
        """
        logger = logging.getLogger()
        # preseason clustering settings
        preseason_cluster_settings = [{'pos': 'preseason-overall', 'plot1': 60, 'k_val_1': 10, 'plot2': 60, 'k_val_2': 8, 'plot3': 80, 'k_val_3': 8},
                                      {'pos': 'preseason-qb', 'max_num': 24, 'k_val': 8},
                                      {'pos': 'preseason-rb', 'max_num': 40, 'k_val': 9},
                                      {'pos': 'preseason-wr', 'max_num': 60, 'k_val': 12},
                                      {'pos': 'preseason-te', 'max_num': 24, 'k_val': 8},
                                      {'pos': 'preseason-k', 'max_num': 24, 'k_val': 5},
                                      {'pos': 'preseason-dst', 'max_num': 24, 'k_val': 6}]
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


class Plot(object):

    def __init__(self):
        pass

    def plot(args, position, week):
        """
        the first stage of the plotting that prepares the data to then be cluster_and_plotted
        TODO's: logging, utilize get_position_settings for preseason data, merge ros/preseason preparation
        :param position: string position used for getting data and position settings for the plotting
        :param week: integer week used for getting data
        :param args: list of parameters can be used to get data and plot directories
        """
        logger = logging.getLogger()
        logger.info("Plotting {} for Week {}".format(position.upper(), week))
        plot_filename = 'week-{}-{}-raw.png'.format(str(week), position)
        title = "Preseason - {} Tiers - {}".format(position[10:].upper(), time.strftime("%Y-%m-%d %H:%M")) if week == 0 else \
            "Week {} - {} Tiers - {}".format(week, position.upper(), time.strftime("%Y-%m-%d %H:%M"))
        data_directory = args.data_directory
        type_cluster_settings, ros_cluster_settings = get_cluster_settings(week)
        headers, data = data_from_csv(position, week, data_directory)
        if 'overall' not in position: max_number, k_value = get_position_setting(position, type_cluster_settings)
        if week == 0:
            list_of_lists = [data.get('rank'), data.get('player name'), [position] * len(data.get('rank')),
                             data.get('avg rank'), data.get('std dev'), data.get('adp')]
            logger.debug(list_of_lists)
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
                        ffb_draft_sheet(args, web_list_of_lists)
            else:
                plot_1 = []
                for list in list_of_lists: plot_1.append(list[0:max_number])
                plot_1.append(k_value)
                plot_list_of_lists = [plot_1]
                cluster_and_plot(plot_list_of_lists, plot_filename, title, args)
        else:
            list_of_lists = [data.get('rank'), data.get('player name'), [position] * len(data.get('rank')),
                             data.get('avg rank'), data.get('std dev')]
            logger.debug(list_of_lists)
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
                plot_1 = []
                for list in list_of_lists: plot_1.append(list[0:max_number])
                plot_1.append(k_value)
                logger.debug(plot_1)
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
            # convert the list of lists to an array
            X = np.array(average_rank_array)
            # initialize KMeans and fit over the array
            kmeans = KMeans(n_clusters=k_value)
            kmeans.fit(X)
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
                logger.debug(type(X[i][0]))
                logger.debug(type(rank_list[i]))
                logger.debug(type(standard_deviation_list[i]))
                plt.errorbar(float(X[i][0]), float(rank_list[i]), xerr=float(standard_deviation_list[i]), marker='.', markersize=4, color=colors[labels[i]], ecolor=colors[labels[i]])
                position = position_list[i][10:].upper() if len(position_list[i]) > 10 else position_list[i].upper()
                # plt.text(str(X[i][0] + standard_deviation_list[i] + 1), str(rank_list[i]), "{} {} ({})".format(name_list[i], position, str(rank_list[i])), size=6, color=colors[labels[i]], ha="left", va="center")
                plt.text(float(X[i][0]) + float(standard_deviation_list[i]) + 1, float(rank_list[i]), "{} {} ({})".format(name_list[i], position, str(rank_list[i])), size=6, color=colors[labels[i]], ha="left", va="center")
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
        logger = logging.getLogger()
        week = get_nfl_week(start_week_date)
        adjust_position_list = position_list
        if week == 0:
            adjust_position_list.remove('flex')
            adjust_position_list.insert(0, 'overall')
            download_nfl_data(args, week, position_list)
            for pos in position_list:
                preseason_pos = 'preseason-{}'.format(pos)
                plot(args, preseason_pos, week)
            if args.upload_site == "True": ftp_upload(args, args.ffbdraft_directory)

        else:
            download_nfl_data(args, week, position_list)
            for pos in position_list:
                plot(args, pos, week)
            if args.upload_site == "True": ftp_upload(args, args.ffbweekly_directory)


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


def ffb_draft_sheet(args, list_of_lists):
    """
    
    :param args: 
    :param list_of_lists: 
    :return: 
    """
    tophalf_html = args.ffbdraft_directory + "_tophalf_draft_html.text"
    bottomhalf_html = args.ffbdraft_directory + "_bottomhalf_draft_html.text"
    destination_html = args.ffbdraft_directory + "FantasyFootballDraftSheet.html"
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
            rank_list, name_list, position_list, average_rank_list, vs_adp_list, ordered_labels = list_of_lists[0][starts[i]:stops[i]], \
                                                                                                  list_of_lists[1][starts[i]:stops[i]], \
                                                                                                  list_of_lists[2][starts[i]:stops[i]], \
                                                                                                  list_of_lists[3][starts[i]:stops[i]], \
                                                                                                  list_of_lists[4][starts[i]:stops[i]], \
                                                                                                  list_of_lists[5][starts[i]:stops[i]]
            print(name_list)
            for n in range(len(rank_list)):
                formatted_ranking = float("{0:.2f}".format(average_rank_list[n]))
                raw_position = ''.join([i for i in position_list[n] if not i.isdigit()])
                position_rank = ''.join([i for i in position_list[n] if i.isdigit()])
                position_image = position_images.get(raw_position)
                if vs_adp_list[n] == 0:
                    vs_adp_str = '0'
                elif vs_adp_list[n] != '':
                    vs_adp_str = '-' + str(abs(vs_adp_list[n])) if vs_adp_list[n] < 0 else '+' + str(vs_adp_list[n])
                else:
                    vs_adp_str = ''
                player_info = '\t\t\t\t\t\t\t\t<li class="listitem1"><img src={} height=20px><small class="grey"> (T{}) {}&nbsp;</small><a style=' \
                              '"cursor: pointer;"> {}</a><small class="grey"> {}-{} (vADP: {})</small> <a href="#" class="" fp-player-name="{}"></a></li>\n'.format(position_image, ordered_labels[n], formatted_ranking, name_list[n],  raw_position, position_rank, vs_adp_str, name_list[n])
                destination_html_file.write(player_info)
            destination_html_file.write(div_stop)
        # write bottom half
        bottomhalf_html_contents = bottomhalf_html_file.read()
        destination_html_file.write(bottomhalf_html_contents)


def ffb_weekly_sheet(args, list_of_lists):
    """=

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


def ftp_upload_sub(ftp, path):
    """
    recursively handles any subfolders from ftp_upload(directory)
    :param ftp:
    :param path:
    :return:
    """
    ftp.retrlines('LIST')
    # print starting working directory
    files = os.listdir(path)
    os.chdir(path)
    print("Current working dir : {}".format(os.getcwd()))
    for f in files:
        print("Item : {}".format(f))
        if os.path.isfile(f):
            fh = open(f, 'rb')
            ftp.storbinary('STOR %s' % f, fh)
            fh.close()
        elif os.path.isdir(f):
            ftp.mkd(f)
            ftp.cwd(f)
            ftp_upload_sub(ftp, path)
            ftp.cwd('..')
            os.chdir('..')


def ftp_upload(args, path):
    """
    start the upload on the core working directory
    :param args:
    :param path:
    :return:
    """
    ftp_address = args.ftp_address
    ftp_username = path[:-1] + "@" + ftp_address
    ftp_password = args.ftp_password
    # print ftp home directory
    ftp = ftplib.FTP(ftp_address, ftp_username, ftp_password)
    ftp.retrlines('NLST')
    files = os.listdir(path)
    os.chdir(path)
    print("Current working dir : {}".format(os.getcwd()))
    # iterate over files in working directory
    for f in files:
        print("Item : {}".format(f))
        if os.path.isfile(f):
            fh = open(f, 'rb')
            ftp.storbinary('STOR %s' % f, fh)
            fh.close()
        elif os.path.isdir(f):
            print(f)
            try: ftp.mkd(f)
            except: pass
            ftp.cwd(f)
            ftp_upload_sub(ftp, f)
            ftp.cwd('..')
            os.chdir('..')


def main(args):
    logger = logging.getLogger()
    # downloading settings
    position_list = ['qb', 'rb', 'wr', 'te', 'flex', 'k', 'dst']
    start_week_date = datetime.date(2016, 9, 6)
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


if __name__ == "__main__":    # get all of the commandline arguments
    parser = argparse.ArgumentParser("FantasyPros clustering program")
    # required parameters
    parser.add_argument('-cred', dest='credentials', help='Pickle file that has credentials', default='credentials.p')
    # optional parameters
    parser.add_argument('-down', dest='download_data', help="Boolean for if script should download data", default="True")
    parser.add_argument('-upload', dest='upload_site', help="Boolean for if script should uploaded", default="True")
    parser.add_argument('-dat', dest='data_directory', help="The directory where the data is downloaded", default="data/fftiers/2016/")
    parser.add_argument('-plot', dest='plots_directory', help="The directory where the plots are saved", default="plots/fftiers/2016/")
    parser.add_argument('-draft', dest='ffbdraft_directory', help="The directory where the draft html is saved", default="ffbdraft/")
    parser.add_argument('-weekly', dest='ffbweekly_directory', help="The directory where the weekly html is saved", default="ffbweekly/")
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