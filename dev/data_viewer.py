##################################################
# Mizzou Racing Data Visualization Tool
# Created by Caleb Harris and Justin Bowers
# First Revision: 26 Nov 2024
# GitHub: CalebH1208/MR_Data_Visualization_Tool
# 
# This is a data visualization tool designed to be
# used alongside the Mizzou Racing data collection
# system. Any CSV can be used provided that the
# "Time" column exists, is unique, and is sorted.
##################################################

import random
import os
os.environ["QT_API"] = "PyQt6"

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QFileDialog, QTextEdit, QDialog
)
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QFont
import sys
import pickle

#################################################
# Class: DataType
# Attributes: 
#   index: The location of this header in the CSV
#   unit: Str for the unit of the data displayed
#   conv: Float multiplier applied to data to
#    convert between units
#   precision: Factor of 10 for floating point,
#    used for ints transmitted in 10x or 100x
#   range_low: Lower bound for data, applied
#    after the unit/precision conversion
#   range_high: Upper bound for data, applied
#    after the unit/precision conversion
#   max_step: The largest allowable step per unit
#    of time for data. Like a low pass filter
#   start_pos: A default starting value for data
# Methods:
#   reinit(): allows resetting of all attributes
#################################################
class DataType:
    def __init__(self, index = 0, unit = 'unknown', conv = 1, precision = 1, range_low = -18446744073709551615, range_high = 18446744073709551615, max_step = 18446744073709551615, start_pos = 0):
        self.index = index
        self.unit = unit
        self.conv = conv
        self.precision = precision
        self.range_low = range_low
        self.range_high = range_high
        self.max_step = max_step
        self.start_pos = start_pos

    def reinit(self, unit, conv, precision, range_low, range_high, max_step, start_pos):
        self.unit = unit
        self.conv = conv
        self.precision = precision
        self.range_low = range_low
        self.range_high = range_high
        self.max_step = max_step
        self.start_pos = start_pos

    def setUnit(self, unit):
        self.unit = unit

    def setConv(self, conv):
        self.conv = conv

    def setPrecision(self, prc):
        self.precision = prc

