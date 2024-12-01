# MR Data Visualization Tool

## Overview

Welcome to the Mizzou Racing Data Visualization Tool, also known as the MR Data Tool!
This application is a data visualization tool built for Mizzou Racing by members of Mizzou Racing.
While the functionality of this tool is direted at our data collection system (based around ESP32 
microcontrollers using both CAN bus and LoRa communication as well as data logging to an SD card),
we hope that everyone who wants to will be able to use this tool to improve their data analysis and
visualization. While we want this tool to be used, we the developers humbly ask that all direct
uses retain the "Mizzou Data Tool" tag at the top of the page, and that all forks give due credit
in their ReadMe and somewhere visible on the application. Enjoy!

## Features

- Load in CSV data and create a unified data structure from multi-frequency sources
- Make interactive graphs in 2 or 3 dimensions with an additional option to graph in 2D with color
- Save the unified data structure into a well defined format for faster future read times
- Have a toggleable "Zen Mode", which hides all non-essential features for maximum useability
- Alter the conversion rates, units, precisions, ranges, and more of the data to allow
maximum customizability with the format of the data coming in from the CSV
- Have manty options for graphing to create both useful and visually appealing graphs
- Create "popout" windows for graphs to allow comparison of many graphs side-by-side
- Allow saving and loading of preset graphing setups
- Allow saving and loading of graphs themselves with all their options and data

## Useage Guide
### Installation
It is first recommended to have an updated version of git, python3, PyQt6, matplotlib, and pickle
Instruction for these can be found plentifully elsewhere.
1. Open the github page: https://github.com/CalebH1208/MR_Data_Visualization_Tool
2. Read this ReadMe to ensure you understand the applications and limitations of this tool
3. Run the following command in the directory of your choice to clone the repository 
(this will clone it as a new folder, so be careful not to unnecessarily nest repos)
```
git clone https://github.com/CalebH1208/MR_Data_Visualization_Tool
```
4. Once the repo has finished cloning, attempt to run the executable. If this does not work,
attempt to run the python code with the below command:
```
cd dev
python3 data_viewer.py
```
5. If the python works but the executable does not, see the instructions for creating a new
executable below

### File Structure
This repo is split into two main sectiond, /dev and /dist. Both contain identical copies of the 
example data set as well as a CONFIG.CSV and PRESETS.CSV file, which are used for default
configuration and saving preset graphs. The /dev folder is intended for new python development and 
modifications, while the /dist folder is intended for use by those less code inclined and who just
want to be able to run an executable and graph their data in peace. It is required that a 
CONFIG.CSV and PRESETS.CSV file remain with the file being executed/run, but this is the only 
filesystem dependancy. In normal operation of the application, the user will open a folder 
containing the csv files with the data they want to access. This folder should ideally not contain
other non-data files. Note that when saving data the application will create a MONOLITH.CSV file. 
This should not be modified directly, and is intended to be interacted with purely through the app.

**VERY IMPORTANT!: FOR LOADING FROM A DIRECTORY, THE FOLDER MUST CONTAIN 3 DATA FILES NAMED
"1HZLOG.CSV", "10HZLOG.CSV", and "100HZLOG.CSV". EACH OF THESE FILES MUST BE IN CSV FORMAT WITH A 
SINGLE HEADER LINE CONSISTING OF DATA NAMES. EACH OF THESE FILES MUST HAVE A COLUMN NAMED "Time" AS
THIS WILL BE USED TO COMPILE THE DATA TOGETHER.**

If only one CSV is desired, use the "Browse File" option.

### Simplest Usage Case
1. Open the app
2. Select a folder containing the data csv files as specified and click "Generate Data Frame"
3. Note that until a dataframe is generated, options are disabled
4. Note that the app opens by default into "Zen Mode", which hides non-essential data, but also
hides the terminal, which will inform the user of error states occuring.
5. Select from the dropdown menus for the axis you wish to graph
6. Click the "Generate Graph" button to display the graph on the embedded canvas.

