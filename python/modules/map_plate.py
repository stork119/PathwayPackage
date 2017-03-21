#! /usr/bin/python
import string, os, logging, csv
from collections import OrderedDict
import modules.file_managment as FM
import modules.csv_managment as CSV_M

logger = logging.getLogger("map plate")
logger.info("Executing map_plate module.")
fatal_error_msg = "Fatal error occured while trying to read mapplate."

def parse_mp(input_path, delimiter):
    """
    Main function of TASK_READ_MAP_PLATE. 
    Parse all map_plate informations (from csv files) into python dictionary.
    
    Arguments:
    - input_path [path to map_plate directory]
    - delimiter [delimiter used in map_plate files to separate their values]
    Returns:
    - map_plate structure (dictionary of ordered dictionaries),
        i.e.:
        map_plate = { 'A01' : OrderedDict([('id', 'A01'),
                                        ('exp_part', '1'),
                                        ('name', 'A01'),
                                        <...>]),
                     'B01' : OrderedDict([('id', 'B01'),
                                        ('exp_part', '2'),
                                        ('name', 'A01'),
                                        <...>]),
                    <...> },
        where:
        map_plate.keys()- experimental wells
        mp_plate[well_id]- dicionary of all experimental settings
                            for given well
    """
    mp_dict = {}
    dim =_parse_base_params(input_path, delimiter, mp_dict)
    _parse_params(input_path, delimiter, dim, mp_dict)
    return mp_dict

def _parse_params(input_path, delimiter, dimensions, mp_dict):
    """
    Parse information about experiment collected in csv files, i.e.:
    - cells type
    - stimulation time
    - <...>
    """
    param_paths =_get_param_paths(input_path)
    param_paths = sorted(param_paths, key = str)
    logger.debug("Map_plate params input paths: %s.", param_paths)
    for mp_file in param_paths:
        correctness = _verify_input_mp_file(mp_file, delimiter, dimensions)
        if correctness == False:
            logger.error(fatal_error_msg)
            exit()
        else:
            _collect_exp_settings(input_path, mp_file, delimiter, mp_dict)

def _parse_base_params(input_path, delimiter, mp_dict):
    """
    1. 'Base' params- params required in each map_plate:
        - args_active
        - args_ind
        - args_name
    2. 'Not base' params- other information (facultative and not pre-defined), 
        i.e. cell type
    """
    dimensions, active = _parse_active(input_path, delimiter)
    name_path, id_path = _verify_name_and_id(input_path, delimiter, dimensions)
    name = CSV_M.read_csv(name_path, delimiter)
    mp_id = CSV_M.read_csv(id_path, delimiter)
    for i, row in enumerate(active):
        for j, col in enumerate(active[i]):
            exp_part = active[i][j]
            if exp_part != "0":
                pos_x = str(i)
                pos_y = str(j)
                key = mp_id[i][j] #id_value
                name_value = name[i][j]
                mp_dict[key] = OrderedDict({"position_x" : pos_x, 
                                "position_y" : pos_y, 
                                "name" : name_value, 
                                "id" : key, 
                                "exp_part" : exp_part})
    return dimensions

def _parse_active(input_path, delimiter):
    active_path = FM.path_join(input_path, "args_active.csv")
    if not FM.path_check_existence(active_path):
        logger.error(fatal_error_msg + 
                     " Cannot parse map_plate active, "
                     "file doesn't exist: %s", active_path)
        exit()
    active = CSV_M.read_csv(active_path, delimiter)
    x = len(active)
    y = len(active[0])
    dimensions = [x,y]
    return dimensions, active

def _verify_name_and_id(input_path, delimiter, dimensions):
    # >>temporary change<<
    #id_path = FM.path_join(input_path, "args_ind.csv") 
    #name_path = FM.path_join(input_path, "args_names.csv")
    name_path = FM.path_join(input_path, "args_ind.csv")
    id_path = FM.path_join(input_path, "args_names.csv")
    # >>temporary change<<
    if not FM.path_check_existence(id_path):
        logger.info("Map_plate names would be used also as ids "
                    "due to original id file doesn't exist: %s", id_path)
        id_path = name_path
    else:
        if not _verify_input_mp_file(id_path, delimiter, dimensions):
            logger.error(fatal_error_msg)
            exit()
    if not FM.path_check_existence(name_path):
        logger.error(fatal_error_msg + 
                    " Cannot parse map_plate names, "
                    "file doesn't exist: %s", name_path)
        exit()
    if not _verify_input_mp_file(name_path, delimiter, dimensions):
        logger.error(fatal_error_msg)
        exit()
    return name_path, id_path

def _get_param_paths(input_path):
    subfile_list = FM.file_get_paths(input_path)
    param_paths = []
    all_paths = []
    for root, dires, files in os.walk(input_path):
        for name in files:
            all_paths.append(FM.path_join(root, name))
    for path in all_paths:
        if path not in subfile_list and path[-4:] == ".csv":
            param_paths.append(path)
    return param_paths