#################################################
# Class: Dataframe
# Attributes: 
#   header_version: The version of the data being
#    read in. v1 is a "normal" CSV w/ name header
#    and v2 encodes the DataType attributes into
#    the CSV.
#   headers: Dict for all headers stored as
#    name: DataType.
#   df: 2D array for actual data being stored
#   restarts: array to hold where in CSV there
#    are restarts occurring.
#   fill_headers: dict storing which headers
#    need interpolating for the different logging
#    speeds.
#   dir_path: Path to search for and store data
#################################################
class Dataframe:
    def __init__(self):
        self.header_version = 1
        self.headers = {}
        self.df = []
        self.restarts = [0]
        self.fill_headers = {}
        self.dir_path = ""

    def __str__(self):
        print(self.headers)
        for line in self.df:
            print(line)
        return ""
    
    # Function to create a buffer str from the headers, used to store these values into a CSV
    def headers_to_CSV(self):
        buf = ""
        buf += ','.join([str(header) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].unit) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].conv) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].precision) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].range_low) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].range_high) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].max_step) for header in self.headers]) + '\n'
        buf += ','.join([str(self.headers[header].start_pos) for header in self.headers]) + '\n'
        return buf
    
    # Function to convert the stored data into a CSV format for storing. Returns a string
    def data_to_CSV(self):
        buf = ""
        buf += '\n'.join([','.join([str(item) for item in line]) for line in self.df])
        return buf
    
    # Function which attempts to save all data in header v2 format into a "MONOLITH.CSV" file
    def save_data(self):
        if self.dir_path == "":
            return False
        outfile = self.dir_path + "/MONOLITH.CSV"
        try:
            with open(outfile, 'w') as f:
                f.write(self.headers_to_CSV())
                f.write(self.data_to_CSV())
                f.write("\n")
        except:
            print("Something went wrong writing file")
            return False
        return True

    # Main function of this class, which attempts to load the data in the Mizzou Racing data format
    # and interpolates data points from the lower HZ log files based on the "Time" column,
    # resulting in one Dataframe which is rectangular and holds all data.
    # This funciton will first attempt to read from the MONOLITH.CSV file, then defaults to
    # "1HZLOG.CSV", "10HZLOG.CSV", and "100HZLOG.CSV"
    def parse_data(self, dir_path):
        # Function which searches for the existance of the MONOLITH.CSV file
        def detect_monolith(dir_path):
            return os.path.exists(dir_path + "/MONOLITH.CSV")

        # Function which takes a list and attempts to cast all values in that list to a float
        def convert_list_to_num(lst):
            result = []
            for item in lst:
                try:
                    result.append(float(item))
                except ValueError:
                    result.append(item)
            return result

        # Function which searches the default files for which version of header is being used
        def detect_header(path):
            with open(path + "/100HZLOG.CSV") as file:
                for line in file:
                    line_list = convert_list_to_num(line.split(','))
                    if type(line_list[0]) == str and line_list[0] != 'Time':
                        return 2
                    elif type(line_list[0]) == float:
                        return 1
                return 0

        # Function which reads in and creates the DataType object from a header v1 (basic CSV)
        def header_v1(file):
            temp_dict = {}

            names = file.readline().rstrip().split(',')
            indices = range(len(names))

            for i in indices:
                temp_dict[names[i]] = DataType(index=(i))
            return temp_dict

        # Function which reads in the header v2 format, which consists of four header lines.
        # These are names, units, conversion rates, and precision (all described above)
        def header_v2(file):
            temp_dict = {}

            names = file.readline().rstrip().split(',')
            indecies = range(len(names))
            units = file.readline().rstrip().split(',')
            conversions = file.readline().rstrip().split(',')
            precisions = file.readline().rstrip().split(',')

            for i in indecies:
                temp_dict[names[i]] = DataType(i, units[i], conversions[i], precisions[i])
            return temp_dict
        
        # Function which inserts values from the given line into the data. This is used as the
        # logging rates are uneven, so data must be filled in to the nearest time value from the
        # lower HZ values into the higher HZ values.
        def insert_value(line, start):
            time = line.pop(0)
            ret = 0
            for x in range(start, len(self.df)):
                if self.df[x][0] > time:
                    self.df[x] = self.df[x] + (line)
                    return x+1
                else:
                    self.df[x] = self.df[x] + ([None]*len(line))
            if ret == 0 and start > 100:
                ret = -1
            return ret
        
        # Function which takes the lower HZ files and fills that data into the larger HZ data,
        # appending all new headers and ignoring repeated headers (such as time)
        def low_HZ_append(file):
            header_remove_dict = {}
            offset_loc = 0
            start = 0
            newheaders = {}

            if self.header_version == 1:
                newheaders = header_v1(file)
            elif self.header_version ==2:
                newheaders = header_v2(file)
            for NH in newheaders:
                if NH not in self.headers:
                    self.headers[NH] = newheaders[NH]
                    self.headers[NH].index = len(self.headers) - 1
                elif NH != 'Time':
                    header_remove_dict[NH] = newheaders[NH]

            self.fill_headers.update(newheaders.copy())

            for x in header_remove_dict:
                self.fill_headers.pop(x) 
            self.fill_headers.pop("Time")

            while True:
                line = file.readline()
                if not line: break
                line = line.rstrip().split(',')
                if len(line) > len(newheaders):
                    continue
                if line[0] == "Time":
                    offset_loc += 1
                    continue
                line = convert_list_to_num(line)
                line[0] += self.restarts[offset_loc]
                for x in header_remove_dict:
                    line.pop(header_remove_dict[x].index)
                
                start = insert_value(line, start)
                if start == -1:
                    break

        # Function which is used to read in the data in the event no MONOLITH.CSV has been
        # created yet. The default files then are 1HZLOG, 10HZLOG, and 100HZLOG
        def no_monolith():
            file1 = open(dir_path + '/1HZLOG.CSV', 'r')
            file10 = open(dir_path + '/10HZLOG.CSV', 'r')
            file100 = open(dir_path + '/100HZLOG.CSV', 'r')

            self.header_version = detect_header(dir_path)

            if self.header_version == 1:
                self.headers = header_v1(file100)
            if self.header_version == 2:
                self.headers = header_v2(file100)
            
            offset = 0
            while True:
                line = file100.readline()
                if not line: break
                line = line.rstrip().split(',')
                if len(line) > len(self.headers):
                    continue
                if line[0] == "Time":
                    offset = self.df[-1][0]
                    self.restarts.append(offset)
                    continue
                line = convert_list_to_num(line)
                line[0] += offset
                self.df.append(line)

            low_HZ_append(file10)
            low_HZ_append(file1)

            for i in range(len(self.df)):
                if len(self.df[i]) < len(self.headers):
                    self.df[i] = self.df[i] + ([None]*(len(self.headers)-len(self.df[i])))

            for header in self.fill_headers:
                y = self.headers[header].index

                first = 0
                first_ind = 0
                for x in range(len(self.df)):
                    while x < len(self.df)-1 and self.df[x][y] is None:
                        x +=1
            
                    second = self.df[x][y]
                    
                    second_ind = x
                    index_range = second_ind - first_ind

                    for i in range(index_range):
                        self.df[first_ind+i][y] = first 
                    first = second
                    first_ind = second_ind

            self.df.pop()

        # Function which reads in the data from the MONOLITH.CSV, in the header v2 format with
        # additional ranges, max_step, and start_vals
        def read_monolith():
            monolith = open(dir_path + '/MONOLITH.CSV', 'r')

            headers = monolith.readline().rstrip().split(",")
            indices = range(len(headers))
            units = monolith.readline().rstrip().split(",")
            convs = monolith.readline().rstrip().split(",")
            precisions = monolith.readline().rstrip().split(",")
            range_lows = monolith.readline().rstrip().split(",")
            range_highs = monolith.readline().rstrip().split(",")
            max_steps = monolith.readline().rstrip().split(",")
            start_vals = monolith.readline().rstrip().split(",")
            for i in indices:
                try:
                    self.headers[headers[i]] = DataType(i, units[i], float(convs[i]), float(precisions[i]), float(range_lows[i]), float(range_highs[i]), float(max_steps[i]), float(start_vals[i]))
                except ValueError:
                    self.headers[headers[i]] = DataType(i)

            while True:
                line = monolith.readline()
                if not line: break
                line = convert_list_to_num(line.rstrip().split(','))
                if None not in line:
                    self.df.append(line)
            
        # Function to load in the config file into the DataTypes. This file is a global
        # configuration and not meant to edited by the regular user. If other FSAE teams are
        # using this project, it is highly recommended that this file be edited once to match
        # the format of your data, then distributed to all team members using this program
        def load_config():
            config_file = "./CONFIG.CSV"
            config = {}
            with open(config_file, "r") as file:
                fields = file.readline().rstrip().split(",")
                while True:
                    line = file.readline()
                    if not line: break
                    line = line.rstrip().split(",")
                    line = convert_list_to_num(line)
                    config[line[0]] = line[1:]
            for header in self.headers:
                if(self.headers[header].conv == 1 and self.headers[header].unit == "unknown" and self.headers[header].precision == 1 and
                   self.headers[header].range_low < -17000000000000000000 and self.headers[header].range_high > 17000000000000000000 and
                   self.headers[header].max_step > 17000000000000000000 and self.headers[header].start_pos == 0):
                    self.headers[header].conv = config[header][0]
                    self.headers[header].unit = config[header][1]
                    self.headers[header].precision = config[header][2]
                    self.headers[header].range_low = config[header][3]
                    self.headers[header].range_high = config[header][4]
                    self.headers[header].max_step = config[header][5]
                    self.headers[header].start_pos = config[header][6]

        # Set global path
        self.dir_path = dir_path

        # Search for a MONOLITH.CSV in the path, and if found then read it in,
        # else, read in from the three default files
        if(detect_monolith(dir_path)):
            read_monolith()
        else:
            no_monolith()
        
        # Finally, load in the config file
        load_config()

    # Function to make a 2D Matplotlib plot with the given options. If the optional parameters are
    # passed, the data and dataTypes passed will be used, otherwise the stored data is used
    def make_plot_2D(self, figure, names, plot_title, remove_data_till_in_range, enable_grid, enforce_square, connect_lines, saved_graph = False, x_data = None, x_passType = None, y_data = None, y_passType = None):
        if not saved_graph:
            x_dataType = self.headers[names[0]]
            y_dataType = self.headers[names[1]]

            x_vals = [row[x_dataType.index] for row in self.df]
            y_vals = [row[y_dataType.index] for row in self.df]
        else:
            x_dataType = x_passType
            y_dataType = y_passType

            x_vals = x_data
            y_vals = y_data

        if remove_data_till_in_range:
            while True:
                x_vals[0] *= x_dataType.conv / x_dataType.precision
                y_vals[0] *= y_dataType.conv / y_dataType.precision
                if x_vals[0] < x_dataType.range_low or x_vals[0] > x_dataType.range_high or y_vals[0] < y_dataType.range_low or y_vals[0] > y_dataType.range_high:
                    x_vals.pop(0)
                    y_vals.pop(0)
                else:
                    break
        else:
            if x_dataType.range_low is not None:
                if (x_vals[0] < x_dataType.range_low or x_vals[0] > x_dataType.range_high) and x_dataType.start_pos is not None:
                    x_vals[0] = x_dataType.start_pos

            if y_dataType.range_low is not None:
                if (y_vals[0] < y_dataType.range_low or y_vals[0] > y_dataType.range_high) and y_dataType.start_pos is not None:
                    y_vals[0] = y_dataType.start_pos

        i = 1
        while i < len(y_vals):
            try:
                x_vals[i] *= x_dataType.conv / x_dataType.precision
                y_vals[i] *= y_dataType.conv / y_dataType.precision
                if x_dataType.range_low is not None:
                    if x_vals[i] < x_dataType.range_low or x_vals[i] > x_dataType.range_high:
                        x_vals[i] = x_vals[i-1]

                if y_dataType.range_low is not None:
                    if y_vals[i] < y_dataType.range_low or y_vals[i] > y_dataType.range_high:
                        y_vals[i] = y_vals[i-1]

                if x_dataType.max_step is not None:
                    if abs(x_vals[i] - x_vals[i-1]) > x_dataType.max_step:
                        x_vals[i] = x_vals[i-1]
                        
                if y_dataType.max_step is not None:
                    if abs(y_vals[i] - y_vals[i-1]) > y_dataType.max_step:
                        y_vals[i] = y_vals[i-1]

            except TypeError:
                print("type error")
                print(i)
            i += 1

        if x_dataType.unit == "unknown": 
            x_unit = ""
        else:
            x_unit = " (" + x_dataType.unit + ")"
        if y_dataType.unit == "unknown":
            y_unit = ""
        else:
            y_unit = " (" + y_dataType.unit + ")"

        plot = figure.add_subplot(111)

        if connect_lines:
            plot.plot(x_vals, y_vals, marker='o', label='label')
        else:
            plot.scatter(x_vals, y_vals, marker='o', label='label')
        plot.set_xlabel(names[0] + x_unit)
        plot.set_ylabel(names[1] + y_unit)
        plot.set_title(plot_title)
        plot.grid(enable_grid)
        
        if enforce_square:
            max_range = max(
                max(x_vals) - min(x_vals), 
                max(y_vals) - min(y_vals), 
            ) / 1.8

            center_x = (max(x_vals) + min(x_vals)) / 2.0
            center_y = (max(y_vals) + min(y_vals)) / 2.0

            plot.set_xlim(center_x - max_range, center_x + max_range)
            plot.set_ylim(center_y - max_range, center_y + max_range)
            plot.set_box_aspect(1)
        else: plot.set_box_aspect(None)
    
    # Function to make a 2D Matplotlib plot with the given options and colored by a 3rd dimension. 
    # If the optional parameters are passed, the data and dataTypes passed will be used, otherwise
    # the stored data is used
    def make_plot_3D_color(self, figure, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, connect_lines, saved_graph = False, x_data = None, x_passType = None, y_data = None, y_passType = None, z_data = None, z_passType = None):
        if not saved_graph:
            x_dataType = self.headers[names[0]]
            y_dataType = self.headers[names[1]]
            color_dataType = self.headers[names[2]]

            x_vals = [row[x_dataType.index] for row in self.df]
            y_vals = [row[y_dataType.index] for row in self.df]
            color_vals = [row[color_dataType.index] for row in self.df]
        else:
            x_dataType = x_passType
            y_dataType = y_passType
            color_dataType = z_passType

            x_vals = x_data
            y_vals = y_data
            color_vals = z_data

        ranges = [
            [x_dataType.range_low, x_dataType.range_high],
            [y_dataType.range_low, y_dataType.range_high],
            [color_dataType.range_low, color_dataType.range_high],
        ]
        convs = [x_dataType.conv, y_dataType.conv, color_dataType.conv]
        precisions = [x_dataType.precision, y_dataType.precision, color_dataType.precision]
        max_steps = [x_dataType.max_step, y_dataType.max_step, color_dataType.max_step]
        starting_pos = [x_dataType.start_pos, y_dataType.start_pos, color_dataType.start_pos]

        if x_dataType.unit == "unknown": 
            x_unit = ""
        else:
            x_unit = " (" + x_dataType.unit + ")"
        if y_dataType.unit == "unknown":
            y_unit = ""
        else:
            y_unit = " (" + y_dataType.unit + ")"
        if color_dataType.unit == "unknown":
            color_unit = ""
        else:
            color_unit = " (" + color_dataType.unit + ")"

        labels = [names[0] + x_unit, names[1] + y_unit, names[2] + color_unit]

        if remove_data_till_in_range:
            while True:
                x_vals[0] *= convs[0] / precisions[0]
                y_vals[0] *= convs[1] / precisions[1]
                color_vals[0] *= convs[2] / precisions[2]
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1] or
                    y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1] or
                    color_vals[0] < ranges[2][0] or color_vals[0] > ranges[2][1]):
                    x_vals.pop(0)
                    y_vals.pop(0)
                    color_vals.pop(0)
                else:
                    break
        else:
            if ranges[0][0] is not None:
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1]) and starting_pos[0] is not None:
                    x_vals[0] = starting_pos[0]

            if ranges[1][0] is not None:
                if (y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1]) and starting_pos[1] is not None:
                    y_vals[0] = starting_pos[1]

            if ranges[2][0] is not None:
                if (color_vals[0] < ranges[2][0] or color_vals[0] > ranges[2][1]) and starting_pos[2] is not None:
                    color_vals[0] = starting_pos[2]

        i = 1
        while i < len(y_vals):
            try:
                x_vals[i] *= convs[0] / precisions[0]
                y_vals[i] *= convs[1] / precisions[1]
                color_vals[i] *= convs[2] / precisions[2]
                if ranges[0] is not None:
                    if x_vals[i] < ranges[0][0] or x_vals[i] > ranges[0][1]:
                        x_vals[i] = x_vals[i-1]

                if ranges[1] is not None:
                    if y_vals[i] < ranges[1][0] or y_vals[i] > ranges[1][1]:
                        y_vals[i] = y_vals[i-1]
                
                if ranges[2] is not None:
                    if color_vals[i] < ranges[2][0] or color_vals[i] > ranges[2][1]:
                        color_vals[i] = color_vals[i-1]

                if max_steps[0] is not None:
                    if abs(x_vals[i] - x_vals[i-1]) > max_steps[0]:
                        x_vals[i] = x_vals[i-1]
                        
                if max_steps[1] is not None:
                    if abs(y_vals[i] - y_vals[i-1]) > max_steps[1]:
                        y_vals[i] = y_vals[i-1]
                
                if max_steps[2] is not None:
                    if abs(color_vals[i] - color_vals[i-1]) > max_steps[2]:
                        color_vals[i] = color_vals[i-1]

            except TypeError:
                print("type error")
                print(i)
                x_vals.pop(i)
                y_vals.pop(i)
                color_vals.pop(i)
            i += 1

        plot = figure.add_subplot(111)

        # Plot the line connecting the points
        if connect_lines:
            plot.plot(x_vals, y_vals, color='black', label='Data Line', linewidth = 0.5)
        
        color_scale = 0
        color_scale_low = None
        color_scale_high = None

        if enforce_color_range:
            color_scale = (color_dataType.range_high - color_dataType.range_low) * 0.1 / 2
            color_scale_low = color_dataType.range_low - color_scale
            color_scale_high = color_dataType.range_high + color_scale

        # Add colored scatter points
        scatter = plot.scatter(x_vals, y_vals, c=color_vals, cmap='nipy_spectral', vmin = color_scale_low, vmax = color_scale_high, s=20)

        # Add color bar
        cbar = figure.colorbar(scatter, ax=plot)
        cbar.set_label(labels[2])

        # Set plot attributes
        plot.set_title(plot_title)
        plot.set_xlabel(labels[0])
        plot.set_ylabel(labels[1])

        # Enable grid if specified
        if enable_grid:
            plot.grid(True)

        # Enforce square aspect ratio if specified
        if enforce_square:
            max_range = max(
                max(x_vals) - min(x_vals), 
                max(y_vals) - min(y_vals), 
            ) / 1.8

            center_x = (max(x_vals) + min(x_vals)) / 2.0
            center_y = (max(y_vals) + min(y_vals)) / 2.0

            plot.set_xlim(center_x - max_range, center_x + max_range)
            plot.set_ylim(center_y - max_range, center_y + max_range)
            plot.set_box_aspect(1)
        else: plot.set_box_aspect(None)

    # Function to make a 3D Matplotlib plot with the given options. If the optional parameters are
    # passed, the data and dataTypes passed will be used, otherwise the stored data is used
    def make_plot_3D(self, figure, names, plot_title, remove_data_till_in_range, enable_grid, enforce_cube, connect_lines, saved_graph = False, x_data = None, x_passType = None, y_data = None, y_passType = None, z_data = None, z_passType = None):
        if not saved_graph:
            x_dataType = self.headers[names[0]]
            y_dataType = self.headers[names[1]]
            z_dataType = self.headers[names[2]]

            x_vals = [row[x_dataType.index] for row in self.df]
            y_vals = [row[y_dataType.index] for row in self.df]
            z_vals = [row[z_dataType.index] for row in self.df]
        else:
            x_dataType = x_passType
            y_dataType = y_passType
            z_dataType = z_passType

            x_vals = x_data
            y_vals = y_data
            z_vals = z_data

        convs = [x_dataType.conv, y_dataType.conv, z_dataType.conv]
        ranges = [
            [x_dataType.range_low, x_dataType.range_high],
            [y_dataType.range_low, y_dataType.range_high],
            [z_dataType.range_low, z_dataType.range_high],
        ]
        precisions = [x_dataType.precision, y_dataType.precision, z_dataType.precision]
        max_steps = [x_dataType.max_step, y_dataType.max_step, z_dataType.max_step]
        start_pos = [x_dataType.start_pos, y_dataType.start_pos, z_dataType.start_pos]

        if x_dataType.unit == "unknown": 
            x_unit = ""
        else:
            x_unit = " (" + x_dataType.unit + ")"
        if y_dataType.unit == "unknown":
            y_unit = ""
        else:
            y_unit = " (" + y_dataType.unit + ")"
        if z_dataType.unit == "unknown":
            z_unit = ""
        else:
            z_unit = " (" + z_dataType.unit + ")"

        labels = [names[0] + x_unit, names[1] + y_unit, names[2] + z_unit]


        if remove_data_till_in_range:
            while True:
                x_vals[0] *= convs[0] / precisions[0]
                y_vals[0] *= convs[1] / precisions[1]
                z_vals[0] *= convs[2] / precisions[2]
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1] or
                    y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1] or
                    z_vals[0] < ranges[2][0] or z_vals[0] > ranges[2][1]):
                    x_vals.pop(0)
                    y_vals.pop(0)
                    z_vals.pop(0)
                else:
                    break
        else:
            if ranges[0][0] is not None:
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1]) and start_pos[0] is not None:
                    x_vals[0] = start_pos[0]

            if ranges[1][0] is not None:
                if (y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1]) and start_pos[1] is not None:
                    y_vals[0] = start_pos[1]

            if ranges[2][0] is not None:
                if (z_vals[0] < ranges[2][0] or z_vals[0] > ranges[2][1]) and start_pos[2] is not None:
                    z_vals[0] = start_pos[2]

        i = 1
        while i < len(y_vals):
            try:
                x_vals[i] *= convs[0] / precisions[0]
                y_vals[i] *= convs[1] / precisions[1]
                z_vals[i] *= convs[2] / precisions[2]
                if ranges[0] is not None:
                    if x_vals[i] < ranges[0][0] or x_vals[i] > ranges[0][1]:
                        x_vals[i] = x_vals[i-1]

                if ranges[1] is not None:
                    if y_vals[i] < ranges[1][0] or y_vals[i] > ranges[1][1]:
                        y_vals[i] = y_vals[i-1]
                
                if ranges[2] is not None:
                    if z_vals[i] < ranges[2][0] or z_vals[i] > ranges[2][1]:
                        z_vals[i] = z_vals[i-1]

                if max_steps[0] is not None:
                    if abs(x_vals[i] - x_vals[i-1]) > max_steps[0]:
                        x_vals[i] = x_vals[i-1]
                        
                if max_steps[1] is not None:
                    if abs(y_vals[i] - y_vals[i-1]) > max_steps[1]:
                        y_vals[i] = y_vals[i-1]
                
                if max_steps[2] is not None:
                    if abs(z_vals[i] - z_vals[i-1]) > max_steps[2]:
                        z_vals[i] = z_vals[i-1]

            except TypeError:
                print("type error")
                print(i)
                x_vals.pop(i)
                y_vals.pop(i)
                z_vals.pop(i)
                i -= 1

            i += 1

        plot = figure.add_subplot(111, projection='3d')

        # Set labels and title
        plot.set_title(plot_title)
        plot.set_xlabel(labels[0])
        plot.set_ylabel(labels[1])
        plot.set_zlabel(labels[2])

        # Scatter plot for the 3D data

        plot.scatter(x_vals, y_vals, z_vals, edgecolor='none', alpha=0.8)

        if connect_lines: plot.plot(x_vals, y_vals, z_vals)

        # Enable grid if specified
        plot.grid(enable_grid)

        # Enforce cube aspect ratio if specified (not straightforward in 3D but can scale axes)
        if enforce_cube:
            max_range = max(
                max(x_vals) - min(x_vals), 
                max(y_vals) - min(y_vals), 
                max(z_vals) - min(z_vals)
            ) / 1.8

            center_x = (max(x_vals) + min(x_vals)) / 2.0
            center_y = (max(y_vals) + min(y_vals)) / 2.0
            center_z = (max(z_vals) + min(z_vals)) / 2.0

            plot.set_xlim(center_x - max_range, center_x + max_range)
            plot.set_ylim(center_y - max_range, center_y + max_range)
            plot.set_zlim(center_z - max_range, center_z + max_range)
            plot.set_box_aspect((1,1,1))
        else: plot.set_box_aspect(None)