### Description of Functionality (Zen Mode Only)
- Browse Folder:
    
    Opens a file explorer which can be used to select the folder containing the data. Please see above
    for requirements of this folder and the data format itself.

- Browse File:
    
    Opens a file explorer which can be used to select the file containing the data. This must be in
    "standard" CSV format.

- Generate Data Frame:

    This button is used to process the data from the given folder. During this process the app will
    freeze and inputs will not register. We have experienced <1 Second per 100k lines of delay on
    this load operation, but this can still build up to a substantial wait time for very large data.

- Save Data Frame:

    This button is used to save the current state of the data into a MONOLITH.CSV file. This file will
    then be searched for and read in by default the next time the data is loaded. This button changes
    to green when there are unsaved changes.

- Dropdown Menus:

    The three menus available allow the user to select the axis they wish to plot, with X being the
    horizontal axis, Y being the vertical, and Z being a tertiary or color-based axis.

- Use Z Axis:

    This checkbox can be used to enable the third axis for 3D plots or 2D plots with color as the
    third dimension.

- Apply Z-Axis as Color:

    This checkbox cna be used to create a 2D plot with color as the third dimension. The "Use Z Axis"
    box must also be enabled for this to function.

- Toggle Zen Mode:

    This button toggles the "Zen Mode", which by default hides all non-essential functions. This is
    intended to increase useability and visuals for the app. Note that when in zen mode the terminal
    is hidden from view, and thus error messages can be missed.

- Generate Graph:

    The standard graph creating button. This will open a graph into the embedded canvas.

- **Interacting with a graph**

    The graphs are created with Matplotlib, and are interactive. The four-arrows symbol can be used to
    translate a graph, and the magnifying glass figure can be used to scale in or out on a graph. The
    floppy disc symbol can be used to save an image of graph, but this image is not then interactive.
    If the entire graph is not showing, press the sliding button icon and click "Tight Layout".
    To modify scaling, axis names, or title of the graph, use the stonks icon.

### Description of Functionality (Advanced Mode)

- Conversion Rate

    This field is used to create a conversion rate from the data being logged to the displayed data.
    This rate should only be used for unit conversions and will be applied as a multiplicative factor.

- Unit

    This field is a purely asthetic field, which defaults to "unknown", and can be used to add units to
    the axis of graphs. Use of this field is highly recommended as it allows future users to know what
    units were intended, instead of needing to guess based on context.

- Precision

    This field is similar to the conversion rate field, but is instead applied as a divisor. It is
    strongly recommended to only use multiples of 10 in this field, and is used to convert for decimal
    points of precision, as is used often in the Mizzou Racing data logging files, because floats are
    difficult to work with.

- Range

    These two fields can be used to provide a boundary for the data being graphed. The underlying data
    will not be modified, but will be bounded by the ranges provided for graphing. The default bounds
    for data are +- the unsigned 64-bit int max, or 18446744073709551615. Any modification of this
    outside the bounds of +-17e18 will not be saved. Leaving this field blank wil be interpreted as the
    default values.

- Max Step

    This field can be used to apply a crude low-pass filter to data values by squashing any changes
    outside the bounds of max_step in a single data step. This field is not recommended for new users.

- Start Position

    This field is used to apply a default starting position to data. This field is not recommended to
    be modified.

- Save Settings

    This button is used to save any changes made to the data settings fields, and update only the
    stored data with the new values. This must be used to have the new values take effect. This will
    NOT store the values to the MONOLITH.CSV file until the "Save Data Frame" button is used. This
    button changes to green when there are unsaved fields.

- Enable Grid Lines

    This checkbox can be used to enable or disable teh default grid lines on the graphs. This will
    apply for embedded, saved, and popout graphs. Checked by default.

- Enforce Square Graph

    This checkbox can be used to force the X and Y axis (and Z if using 3D) to take on the same scaling
    and physical size on the screen. This is most useful for data where the X and Y axes are in
    relation to each other (such as longitude vs lattitude or GvG Graphs). Unchecked by default.