def _collect_exp_settings(abs_path, mp_file, delimiter, mp_dict):
    """
    Extracts information about optional experiment's parameter,
    i.e. stimulation.1.1.
    Returns:
    - Additional parameter to map_plate dictionary structure, i.e:
        mp_dict['A01']['cells.1.1'] = 'A549'
    """
    rel_path = FM.path_get_relative(abs_path, mp_file)
    fullname = ".".join(FM._path_split(rel_path))
    # Extracting proper column name from rel_path 
    # i.e. compare.1.1 from compare/1.1.csv
    extension_length = len(FM.file_get_extension(fullname)) 
    name = fullname[:-extension_length]
    data = CSV_M.read_csv(mp_file, delimiter)
    for well in mp_dict:
        pos_x = int(mp_dict[well]["position_x"])
        pos_y = int(mp_dict[well]["position_y"])
        value = (data[pos_x][pos_y])
        mp_dict[well][name] = value

def get_param_value(mp_dict, well_name, param):
    """
    Function getting values for a given well and parameter.
    """
    value = mp_dict[well_name][param]
    return value

def get_param_values(mp_dict, param):
    """
    Function gettin all values for a given param 
    from map_plate dictionary.
    """
    values = []
    for well in mp_dict:
        values.append(mp_dict[well][param])
    return values

def get_param_unique_values(mp_dict, param): 
    """
    Function gettin all unique values for a given param 
    from map_plate dictionary.
    """
    values = get_param_values(mp_dict, param)
    unique = list(set(values))
    return unique

def get_params_names(mp_dict): # get all key names from map_plate dictionary
    names = []
    key_0 = list(mp_dict.keys())[0]
    names = list(mp_dict[key_0].keys()) 
    """
    Uncommented option (above):
        if we assume that number of information between wells is constant
    Commented option (below): 
        if we assume that number of information about wells may somehow differ
    """
    """params_count = len(mp_dict[key_0])
    for well in mp_dict: 
        tmp= len(mp_dict[well])
        if params_count != tmp:
            logger.warning("Some wells are not described by " 
                    "the same number of information: %s, %s", key_0, well)
            if tmp > params_count:
                names = []
                params_count = tmp
                for param in mp_dict[well]:
                    names.append(param)"""
    return names

def get_well_params(mp_dict, well):
    """ 
    Gives all parameters values for a given well
    """
    values = []
    for param in mp_dict[well]:
        values.append(mp_dict[well][param])
    return values

def _verify_input_mp_file(input_file, delimiter, dimensions = 0):
    if not FM.file_verify_extension(input_file, ".csv"):
        logger.error("Wrong input format: %s", input_file)
        return False
    if dimensions != 0:
        data = CSV_M.read_csv(input_file, delimiter)
        x = len(data)
        y = len(data[0])
        if dimensions != [x,y]:
            logger.error("Wrong input file "
                        "(improper csv dimensions): %s.", input_file)
            return False
    return True

def _prepare_mp_output(input_data, mp_dict, mp_key):
    """
    Arguemnts:
    - input_data - data from input csv file
    - mp_dict- map_plate structure containing all information about experiment
    - mp_key - well id/key to all well parameters in map_plate structure
    """
    output_data = []
    column_names = input_data[0]
    new_line = column_names + get_params_names(mp_dict)
    output_data.append(new_line)
    for i in range(1, len(input_data)):
        new_line = input_data[i] + get_well_params(mp_dict, mp_key)
        output_data.append(new_line)
    return output_data

def apply_mp(input_path, output_path, delimiter, mp_dict, 
            csv_names, mp_key):
    """
    Main function of TASK_APPLY_MAP_PLATE. 
    Writes all map_plate information (from mp_dictionary) 
    into given csv files.
    Arguments:
    - input_path- path to dir collecting input files
    - output_path- path to output files
    - delimiter- separator used in csv files
    - mp_dict- map_plate structure containing all information about experiment
    - csv_names- list of filenames to apply map_plate
    - mp_key - well id/key to all well parameters in map_plate structure
    """
    input_paths_list = FM.filenames_make_paths_list(input_path, csv_names)
    logger.debug("Apply map_plate: CSV input files list: "
                "%s.",input_paths_list)
    output_paths_list = FM.filenames_make_paths_list(output_path, csv_names)
    logger.debug("Apply map_plate: CSV output files list: "
                "%s.", output_paths_list)
    for in_path, out_path in zip(input_paths_list, output_paths_list):
        if FM.path_check_existence(in_path):
            input_csv = CSV_M.read_csv(in_path, delimiter)
            output = _prepare_mp_output(input_csv, mp_dict, mp_key)
            CSV_M.write_csv(out_path, delimiter, output)
        else:
            logger.warning("Apply map_plate: following input csv file "
                        "doesn't exist: %s", in_path)