# Worker class used to async run functions
class Worker(QObject):
    finished = pyqtSignal(bool)

    def run(self,function):
        result = function()  
        self.finished.emit(result)

# Canvas class to embedd into the window for plots
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(fig)

# Class which will store all characteristic data of a graph, which can then be pickled into a 
# bytestream and stored for later graphing
class SavedGraph:
    def __init__(self, x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable):
        self.x_data = x_data
        self.x_dataType = x_dataType
        self.y_data = y_data
        self.y_dataType = y_dataType
        self.z_data = z_data
        self.z_dataType = z_dataType
        self.plot_type = plot_type
        self.names = names
        self.plot_title = plot_title
        self.remove_till_in_range = remove_data_till_in_range
        self.enable_grid = enable_grid
        self.enforce_color_range = enforce_color_range
        self.enforce_square = enforce_square
        self.enable = enable

# Main window class which holds the app
class MizzouDataTool(QMainWindow):
    # Function to initialize all widgets and layouts of the main page
    def __init__(self):
        super().__init__()

        self.data_file_path = "."
        self.data_frame = None

        # Set the window title
        self.setWindowTitle("Mizzou Data Tool")

        # Set the minimum dimensions of the window
        self.setMinimumWidth(1080)
        self.setMinimumHeight(720)

        # Class variable to control visibility
        self.data_frame_generated = False

        # Create the central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)

        # Title Section
        self.title_label = QLabel("Mizzou Data Tool")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFixedHeight(100)
        self.title_label.setStyleSheet("color:black")
        self.title_label.setFont(QFont("Arial", 50, QFont.Weight.Bold))
        self.set_title_background_color(241, 184, 45)  # Default yellow
        main_layout.addWidget(self.title_label)

        # File Path Input Section
        file_path_layout = QHBoxLayout()
        file_path_label = QLabel("File Path:")
        self.file_path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        generate_df_button = QPushButton("Generate Data Frame")
        save_df_button = QPushButton("Save Data Frame")
        save_df_button.setObjectName("save_df_button")
        file_path_layout.addWidget(file_path_label)
        file_path_layout.addWidget(self.file_path_input)
        file_path_layout.addWidget(browse_button)
        file_path_layout.addWidget(generate_df_button)
        file_path_layout.addWidget(save_df_button)
        main_layout.addLayout(file_path_layout)

        # Axis Selection Section
        self.axis_section_layout = QVBoxLayout()
        axis_row_layout = QHBoxLayout()

        # X-Axis Dropdown and Inputs
        self.x_axis_layout = self.create_axis_section("X-Axis")
        axis_row_layout.addLayout(self.x_axis_layout)

        # Y-Axis Dropdown and Inputs
        self.y_axis_layout = self.create_axis_section("Y-Axis")
        axis_row_layout.addLayout(self.y_axis_layout)

        # Z-Axis Dropdown and Inputs
        self.z_axis_layout = self.create_axis_section("Z-Axis")
        
        axis_row_layout.addLayout(self.z_axis_layout)

        # Add Axis Row to Axis Section Layout
        self.axis_section_layout.addLayout(axis_row_layout)

        main_layout.addLayout(self.axis_section_layout)

        # Extra Options Section
        self.extra_options_layout = QGridLayout()

        # Z-Axis Checkboxes
        self.use_z_axis_checkbox = QCheckBox("Use Z-Axis")
        self.use_z_axis_checkbox.stateChanged.connect(self.toggle_z_axis)
        self.toggle_z_axis(False)
        self.apply_z_as_color_checkbox = QCheckBox("Apply Z-Axis as Color")
        self.extra_options_layout.addWidget(self.use_z_axis_checkbox, 0, 0)
        self.extra_options_layout.addWidget(self.apply_z_as_color_checkbox, 1, 0)

        # Enable Grid Lines and Enforce Square Chech Boxes
        self.enable_grid_lines_checkbox = QCheckBox("Enable Grid Lines")
        self.enable_grid_lines_checkbox.setChecked(True)
        self.enable_grid_lines_checkbox.setObjectName("enable_grid_lines_checkbox")
        self.enforce_square_graph_checkbox = QCheckBox("Enforce Square Graph")
        self.enforce_square_graph_checkbox.setObjectName("enforce_square_graph_checkbox")
        self.extra_options_layout.addWidget(self.enable_grid_lines_checkbox, 0, 1)
        self.extra_options_layout.addWidget(self.enforce_square_graph_checkbox, 1, 1)

        # Delete Till in Range
        self.delete_till_in_range_checkbox = QCheckBox("Remove Data Until in Range")
        self.delete_till_in_range_checkbox.setChecked(True)
        self.delete_till_in_range_checkbox.setObjectName("delete_till_in_range_checkbox")
        self.extra_options_layout.addWidget(self.delete_till_in_range_checkbox, 0, 2)

        # Draw Line Between Points on Graph
        self.line_between_points_checkbox = QCheckBox("Line Between Points")
        self.line_between_points_checkbox.setChecked(False)
        self.line_between_points_checkbox.setObjectName("line_between_points_checkbox")
        self.extra_options_layout.addWidget(self.line_between_points_checkbox, 0, 3)

        # Make Graph Edges Equal to Range
        self.enforce_color_range_checkbox = QCheckBox("Enforce Color Range")
        self.enforce_color_range_checkbox.setChecked(False)
        self.enforce_color_range_checkbox.setObjectName("enforce_color_range_checkbox")
        self.extra_options_layout.addWidget(self.enforce_color_range_checkbox, 0, 4)

        # Use Custom Plot Title
        self.custom_plot_title_checkbox = QCheckBox("Use Custom Plot Title")
        self.custom_plot_title_line_edit = QLineEdit()
        self.custom_plot_title_line_edit.setPlaceholderText("Custom Plot Title")
        self.custom_plot_title_line_edit.setObjectName("custom_plot_title_line_edit")
        self.custom_plot_title_line_edit.setMaximumWidth(self.width()//4)
        self.extra_options_layout.addWidget(self.custom_plot_title_checkbox, 1, 2)
        self.extra_options_layout.addWidget(self.custom_plot_title_line_edit, 1, 3)

        self.preset_graphing_dropdown = QComboBox()
        self.preset_graphing_dropdown.setObjectName("extra_graph_buttons_dropdown")
        self.preset_graphs = self.get_preset_graphs()
        self.preset_graphing_dropdown.addItems(self.preset_graphs)
        self.preset_graphing_dropdown.currentIndexChanged.connect(self.execute_preset_graph)
        self.extra_options_layout.addWidget(self.preset_graphing_dropdown, 1, 4)

        main_layout.addLayout(self.extra_options_layout)

        # Graph Buttons Section
        self.graph_buttons_layout = QHBoxLayout()
        self.generate_graph_button = QPushButton("Generate Graph")
        self.generate_graph_button.clicked.connect(lambda: self.generate_graph(False))
        self.IFL_Button = QPushButton("I'm Feelin Lucky")
        self.IFL_Button.clicked.connect(self.up_all_night)
        self.extra_graph_buttons_dropdown = QComboBox()
        self.extra_graph_buttons_dropdown.setObjectName("extra_graph_buttons_dropdown")
        self.extra_graph_options = {  
                                    "Extra Graphing Options:": lambda: None,
                                    "Create Pop Out Graph": self.full_screen_figure, 
                                    "Save Graph": self.save_graph, 
                                    "Open Saved Graph": self.open_saved_graph, 
                                    "Clear Graph": self.clear_graph,
                                    "Save Preset Graph": self.save_preset_graph,
                                    "Remove Preset Graph": self.remove_preset_graph
                                   }
        self.extra_graph_buttons_dropdown.addItems(self.extra_graph_options.keys())
        self.extra_graph_buttons_dropdown.currentIndexChanged.connect(self.execute_extra_graph_button)
        self.zen_mode_button = QPushButton("Toggle Zen Mode")
        self.zen_mode_button.clicked.connect(self.enter_zen_mode)
        self.zen = False
        self.graph_buttons_layout.addWidget(self.generate_graph_button)    
        self.graph_buttons_layout.addWidget(self.IFL_Button)
        self.graph_buttons_layout.addWidget(self.zen_mode_button)
        self.graph_buttons_layout.addWidget(self.extra_graph_buttons_dropdown)
        main_layout.addLayout(self.graph_buttons_layout)

        # Canvas Section for Plots
        canvas_layout = QVBoxLayout()
        self.canvas = MplCanvas(width=5, height=4, dpi=150)
        self.array_window = []
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        canvas_layout.addWidget(self.toolbar)
        canvas_layout.addWidget(self.canvas)
        canvas_layout.setStretch(0,10)
        main_layout.addLayout(canvas_layout)

        self.specialty_item_layout = QGridLayout()

        # Terminal Section
        self.terminal_title = QLabel("Terminal:")
        self.terminal_title.setObjectName("terminal_title")
        self.terminal_title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.terminal_title.setFixedHeight(50)
        self.terminal_title.setStyleSheet("color: rgb(241, 184, 45);")
        self.specialty_item_layout.addWidget(self.terminal_title, 0, 0)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: black; color: white; font-family: Consolas;")
        self.terminal.setFixedHeight(100)
        self.specialty_item_layout.addWidget(self.terminal, 1, 0)

        # Extra Features
        self.extra_features_title = QLabel("Extra Features:")
        self.extra_features_title.setObjectName("extra_features_title")
        self.extra_features_title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.extra_features_title.setFixedHeight(50)
        self.extra_features_title.setStyleSheet("color: rgb(241, 184, 45);")
        self.specialty_item_layout.addWidget(self.extra_features_title, 0, 1)

        # Swap Headers
        self.swap_headers_layout = QVBoxLayout()
        self.swap_headers_label = QLabel("Swap Data:")
        self.swap_headers_label.setObjectName("swap_headers_label")
        self.swap_headers_dropdown_1 = QComboBox()
        self.swap_headers_dropdown_1.setObjectName("swap_headers_dropdown_1")
        self.swap_headers_dropdown_2 = QComboBox()
        self.swap_headers_dropdown_2.setObjectName("swap_headers_dropdown_2")
        self.swap_headers_button = QPushButton("Swap (Only use if certain)")
        self.swap_headers_button.clicked.connect(self.swap_headers)
        self.swap_headers_layout.addWidget(self.swap_headers_label)
        self.swap_headers_layout.addWidget(self.swap_headers_dropdown_1)
        self.swap_headers_layout.addWidget(self.swap_headers_dropdown_2)
        self.swap_headers_layout.addWidget(self.swap_headers_button)
        self.specialty_item_layout.addLayout(self.swap_headers_layout, 1, 1)

        main_layout.addLayout(self.specialty_item_layout)

        # Initially disable all elements below file path input
        self.set_elements_enabled(False)
        self.zen_mode_button.setEnabled(True)

        # Connect signals
        browse_button.clicked.connect(self.browse_file)
        generate_df_button.clicked.connect(self.generate_data_frame)
        save_df_button.clicked.connect(self.save_data_frame)

        self.enter_zen_mode()

    # Function which sets the title background
    def set_title_background_color(self, r, g, b):
        """
        Set a custom RGB background color for the title.
        """
        color = QColor(r, g, b)
        palette = self.title_label.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self.title_label.setAutoFillBackground(True)
        self.title_label.setPalette(palette)

    # Function to enable and disable elements, which is used for keeping the user from entering
    # values before data has been loaded
    def set_elements_enabled(self, enabled):
        """
        Enable or disable all elements below the file path input.
        """
        self.axis_section_layout.setEnabled(enabled)
        self.extra_options_layout.setEnabled(enabled)
        self.graph_buttons_layout.setEnabled(enabled)
        
        self.toggle_children(self.axis_section_layout, enabled)
        self.toggle_children(self.extra_options_layout, enabled)
        self.toggle_children(self.graph_buttons_layout, enabled)

    # Recursively disable child widgets
    def toggle_children(self, layout, state):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setEnabled(state)
            elif isinstance(layout.itemAt(i), QVBoxLayout) or isinstance(layout.itemAt(i), QHBoxLayout) or isinstance(layout.itemAt(i), QGridLayout):
                self.toggle_children(layout.itemAt(i), state)

    # Function used to make the three axis sections
    def create_axis_section(self, axis_name):
        """
        Create a section for an axis with a dropdown and additional input boxes.
        """
        layout = QVBoxLayout()

        axis = axis_name.split("-")[0]

        # Axis Title
        axis_label = QLabel(axis_name)
        axis_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        axis_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        axis_label.setFixedHeight(50)
        axis_label.setStyleSheet("color: rgb(241, 184, 45);")
        layout.addWidget(axis_label)

        # Dropdown
        axis_dropdown = QComboBox()
        axis_dropdown.setObjectName("axis_dropdown_" + axis)
        axis_dropdown.setMaximumHeight(25)
        axis_dropdown.currentIndexChanged.connect(lambda: self.update_axis_inputs(axis_dropdown))
        layout.addWidget(axis_dropdown)

        # Conversion Rate, Unit, and Precision Inputs
        inputs_grid_layout = QGridLayout()
        inputs_grid_layout.setObjectName("inputs_grid_layout_" + axis)

        # Conversion Rate Input
        conversion_rate_label = QLabel("Conversion Rate:")
        conversion_rate_label.setObjectName("conversion_rate_label_" + axis)
        conversion_rate_input = QLineEdit()
        conversion_rate_input.setObjectName("conversion_rate_input_" + axis)
        conversion_rate_input.setPlaceholderText("Enter a float")
        conversion_rate_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_grid_layout.addWidget(conversion_rate_label, 0, 0)
        inputs_grid_layout.addWidget(conversion_rate_input, 0, 1)

        # Unit Input
        unit_label = QLabel("Unit:")
        unit_label.setObjectName("unit_label_" + axis)
        unit_input = QLineEdit()
        unit_input.setObjectName("unit_input_" + axis)
        unit_input.setPlaceholderText("Enter a unit")
        unit_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_grid_layout.addWidget(unit_label, 0, 2)
        inputs_grid_layout.addWidget(unit_input, 0, 3)

        # Precision Input
        precision_label = QLabel("Precision:")
        precision_label.setObjectName("precision_label_" + axis)
        precision_input = QLineEdit()
        precision_input.setObjectName("precision_input_" + axis)
        precision_input.setPlaceholderText("Enter a float")
        precision_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_grid_layout.addWidget(precision_label, 0, 4)
        inputs_grid_layout.addWidget(precision_input, 0, 5)

        # Range High and Low
        range_label = QLabel("Range:")
        range_label.setObjectName("range_label_" + axis)
        inputs_grid_layout.addWidget(range_label, 1,0)
        inputs_range_layout = QHBoxLayout()
        range_low_input = QLineEdit()
        range_low_input.setObjectName("range_low_input_" + axis)
        range_low_input.setPlaceholderText("LOW")
        range_low_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_range_layout.addWidget(range_low_input)
        range_high_input = QLineEdit()
        range_high_input.setObjectName("range_high_input_" + axis)
        range_high_input.setPlaceholderText("HIGH")
        range_high_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_range_layout.addWidget(range_high_input)
        inputs_grid_layout.addLayout(inputs_range_layout, 1, 1)

        # Max step
        max_step_label = QLabel("Max Step:")
        max_step_label.setObjectName("max_step_label_" + axis)
        max_step_input = QLineEdit()
        max_step_input.setObjectName("max_step_input_" + axis)
        max_step_input.setPlaceholderText("smoothing step")
        max_step_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_grid_layout.addWidget(max_step_label, 1, 2)
        inputs_grid_layout.addWidget(max_step_input, 1, 3)

        # start pos
        start_pos_label = QLabel("Start Pos:")
        start_pos_label.setObjectName("start_pos_label_" + axis)
        start_pos_input = QLineEdit()
        start_pos_input.setObjectName("start_pos_input_" + axis)
        start_pos_input.setPlaceholderText("start pos")
        start_pos_input.textChanged.connect(lambda: self.update_save_color(axis))
        inputs_grid_layout.addWidget(start_pos_label, 1, 4)
        inputs_grid_layout.addWidget(start_pos_input, 1, 5)

        #Save Button
        save_button = QPushButton("SAVE SETTINGS")
        save_button.setObjectName("save_button_" + axis)
        save_button.clicked.connect(lambda: self.save_settings(axis))
        inputs_grid_layout.addWidget(save_button, 3, 0, 1, 6)

        layout.addLayout(inputs_grid_layout)
        return layout

    # Function which opens a sub dialog for the user to select the path to the data
    def browse_file(self):
        """
        Opens a file dialog to browse for a file path.
        """
        file_path = QFileDialog.getExistingDirectory(self, "Select File")
        if file_path:
            self.file_path_input.setText(file_path)
            self.log_message("Directory selected")
        else:
            self.log_message("directory selection cancelled")

    # Function which generates the data frame from the given path and enables all window functions
    def generate_data_frame(self):
        """
        Function for generating a data frame.
        Enables all options when data frame is ready.
        """
        self.log_message("Attempting Data Frame Generation")
        self.data_file_path = self.file_path_input.text()
        if(os.path.exists(str(self.data_file_path) + '/100HZLOG.CSV')) and (os.path.exists(str(self.data_file_path) + '/10HZLOG.CSV')) and (os.path.exists(str(self.data_file_path) + '/1HZLOG.CSV')):
            self.data_frame = Dataframe()
            self.data_frame.parse_data(self.data_file_path)
            self.data_frame_generated = True
            self.set_elements_enabled(True)
            self.toggle_z_axis(False)
            self.use_z_axis_checkbox.setChecked(False)
            self.apply_z_as_color_checkbox.setChecked(False)
            self.log_message("Data Frame has been generated!")
            self.populate_axis_dropdowns(self.data_frame.headers)
            if os.path.exists(str(self.data_file_path) + '/MONOLITH.CSV'):
                self.findChild(QWidget, "save_df_button").setStyleSheet("background-color: none")
            else:
                self.findChild(QWidget, "save_df_button").setStyleSheet("background-color: #0BA87A")
        else:
            self.log_message("An error occured please make sure that the 3 files needed exist in that directory.")

    # Function to async log to the terminal after the save process
    def finished_save(self, result):
        if result: 
            self.log_message("Data saved!")
        else:
            self.log_message("Something went wrong, the data was not saved.")

    # Function to save the data from the data frame into a MONOLITH.CSV file
    def save_data_frame(self):
        """
        Placeholder function for saving the data frame.
        """
        self.log_message("Saving data Frame please hold:")

        self.findChild(QWidget, "save_df_button").setStyleSheet("background-color: none")

        self.thread = QThread()

        self.worker = Worker()

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: (self.worker.run(self.data_frame.save_data)))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda result: self.finished_save(result))
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    # General function which logs information to the terminal widget
    def log_message(self, message: str):
        """
        Logs a message to the terminal at the bottom.
        """
        self.terminal.append(message)

    # Function to populate the axis dropdowns with the available headers from the data
    def populate_axis_dropdowns(self, options_dict):
        """
        Populate all axis dropdown menus with keys from a dictionary.
        """
        central_widget = self.findChild(QWidget, name = "central_widget")
        x_axis_dropdown = central_widget.findChild(QWidget, "axis_dropdown_X")
        y_axis_dropdown = central_widget.findChild(QWidget, "axis_dropdown_Y")
        z_axis_dropdown = central_widget.findChild(QWidget, "axis_dropdown_Z")
        swap_headers_dropdown_1 = central_widget.findChild(QWidget, "swap_headers_dropdown_1")
        swap_headers_dropdown_2 = central_widget.findChild(QWidget, "swap_headers_dropdown_2")

        for dropdown in [x_axis_dropdown, y_axis_dropdown, z_axis_dropdown,
                            swap_headers_dropdown_1, swap_headers_dropdown_2]:
            dropdown.clear()
            dropdown.addItems(options_dict.keys())
    
    # Function to enable or disable the z-axis fields
    def toggle_z_axis(self, state):
        z_axis_dropdown = self.z_axis_layout
        self.toggle_children(z_axis_dropdown, state)

    # Function to automatically update the axis input fields when a name is selected from the 
    # dropdown menu. These are pulled from the stored DataTypes.
    def update_axis_inputs(self, dropdown: QWidget):
        selected_item = dropdown.currentText()
        if selected_item in self.data_frame.headers:
            data_type = self.data_frame.headers[selected_item]
            axis = dropdown.objectName()[-1]
            central_widget = self.findChild(QWidget, name = "central_widget")

            # Get the appropriate inputs based on their object names
            conversion_rate_input = central_widget.findChild(QLineEdit, name = "conversion_rate_input_" + axis)  # Conversion Rate input (indexing is based on layout structure)
            unit_input = central_widget.findChild(QLineEdit, name = "unit_input_" + axis)  # Unit input
            precision_input = central_widget.findChild(QLineEdit, name = "precision_input_" + axis)  # Precision input
            range_low_input = central_widget.findChild(QLineEdit, "range_low_input_" + axis)
            range_high_input = central_widget.findChild(QLineEdit, "range_high_input_" + axis)
            max_step_input = central_widget.findChild(QLineEdit, "max_step_input_" + axis)
            start_pos_input = central_widget.findChild(QLineEdit, "start_pos_input_" + axis)            
            
            # Update the text of the input fields
            conversion_rate_input.setText(str(data_type.conv))
            unit_input.setText(str(data_type.unit))
            precision_input.setText(str(data_type.precision))
            if data_type.range_low < -17000000000000000000: range_low_input.setText("")
            else: range_low_input.setText(str(data_type.range_low))
            if data_type.range_high > 17000000000000000000: range_high_input.setText("")
            else: range_high_input.setText(str(data_type.range_high))
            if data_type.max_step > 17000000000000000000: max_step_input.setText("")
            else: max_step_input.setText(str(data_type.max_step))
            if data_type.start_pos == 0: start_pos_input.setText("")
            else: start_pos_input.setText(str(data_type.start_pos))

            self.findChild(QWidget, "save_button_" + axis).setStyleSheet("background-color: none")

    # Function to set the color of the save button to alert the user to an unsaved change
    def update_save_color(self, axis):
        self.findChild(QWidget, "save_button_" + axis).setStyleSheet("background-color: #0BA87A")

    # Function which saves all of the input fields to the dataframe, including error and bounds
    # checking. If fields are left blank then the default values are used.
    def save_settings(self, axis):
        central_widget = self.findChild(QWidget, name = "central_widget")

        # Get the header name from the dropdown text
        dropdown = central_widget.findChild(QWidget, "axis_dropdown_" + axis)
        selected_item = dropdown.currentText()

        if selected_item in self.data_frame.headers:
            # Get the appropriate inputs based on their object names
            conversion_rate_input = central_widget.findChild(QWidget, name = "conversion_rate_input_" + axis)
            unit_input = central_widget.findChild(QWidget, name = "unit_input_" + axis)
            precision_input = central_widget.findChild(QWidget, name = "precision_input_" + axis)
            range_low_input = central_widget.findChild(QWidget, name = "range_low_input_" + axis)
            range_high_input = central_widget.findChild(QWidget, name = "range_high_input_" + axis)
            max_step_input = central_widget.findChild(QWidget, name = "max_step_input_" + axis)
            start_pos_input = central_widget.findChild(QWidget, name = "start_pos_input_" + axis)

            # Get the texts of the inputs
            conversion_rate_text = conversion_rate_input.text()
            unit_text = unit_input.text()
            precision_text = precision_input.text()
            range_low_text = range_low_input.text()
            range_high_text = range_high_input.text()
            max_step_text = max_step_input.text()
            start_pos_text = start_pos_input.text()

            if conversion_rate_text == "": conversion_rate_text = 1
            if unit_text == "": unit_text = "unknown"
            if precision_text == "": precision_text = 1
            if range_low_text == "": range_low_text = -18446744073709551615
            if range_high_text == "": range_high_text = 18446744073709551615
            if max_step_text == "": max_step_text = 18446744073709551615
            if start_pos_text == "": start_pos_text = 0

            try:
                conversion_rate_text = float(conversion_rate_text)
                precision_text = float(precision_text)
                range_low_text = float(range_low_text)
                range_high_text = float(range_high_text)
                max_step_text = float(max_step_text)
                start_pos_text = float(start_pos_text)
            except ValueError:
                self.log_message("Invalid inputs, ensure that all are numbers")
                return

            self.data_frame.headers[selected_item].reinit(unit_text, conversion_rate_text, precision_text, range_low_text, range_high_text, max_step_text, start_pos_text)

            self.findChild(QWidget, "save_button_" + axis).setStyleSheet("background-color: none")
            self.findChild(QWidget, "save_df_button").setStyleSheet("background-color: #0BA87A")

    # Function to generate a graph into the canvas from all of the selected options and dropdowns
    def generate_graph(self, return_params):
        central_widget = self.findChild(QWidget, name = "central_widget")

        # Get the axis selections
        x_selection = central_widget.findChild(QWidget, "axis_dropdown_X").currentText()
        y_selection = central_widget.findChild(QWidget, "axis_dropdown_Y").currentText()
        z_selection = central_widget.findChild(QWidget, "axis_dropdown_Z").currentText()

        # Get all custom options
        z_enabled = self.use_z_axis_checkbox.isChecked()
        z_color = self.apply_z_as_color_checkbox.isChecked()
        enable_grid = central_widget.findChild(QWidget, "enable_grid_lines_checkbox").isChecked()
        enforce_color_range = central_widget.findChild(QWidget, "enforce_color_range_checkbox").isChecked()
        enforce_square = central_widget.findChild(QWidget, "enforce_square_graph_checkbox").isChecked()
        remove_till_in_range = central_widget.findChild(QWidget, "delete_till_in_range_checkbox").isChecked()
        use_custom_title = self.custom_plot_title_checkbox.isChecked()
        use_lines = central_widget.findChild(QWidget, "line_between_points_checkbox").isChecked()
        if use_custom_title:
            title = central_widget.findChild(QWidget, "custom_plot_title_line_edit").text()
        else:
            if z_enabled:
                title = z_selection + " vs. " + y_selection + " vs. " + x_selection
            else:
                title = y_selection + " vs. " + x_selection

        self.canvas.figure.clear()

        figure = self.canvas.figure
        try:
            if not return_params:
                if not z_enabled:
                    self.data_frame.make_plot_2D(figure, [x_selection, y_selection], title, remove_till_in_range, enable_grid, enforce_square, use_lines)
                elif z_color:
                    self.data_frame.make_plot_3D_color(figure, [x_selection, y_selection, z_selection], title, remove_till_in_range, enable_grid, enforce_color_range, enforce_square, use_lines)
                else:
                    self.data_frame.make_plot_3D(figure, [x_selection, y_selection, z_selection], title, remove_till_in_range, enable_grid, enforce_square, use_lines)
                self.canvas.draw()
            else:
                x_dataType = self.data_frame.headers[x_selection]
                x_data = [row[x_dataType.index] for row in self.data_frame.df]
                y_dataType = self.data_frame.headers[y_selection]
                y_data = [row[y_dataType.index] for row in self.data_frame.df]
                z_dataType = self.data_frame.headers[z_selection]
                z_data = [row[z_dataType.index] for row in self.data_frame.df]
                if not z_enabled: plot_type = 0
                elif z_color: plot_type = 1
                else: plot_type = 2
                return x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, [x_selection, y_selection, z_selection], title, remove_till_in_range, enable_grid, enforce_color_range, enforce_square, use_lines
        except Exception as e:
            self.log_message("Don't do that!!!")
            self.log_message(str(e))

    # Function to pop out a full screen window with the currently selected graph options. This
    # window will behave as a fully independant graph, and can be translated and rescaled
    def full_screen_figure(self):
            w = BreakoutWindow()
            x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable = self.generate_graph(True)
            w.fullscreen_graph(x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable)
            w.show_new_window()
            self.array_window.append(w)

    # Function to save a graph as a .MRGO bytestream. Uses docs.python.org/3/library/pickle.html
    def save_graph(self):
        try:
            x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable = self.generate_graph(True)
            save = SavedGraph(x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable)
            name,ft = QFileDialog.getSaveFileName(self, "Save :)", "./","Mizzou Racing Graph Object (*.MRGO)")
            with open(name, 'wb') as file:
                pickle.dump(save,file)
        except Exception as e:
            self.log_message("Save Graph Cancelled or incorrect file was used")
            self.log_message(str(e))

    # Function which opens a saved .MRGO object file and plots it into the canvas
    def open_saved_graph(self):
        try:
            path = QFileDialog.getOpenFileName(self, "Select File")
            
            with open(path[0], 'rb') as file:
                pickled_object = pickle.load(file)

            self.canvas.figure.clear()
            
            figure = self.canvas.figure
            if pickled_object.plot_type == 0:
                self.data_frame.make_plot_2D(figure, pickled_object.names, pickled_object.plot_title, pickled_object.remove_till_in_range, pickled_object.enable_grid, pickled_object.enforce_square, pickled_object.enable,
                True, pickled_object.x_data, pickled_object.x_dataType, pickled_object.y_data, pickled_object.y_dataType)
            elif pickled_object.plot_type == 1:
                self.data_frame.make_plot_3D_color(figure, pickled_object.names, pickled_object.plot_title, pickled_object.remove_till_in_range, pickled_object.enable_grid, pickled_object.enforce_color_range, pickled_object.enforce_square, 
                pickled_object.enable, True, pickled_object.x_data, pickled_object.x_dataType, pickled_object.y_data, pickled_object.y_dataType, pickled_object.z_data, pickled_object.z_dataType)
            else:
                self.data_frame.make_plot_3D(figure, pickled_object.names, pickled_object.plot_title, pickled_object.remove_till_in_range, pickled_object.enable_grid, pickled_object.enforce_square, pickled_object.enable,
                True, pickled_object.x_data, pickled_object.x_dataType, pickled_object.y_data, pickled_object.y_dataType, pickled_object.z_data, pickled_object.z_dataType)
            self.canvas.draw()
        except Exception as e:
            self.log_message("Open Graph Cancelled or incorrect file was used")
            self.log_message(str(e))

    # Function which clears the canvas of all graphs
    def clear_graph(self):
        self.canvas.figure.clear()
        self.canvas.draw()

    # Function which executes a functionality from the extra graphing options dropdown menu.
    # Will call the function stored in the dictionary of options and set the dropdown
    # back to the default option.
    def execute_extra_graph_button(self):
        self.extra_graph_options[self.extra_graph_buttons_dropdown.currentText()]()
        self.extra_graph_buttons_dropdown.setCurrentIndex(0)

    # Function which searches for and loads up options from the PRESETS.CSV file. This is intended
    # to allow the user to store commonly used graph setups as "presets". For example, the course
    # map graphing setup is by default kept in the PRESETS.CSV, as this will be commonly used
    def get_preset_graphs(self):
        ret_list = []
        ret_list.append("Load Preset Graph")
        with open("./PRESETS.CSV", "r") as preset_file:
            if not preset_file:
                self.log_message("Error: no presets file found")
                with open("./PRESETS.CSV", "w") as preset_file:
                    preset_file.write("name,x_selection,y_selection,z_selection,use_z_axis,use_z_axis_as_color")
            else:
                # Strip headers (these only exist for user convenience)
                preset_file.readline().rstrip().split(",")
                while True:
                    line = preset_file.readline()
                    if not line:
                        break
                    line = line.rstrip().split(",")
                    ret_list.append(line[0])
        return ret_list

    # Function which graphs from the preset graphs by setting the dropdown menus and calling the
    # standard graphing function
    def populate_preset_graph(self, x_sel, y_sel, z_sel, use_z, z_as_color):
        self.findChild(QWidget, "axis_dropdown_X").setCurrentIndex(self.data_frame.headers[x_sel].index)
        self.findChild(QWidget, "axis_dropdown_Y").setCurrentIndex(self.data_frame.headers[y_sel].index)
        self.findChild(QWidget, "axis_dropdown_Z").setCurrentIndex(self.data_frame.headers[z_sel].index)
        self.use_z_axis_checkbox.setChecked(use_z)
        self.apply_z_as_color_checkbox.setChecked(z_as_color)
        self.generate_graph(False)

    # Function which pulls info from the PRESETS.CSV file based on the currently selected preset
    # and then makes a call to graph that preset option.
    def execute_preset_graph(self):
        if self.preset_graphing_dropdown.currentIndex() == 0: return
        selection = self.preset_graphing_dropdown.currentText()
        with open("./PRESETS.CSV", "r") as preset_file:
            # Strip headers (these only exist for user convenience)
            preset_file.readline().rstrip().split(",")
            while True:
                line = preset_file.readline()
                if not line:
                    break
                line = line.rstrip().split(",")
                if line[0] == selection:
                    self.populate_preset_graph(x_sel=line[1], y_sel=line[2], z_sel=line[3], use_z= line[4]=="True", z_as_color= line[5]=="True")
        self.preset_graphing_dropdown.setCurrentIndex(0)

    # Function which saves the current graph options as a preset to the PRESETS.CSV file
    def save_preset_graph(self):
        save_preset_dialog = SavePresetPopoutWindow(self)
        if save_preset_dialog.exec() == QDialog.DialogCode.Accepted:
            preset_name = save_preset_dialog.get_name()

            with open("./PRESETS.CSV", "a") as presets_file:
                x_sel = self.findChild(QWidget, "axis_dropdown_X").currentText()
                y_sel = self.findChild(QWidget, "axis_dropdown_Y").currentText()
                z_sel = self.findChild(QWidget, "axis_dropdown_Z").currentText()
                use_z = self.use_z_axis_checkbox.isChecked()
                z_as_color = self.apply_z_as_color_checkbox.isChecked()
                line = ",".join([preset_name, x_sel, y_sel, z_sel, str(use_z), str(z_as_color)]) + "\n"
                presets_file.write(line)
            self.log_message("Preset sucesssfully saved!")
            self.preset_graphs = self.get_preset_graphs()
            self.preset_graphing_dropdown.clear()
            self.preset_graphing_dropdown.addItems(self.preset_graphs)

    # Function to remove a preset from the csv of presets. This is done via a popout dialog
    # with a dropdown of the presets which can be selected for removal
    def remove_preset_graph(self):
        remove_preset_dialog = RemovePresetPopoutWindow(self.preset_graphs, self)
        if remove_preset_dialog.exec() == QDialog.DialogCode.Accepted:
            preset_name = remove_preset_dialog.get_name()
            with open("./PRESETS.CSV", "r") as presets_file:
                presets = presets_file.readlines()
            with open("./PRESETS.CSV", "w") as presets_file:
                for preset in presets:
                    if preset.rstrip().split(",")[0] != preset_name:
                        presets_file.write(preset)

            self.log_message("Preset sucesssfully removed!")

            self.preset_graphs = self.get_preset_graphs()
            self.preset_graphing_dropdown.clear()
            self.preset_graphing_dropdown.addItems(self.preset_graphs)

    # Function which swaps the index associated with two headers, for use when data is accientally
    # labeled incorrectly. We have found this to be an issue with IMU data specifically due to
    # changes in mounting and orientation
    def swap_headers(self):
        central_widget = self.findChild(QWidget, "central_widget")
        header_1 = central_widget.findChild(QWidget, "swap_headers_dropdown_1").currentText()
        header_2 = central_widget.findChild(QWidget, "swap_headers_dropdown_2").currentText()
        if header_1 == header_2:
            self.log_message("Error: Cannot swap from same labels")
            return
        try:
            index_1 = self.data_frame.headers[header_1].index
            index_2 = self.data_frame.headers[header_2].index
            self.data_frame.headers[header_1].index = index_2
            self.data_frame.headers[header_2].index = index_1
            self.log_message("Successfully swapped data in " + header_1 + " and " + header_2 + "!")
        except:
            self.log_message("Error: Data failed to be swapped")

    # Function to enter the "zen mode" for this app, which removes all non-essential widgets from
    # the user's view. Note that these widgets still exist in this state and are interacted with by
    # the program, but cannot be seen until zen mode is toggled off, also with this function
    def enter_zen_mode(self):
        central_widget = self.findChild(QWidget, "central_widget")
        self.zen = not self.zen
        if self.zen:
            central_widget.findChild(QWidget, "conversion_rate_label_X").hide()
            central_widget.findChild(QWidget, "conversion_rate_label_Y").hide()
            central_widget.findChild(QWidget, "conversion_rate_label_Z").hide()
            central_widget.findChild(QWidget, "conversion_rate_input_X").hide()
            central_widget.findChild(QWidget, "conversion_rate_input_Y").hide()
            central_widget.findChild(QWidget, "conversion_rate_input_Z").hide()
            central_widget.findChild(QWidget, "unit_label_X").hide()
            central_widget.findChild(QWidget, "unit_label_Y").hide()
            central_widget.findChild(QWidget, "unit_label_Z").hide()
            central_widget.findChild(QWidget, "unit_input_X").hide()
            central_widget.findChild(QWidget, "unit_input_Y").hide()
            central_widget.findChild(QWidget, "unit_input_Z").hide()
            central_widget.findChild(QWidget, "precision_label_X").hide()
            central_widget.findChild(QWidget, "precision_label_Y").hide()
            central_widget.findChild(QWidget, "precision_label_Z").hide()
            central_widget.findChild(QWidget, "precision_input_X").hide()
            central_widget.findChild(QWidget, "precision_input_Y").hide()
            central_widget.findChild(QWidget, "precision_input_Z").hide()
            central_widget.findChild(QWidget, "range_label_X").hide()
            central_widget.findChild(QWidget, "range_label_Y").hide()
            central_widget.findChild(QWidget, "range_label_Z").hide()
            central_widget.findChild(QWidget, "range_low_input_X").hide()
            central_widget.findChild(QWidget, "range_low_input_Y").hide()
            central_widget.findChild(QWidget, "range_low_input_Z").hide()
            central_widget.findChild(QWidget, "range_high_input_X").hide()
            central_widget.findChild(QWidget, "range_high_input_Y").hide()
            central_widget.findChild(QWidget, "range_high_input_Z").hide()
            central_widget.findChild(QWidget, "max_step_label_X").hide()
            central_widget.findChild(QWidget, "max_step_label_Y").hide()
            central_widget.findChild(QWidget, "max_step_label_Z").hide()
            central_widget.findChild(QWidget, "max_step_input_X").hide()
            central_widget.findChild(QWidget, "max_step_input_Y").hide()
            central_widget.findChild(QWidget, "max_step_input_Z").hide()
            central_widget.findChild(QWidget, "start_pos_label_X").hide()
            central_widget.findChild(QWidget, "start_pos_label_Y").hide()
            central_widget.findChild(QWidget, "start_pos_label_Z").hide()
            central_widget.findChild(QWidget, "start_pos_input_X").hide()
            central_widget.findChild(QWidget, "start_pos_input_Y").hide()
            central_widget.findChild(QWidget, "start_pos_input_Z").hide()
            central_widget.findChild(QWidget, "save_button_X").hide()
            central_widget.findChild(QWidget, "save_button_Y").hide()
            central_widget.findChild(QWidget, "save_button_Z").hide()

            self.enable_grid_lines_checkbox.hide()
            self.enforce_square_graph_checkbox.hide()
            self.delete_till_in_range_checkbox.hide()
            self.line_between_points_checkbox.hide()
            self.enforce_color_range_checkbox.hide()
            self.custom_plot_title_checkbox.hide()
            self.custom_plot_title_line_edit.hide()
            self.preset_graphing_dropdown.hide()
            self.extra_options_layout.removeWidget(self.apply_z_as_color_checkbox)
            self.extra_options_layout.addWidget(self.apply_z_as_color_checkbox, 0, 1)

            self.extra_graph_buttons_dropdown.hide()

            self.terminal_title.hide()
            self.terminal.hide()

            self.extra_features_title.hide()
            self.swap_headers_label.hide()
            self.swap_headers_dropdown_1.hide()
            self.swap_headers_dropdown_2.hide()
            self.swap_headers_button.hide()

        else:
            central_widget.findChild(QWidget, "conversion_rate_label_X").show()
            central_widget.findChild(QWidget, "conversion_rate_label_Y").show()
            central_widget.findChild(QWidget, "conversion_rate_label_Z").show()
            central_widget.findChild(QWidget, "conversion_rate_input_X").show()
            central_widget.findChild(QWidget, "conversion_rate_input_Y").show()
            central_widget.findChild(QWidget, "conversion_rate_input_Z").show()
            central_widget.findChild(QWidget, "unit_label_X").show()
            central_widget.findChild(QWidget, "unit_label_Y").show()
            central_widget.findChild(QWidget, "unit_label_Z").show()
            central_widget.findChild(QWidget, "unit_input_X").show()
            central_widget.findChild(QWidget, "unit_input_Y").show()
            central_widget.findChild(QWidget, "unit_input_Z").show()
            central_widget.findChild(QWidget, "precision_label_X").show()
            central_widget.findChild(QWidget, "precision_label_Y").show()
            central_widget.findChild(QWidget, "precision_label_Z").show()
            central_widget.findChild(QWidget, "precision_input_X").show()
            central_widget.findChild(QWidget, "precision_input_Y").show()
            central_widget.findChild(QWidget, "precision_input_Z").show()
            central_widget.findChild(QWidget, "range_label_X").show()
            central_widget.findChild(QWidget, "range_label_Y").show()
            central_widget.findChild(QWidget, "range_label_Z").show()
            central_widget.findChild(QWidget, "range_low_input_X").show()
            central_widget.findChild(QWidget, "range_low_input_Y").show()
            central_widget.findChild(QWidget, "range_low_input_Z").show()
            central_widget.findChild(QWidget, "range_high_input_X").show()
            central_widget.findChild(QWidget, "range_high_input_Y").show()
            central_widget.findChild(QWidget, "range_high_input_Z").show()
            central_widget.findChild(QWidget, "max_step_label_X").show()
            central_widget.findChild(QWidget, "max_step_label_Y").show()
            central_widget.findChild(QWidget, "max_step_label_Z").show()
            central_widget.findChild(QWidget, "max_step_input_X").show()
            central_widget.findChild(QWidget, "max_step_input_Y").show()
            central_widget.findChild(QWidget, "max_step_input_Z").show()
            central_widget.findChild(QWidget, "start_pos_label_X").show()
            central_widget.findChild(QWidget, "start_pos_label_Y").show()
            central_widget.findChild(QWidget, "start_pos_label_Z").show()
            central_widget.findChild(QWidget, "start_pos_input_X").show()
            central_widget.findChild(QWidget, "start_pos_input_Y").show()
            central_widget.findChild(QWidget, "start_pos_input_Z").show()
            central_widget.findChild(QWidget, "save_button_X").show()
            central_widget.findChild(QWidget, "save_button_Y").show()
            central_widget.findChild(QWidget, "save_button_Z").show()

            self.enable_grid_lines_checkbox.show()
            self.enforce_square_graph_checkbox.show()
            self.delete_till_in_range_checkbox.show()
            self.line_between_points_checkbox.show()
            self.enforce_color_range_checkbox.show()
            self.custom_plot_title_checkbox.show()
            self.custom_plot_title_line_edit.show()
            self.preset_graphing_dropdown.show()
            self.extra_options_layout.removeWidget(self.apply_z_as_color_checkbox)
            self.extra_options_layout.addWidget(self.apply_z_as_color_checkbox, 1, 0)

            self.extra_graph_buttons_dropdown.show()

            self.terminal_title.show()
            self.terminal.show()

            self.extra_features_title.show()
            self.swap_headers_label.show()
            self.swap_headers_dropdown_1.show()
            self.swap_headers_dropdown_2.show()
            self.swap_headers_button.show()

    # Function to implement the "I'm Feelin Lucky" button. This is purely for fun, and makes a 
    # random graph of the 3D with color variety (chosen because that's the coolest looking one)
    def up_all_night(self):
        central_widget = self.findChild(QWidget, "central_widget")
        x_axis_dropdown = central_widget.findChild(QWidget, "axis_dropdown_X")
        y_axis_dropdown = central_widget.findChild(QWidget, "axis_dropdown_Y")
        z_axis_dropdown = central_widget.findChild(QWidget, "axis_dropdown_Z")
        x_axis_dropdown.setCurrentIndex(random.randint(0, x_axis_dropdown.count()-1))
        y_axis_dropdown.setCurrentIndex(random.randint(0, y_axis_dropdown.count()-1))
        z_axis_dropdown.setCurrentIndex(random.randint(0, z_axis_dropdown.count()))
        self.use_z_axis_checkbox.setChecked(True)
        self.apply_z_as_color_checkbox.setChecked(True)
        self.generate_graph(False)