- Remove Data Till in Range

    This checkbox can be used to hide all datapoints from the beginning of the file till these points
    are in the specified valid range in both X and Y axes. This is most useful for removing invalid
    start-up data such as that GPS data obtained before GPS-lock is acheived. If this is left
    unchecked, then the out of range data will default to the range boundary. Checked by default.

- Use Custom Plot Title

    This checkbox and field combo can be used to apply a custom title to a graph when it generates.
    If the check box is not checked, then the title will default to "{Z} vs. {Y} vs. {X}", and include
    units if they are available. All labels can be overriden in plot, see "Interacting with a graph"
    above. Unchecked by default.

- Enforce Color Range

    This checkbox will enforce that the max and min values for the color axis on the 2D plots with
    color are set to the max and min range values for that axis. This is helpful for standardizing the
    color scaling when comparing graphs, as it is difficult to get a quantitative comparison otherwise.
    If desired, the scaling can be fine tuned from the stonks icon menu on the interactive graph.
    Unchecked by default.

- Load preset Graph

    The PRESETS.CSV file will store created preset graphs, which can then be loaded using this dropdown
    menu. The presets here will then be populated into the axis dropdowns for X, Y, and Z, and the Z
    axis checkboxes will be updated. Note that the other optional checkboxes are not stored with
    presets. See below for creating new presets.

- Extra Graphing Options

    The extra graphing options dropdown provides a wealth of added and useful features for creating and
    storing graphs in different ways. Each of these options has a section below to describe its use.
    To select any of these, simply click the dropdown menu then click the desired function.

- Create Pop Out Graph

    This function can be used to grate a completely new graphing window which has only the interactive
    graph as was set up in the main window. There can be an unlimited number of these pop out graphs
    and none of them will affect the others. Closing the main window will not close these graphs, but
    ending the program entirely will. 

- Save Graph / Open Saved Graph

    This function can be used to created a saved graph object. The contents of this are stored using
    pickle, a python object serialization tool. These objects are stored as .MRGO files (Mizzou Racing
    Graph Objects), and can be loaded back in with the "Open Saved Graph" feature. Note that graphs are
    stored with their data and header info, so these graphs do not need their original data to be also
    loaded, and cannot be modified and saved again once loaded up.

- Clear Graph

    This function clears the embedded canvas of all graphs, but does not affect any popout windows.

- Save Preset Graph

    This function can be used to save the current graph axes and type to the PRESETS.CSV file, which
    can then be pulled up for any loaded data using the Load Preset Graph dropdown. Note that the
    other graph options (Enable Grid, Enfore Square, etc.) are not stored as part of the preset. When
    this selection is used, a popout window will appear prompting a name for the preset. The "Save"
    button must then be used to confirm the save.

- Delete Preset Graph

    This function can be used to remove a preset graph from the list. This will open a popout window
    from which the desired preset can be selected for removal. The "Remove" button must be used to
    confirm the removal.

- Terminal

    The terminal is a write only text box providing diagnostic and error information to the user.

- Extra Features

    This section is reserved for the least-used functionality, and may be heaily modified in updates

- Swap Data

    This function can be used to swap the names assigned to data in the event that the original CSV was
    incorrect. These changes are only persistent to the instance of the program, and will not be saved.
    This function may be removed in future updates, as it is equivalent to simply changing the axis
    names using the matplotlib interactive graphing options (see above). This feature is not
    recommended for the casual user.

### Developer's Guide

This code is implmented using mainly python3, PyQt6, and matplotlib. There are abundant resources
online for learning how to use these. The executable file was created using pyinstaller. If changes
are made to the /dev/data_viewer.py, an undated .exe can be made with:
```
pyinstaller --onefile --icon=../dist/mrlogo.ico -w 'data_viewer.py'
```

### Contributing

All are welcome to contribute to this project. If you would like to make updates please make a branch
to work on and create a pull request if you want your code merged into main. Alternatively, if you want
to make and maintain your own changes, all are welcome to fork this repo, but as stated previously, we
humbly request that you maintain some visible credit to our original project, in addition to the 
license as specified below.

### License and Copyright

This project is licensed under the MIT License - see the LICENSE file for details.