# Secondary window class explicitly for creating and holding popout windowed graphs. Becasue
# graphs cannot be passed directly without binding to the main canvas, a completely new canvas
# object is created and data graphed on with this window
class BreakoutWindow(QMainWindow):
    # Function which initializes all widgets of the breakout window
    def __init__(self):
        super().__init__()
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)

        # Canvas Section for Plots
        self.canvas = MplCanvas(width=5, height=4, dpi=200)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        main_layout.addWidget(self.toolbar) 
        main_layout.addWidget(self.canvas)
        
    # Main function of the window, which accepts the data from the calling window and plots it
    def fullscreen_graph(self, x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, plot_type, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable):
        self.canvas.figure.clear()
        figure = self.canvas.figure

        if plot_type == 0: self.make_plot_2D(figure, x_data, x_dataType, y_data, y_dataType, names, plot_title, remove_data_till_in_range, enable_grid, enforce_square, enable)
        elif plot_type == 1: self.make_plot_3D_color(figure, x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable)
        else: self.make_plot_3D(figure, x_data, x_dataType, y_data, y_dataType, z_data, z_dataType, names, plot_title, remove_data_till_in_range, enable_grid, enforce_square, enable)

        self.canvas.draw()

    # Function to call window as fullscreen popup
    def show_new_window(self):
        self.showMaximized()

    # Near-copy of make_plot_2D function in Dataframe, but which accepts only explicit data
    def make_plot_2D(self, figure, x_vals, x_dataType, y_vals, y_dataType, names, plot_title, remove_data_till_in_range, enable_grid, enforce_square, enable_lines):
        if remove_data_till_in_range:
            while True:
                x_vals[0] *= x_dataType.conv / x_dataType.precision
                y_vals[0] *= y_dataType.conv / y_dataType.precision
                if x_vals[0] < x_dataType.range_low or x_vals[0] > x_dataType.range_high or y_vals[0] < y_dataType.range_low or y_vals[0] > y_dataType.range_high:
                    x_vals.pop(0)
                    y_vals.pop(0)
                else:
                    break
        else:
            if x_dataType.range_low is not None:
                if (x_vals[0] < x_dataType.range_low or x_vals[0] > x_dataType.range_high) and x_dataType.start_pos is not None:
                    x_vals[0] = x_dataType.start_pos

            if y_dataType.range_low is not None:
                if (y_vals[0] < y_dataType.range_low or y_vals[0] > y_dataType.range_high) and y_dataType.start_pos is not None:
                    y_vals[0] = y_dataType.start_pos

        i = 1
        while i < len(y_vals):
            try:
                x_vals[i] *= x_dataType.conv / x_dataType.precision
                y_vals[i] *= y_dataType.conv / y_dataType.precision
                if x_dataType.range_low is not None:
                    if x_vals[i] < x_dataType.range_low or x_vals[i] > x_dataType.range_high:
                        x_vals[i] = x_vals[i-1]

                if y_dataType.range_low is not None:
                    if y_vals[i] < y_dataType.range_low or y_vals[i] > y_dataType.range_high:
                        y_vals[i] = y_vals[i-1]

                if x_dataType.max_step is not None:
                    if abs(x_vals[i] - x_vals[i-1]) > x_dataType.max_step:
                        x_vals[i] = x_vals[i-1]
                        
                if y_dataType.max_step is not None:
                    if abs(y_vals[i] - y_vals[i-1]) > y_dataType.max_step:
                        y_vals[i] = y_vals[i-1]

            except TypeError:
                print("type error")
                print(i)
            i += 1

        if x_dataType.unit == "unknown": 
            x_unit = ""
        else:
            x_unit = "(" + x_dataType.unit + ")"
        if y_dataType.unit == "unknown":
            y_unit = ""
        else:
            y_unit = "(" + y_dataType.unit + ")"

        plot = figure.add_subplot(111)

        if enable_lines:
            plot.plot(x_vals, y_vals, marker='o', label='label')
        else:
            plot.scatter(x_vals, y_vals, marker='o', label='label')

        plot.set_xlabel(names[0] + x_unit)
        plot.set_ylabel(names[1] + y_unit)
        plot.set_title(plot_title)
        plot.grid(enable_grid)

        if enforce_square:
            max_range = max(
                max(x_vals) - min(x_vals), 
                max(y_vals) - min(y_vals), 
            ) / 1.8

            center_x = (max(x_vals) + min(x_vals)) / 2.0
            center_y = (max(y_vals) + min(y_vals)) / 2.0

            plot.set_xlim(center_x - max_range, center_x + max_range)
            plot.set_ylim(center_y - max_range, center_y + max_range)
            plot.set_box_aspect(1)
        else: plot.set_box_aspect(None)
    
    # Near-copy of make_plot_3D_color function in Dataframe, but which accepts only explicit data
    def make_plot_3D_color(self, figure, x_vals, x_dataType, y_vals, y_dataType, color_vals, color_dataType, names, plot_title, remove_data_till_in_range, enable_grid, enforce_color_range, enforce_square, enable_lines):
        ranges = [
            [x_dataType.range_low, x_dataType.range_high],
            [y_dataType.range_low, y_dataType.range_high],
            [color_dataType.range_low, color_dataType.range_high],
        ]
        convs = [x_dataType.conv, y_dataType.conv, color_dataType.conv]
        precisions = [x_dataType.precision, y_dataType.precision, color_dataType.precision]
        max_steps = [x_dataType.max_step, y_dataType.max_step, color_dataType.max_step]
        starting_pos = [x_dataType.start_pos, y_dataType.start_pos, color_dataType.start_pos]

        if x_dataType.unit == "unknown": 
            x_unit = ""
        else:
            x_unit = "(" + x_dataType.unit + ")"
        if y_dataType.unit == "unknown":
            y_unit = ""
        else:
            y_unit = "(" + y_dataType.unit + ")"
        if color_dataType.unit == "unknown":
            color_unit = ""
        else:
            color_unit = "(" + color_dataType.unit + ")"

        labels = [names[0] + x_unit, names[1] + y_unit, names[2] + color_unit]

        if remove_data_till_in_range:
            while True:
                x_vals[0] *= convs[0] / precisions[0]
                y_vals[0] *= convs[1] / precisions[1]
                color_vals[0] *= convs[2] / precisions[2]
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1] or
                    y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1] or
                    color_vals[0] < ranges[2][0] or color_vals[0] > ranges[2][1]):
                    x_vals.pop(0)
                    y_vals.pop(0)
                    color_vals.pop(0)
                else:
                    break
        else:
            if ranges[0][0] is not None:
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1]) and starting_pos[0] is not None:
                    x_vals[0] = starting_pos[0]

            if ranges[1][0] is not None:
                if (y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1]) and starting_pos[1] is not None:
                    y_vals[0] = starting_pos[1]

            if ranges[2][0] is not None:
                if (color_vals[0] < ranges[2][0] or color_vals[0] > ranges[2][1]) and starting_pos[2] is not None:
                    color_vals[0] = starting_pos[2]

        i = 1
        while i < len(y_vals):
            try:
                x_vals[i] *= convs[0] / precisions[0]
                y_vals[i] *= convs[1] / precisions[1]
                color_vals[i] *= convs[2] / precisions[2]
                if ranges[0] is not None:
                    if x_vals[i] < ranges[0][0] or x_vals[i] > ranges[0][1]:
                        x_vals[i] = x_vals[i-1]

                if ranges[1] is not None:
                    if y_vals[i] < ranges[1][0] or y_vals[i] > ranges[1][1]:
                        y_vals[i] = y_vals[i-1]
                
                if ranges[2] is not None:
                    if color_vals[i] < ranges[2][0] or color_vals[i] > ranges[2][1]:
                        color_vals[i] = color_vals[i-1]

                if max_steps[0] is not None:
                    if abs(x_vals[i] - x_vals[i-1]) > max_steps[0]:
                        x_vals[i] = x_vals[i-1]
                        
                if max_steps[1] is not None:
                    if abs(y_vals[i] - y_vals[i-1]) > max_steps[1]:
                        y_vals[i] = y_vals[i-1]
                
                if max_steps[2] is not None:
                    if abs(color_vals[i] - color_vals[i-1]) > max_steps[2]:
                        color_vals[i] = color_vals[i-1]

            except TypeError:
                print("type error")
                print(i)
                x_vals.pop(i)
                y_vals.pop(i)
                color_vals.pop(i)
            i += 1

        plot = figure.add_subplot(111)

        # Plot the line connecting the points
        if enable_lines :plot.plot(x_vals, y_vals, color='black', label='Data Line', linewidth = 0.5)

        color_scale = 0
        color_scale_low = None
        color_scale_high = None

        if enforce_color_range:
            color_scale = (color_dataType.range_high - color_dataType.range_low) * 0.1 / 2
            color_scale_low = color_dataType.range_low - color_scale
            color_scale_high = color_dataType.range_high + color_scale

        # Add colored scatter points
        scatter = plot.scatter(x_vals, y_vals, c=color_vals, cmap='nipy_spectral', vmin = color_scale_low, vmax = color_scale_high, s=20)

        # Add color bar
        cbar = figure.colorbar(scatter, ax=plot)
        cbar.set_label(labels[2])

        # Set plot attributes
        plot.set_title(plot_title)
        plot.set_xlabel(labels[0])
        plot.set_ylabel(labels[1])

        # Enable grid if specified
        if enable_grid:
            plot.grid(True)

        if enable_lines:
            plot.plot(x_vals, y_vals, color='black', label='Data Line', linewidth = 0.5)

        # Enforce square aspect ratio if specified
        if enforce_square:
            max_range = max(
                max(x_vals) - min(x_vals), 
                max(y_vals) - min(y_vals), 
            ) / 1.8

            center_x = (max(x_vals) + min(x_vals)) / 2.0
            center_y = (max(y_vals) + min(y_vals)) / 2.0

            plot.set_xlim(center_x - max_range, center_x + max_range)
            plot.set_ylim(center_y - max_range, center_y + max_range)
            plot.set_box_aspect(1)
        else: plot.set_box_aspect(None)

    # Near-copy of make_plot_3D function in Dataframe, but which accepts only explicit data
    def make_plot_3D(self, figure, x_vals, x_dataType, y_vals, y_dataType, z_vals, z_dataType, names, plot_title, remove_data_till_in_range, enable_grid, enforce_cube, enable_lines):
        convs = [x_dataType.conv, y_dataType.conv, z_dataType.conv]
        ranges = [
            [x_dataType.range_low, x_dataType.range_high],
            [y_dataType.range_low, y_dataType.range_high],
            [z_dataType.range_low, z_dataType.range_high],
        ]
        precisions = [x_dataType.precision, y_dataType.precision, z_dataType.precision]
        max_steps = [x_dataType.max_step, y_dataType.max_step, z_dataType.max_step]
        start_pos = [x_dataType.start_pos, y_dataType.start_pos, z_dataType.start_pos]

        if x_dataType.unit == "unknown": 
            x_unit = ""
        else:
            x_unit = "(" + x_dataType.unit + ")"
        if y_dataType.unit == "unknown":
            y_unit = ""
        else:
            y_unit = "(" + y_dataType.unit + ")"
        if z_dataType.unit == "unknown":
            z_unit = ""
        else:
            z_unit = "(" + z_dataType.unit + ")"

        labels = [names[0] + x_unit, names[1] + y_unit, names[2] + z_unit]

        if remove_data_till_in_range:
            while True:
                x_vals[0] *= convs[0] / precisions[0]
                y_vals[0] *= convs[1] / precisions[1]
                z_vals[0] *= convs[2] / precisions[2]
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1] or
                    y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1] or
                    z_vals[0] < ranges[2][0] or z_vals[0] > ranges[2][1]):
                    x_vals.pop(0)
                    y_vals.pop(0)
                    z_vals.pop(0)
                else:
                    break
        else:
            if ranges[0][0] is not None:
                if (x_vals[0] < ranges[0][0] or x_vals[0] > ranges[0][1]) and start_pos[0] is not None:
                    x_vals[0] = start_pos[0]

            if ranges[1][0] is not None:
                if (y_vals[0] < ranges[1][0] or y_vals[0] > ranges[1][1]) and start_pos[1] is not None:
                    y_vals[0] = start_pos[1]

            if ranges[2][0] is not None:
                if (z_vals[0] < ranges[2][0] or z_vals[0] > ranges[2][1]) and start_pos[2] is not None:
                    z_vals[0] = start_pos[2]

        i = 0
        while i < len(y_vals):
            try:
                x_vals[i] *= convs[0] / precisions[0]
                y_vals[i] *= convs[1] / precisions[1]
                z_vals[i] *= convs[2] / precisions[2]
                if ranges[0] is not None:
                    if x_vals[i] < ranges[0][0] or x_vals[i] > ranges[0][1]:
                        x_vals[i] = x_vals[i-1]

                if ranges[1] is not None:
                    if y_vals[i] < ranges[1][0] or y_vals[i] > ranges[1][1]:
                        y_vals[i] = y_vals[i-1]
                
                if ranges[2] is not None:
                    if z_vals[i] < ranges[2][0] or z_vals[i] > ranges[2][1]:
                        z_vals[i] = z_vals[i-1]

                if max_steps[0] is not None:
                    if abs(x_vals[i] - x_vals[i-1]) > max_steps[0]:
                        x_vals[i] = x_vals[i-1]
                        
                if max_steps[1] is not None:
                    if abs(y_vals[i] - y_vals[i-1]) > max_steps[1]:
                        y_vals[i] = y_vals[i-1]
                
                if max_steps[2] is not None:
                    if abs(z_vals[i] - z_vals[i-1]) > max_steps[2]:
                        z_vals[i] = z_vals[i-1]

            except TypeError:
                print("type error")
                print(i)
                x_vals.pop(i)
                y_vals.pop(i)
                z_vals.pop(i)
                i -= 1

            i += 1

        plot = figure.add_subplot(111, projection='3d')

        # Set labels and title
        plot.set_title(plot_title)
        plot.set_xlabel(labels[0])
        plot.set_ylabel(labels[1])
        plot.set_zlabel(labels[2])

        # Scatter plot for the 3D data
        plot.scatter(x_vals, y_vals, z_vals, edgecolor='none', alpha=0.8)

        if enable_lines:    plot.plot(x_vals, y_vals, z_vals)

        # Enable grid if specified
        plot.grid(enable_grid)

        # Enforce cube aspect ratio if specified (not straightforward in 3D but can scale axes)
        if enforce_cube:
            max_range = max(
                max(x_vals) - min(x_vals), 
                max(y_vals) - min(y_vals), 
                max(z_vals) - min(z_vals)
            ) / 1.8

            center_x = (max(x_vals) + min(x_vals)) / 2.0
            center_y = (max(y_vals) + min(y_vals)) / 2.0
            center_z = (max(z_vals) + min(z_vals)) / 2.0

            plot.set_xlim(center_x - max_range, center_x + max_range)
            plot.set_ylim(center_y - max_range, center_y + max_range)
            plot.set_zlim(center_z - max_range, center_z + max_range)
            plot.set_box_aspect(1)
        else: plot.set_box_aspect(None)

# Breakout window class used to store presets with a passed name. Called by main window. Returns
# the entered name and wether or not the button was clicked, as exiting out of the window should
# result in not saving the graph
class SavePresetPopoutWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Preset")
        self.setGeometry(parent.x() + parent.width()//2 - 150, parent.y() + parent.height()//2 - 50, 300, 100)

        # Layout and widgets
        self.layout = QVBoxLayout()
        self.preset_name_label = QLabel("Enter Preset Name:")
        self.preset_name_input = QLineEdit()
        self.confirm_button = QPushButton("Save")

        # Add widgets to layout
        self.layout.addWidget(self.preset_name_label)
        self.layout.addWidget(self.preset_name_input)
        self.layout.addWidget(self.confirm_button)
        self.setLayout(self.layout)

        # Connect button signal
        self.confirm_button.clicked.connect(self.accept)

    def get_name(self):
        """Return the entered text when dialog is accepted."""
        return self.preset_name_input.text()
    
# Breakout window class used for removing presets from the PRESETS.CSV. Contains only a dropdown
# which is populated with the existing presets to be selected from
class RemovePresetPopoutWindow(QDialog):
    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remove Preset")
        self.setGeometry(parent.x() + parent.width()//2 - 150, parent.y() + parent.height()//2 - 50, 300, 100)

        # Layout and widgets
        self.layout = QVBoxLayout()
        self.preset_name_dropdown = QComboBox()
        self.preset_name_dropdown.addItems(names)
        self.preset_name_dropdown.setItemText(0, "Remove Preset Graph")
        self.confirm_button = QPushButton("Remove")

        # Add widgets to layout
        self.layout.addWidget(self.preset_name_dropdown)
        self.layout.addWidget(self.confirm_button)
        self.setLayout(self.layout)

        # Connect button signal
        self.confirm_button.clicked.connect(self.accept)

    def get_name(self):
        """Return the entered text when dialog is accepted."""
        return self.preset_name_dropdown.currentText()

# Main code for the app. Creates a new QApp, a new window to show, and starts the app
app = QApplication(sys.argv)
window = MizzouDataTool()
window.showMaximized()
app.exec()
