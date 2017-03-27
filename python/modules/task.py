#! /usr/bin/python
from collections import OrderedDict
import modules.file_managment as FM
import modules.flow_control as FC
import modules.cellprofiler as cpm
import modules.csv_managment as CSV_M
import modules.map_plate as map_plate
import modules.r_connection as R_connection
import modules.ffc as ffc
from time import sleep
import multiprocessing 
import logging
import os

logger = logging.getLogger("Task module")

class TASK():

    dict_task = {}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args = {}):
        self.parameters_by_value = parameters_by_value
        self.parameters_by_name = parameters_by_name
        self.updates_by_value = updates_by_value
        self.updates_by_name = updates_by_name
        #self.logger = logging.getLogger(self.__class__.__name__) - doesn't work with parallelize

    def execute(self, dict_global):
        dict_local = dict_global.copy()
        logger.debug("dict_local before update: %s", dict_local.keys())
        dict_local = self.update_dict(dict_local, dict_local, self.parameters_by_value, self.parameters_by_name) #check out if its working 
        logger.debug("dict_local after update: %s", dict_local.keys())
        logger.info("Executing: %s", self.__class__.__name__) #information what task is being executed
        dict_setts = self.parse_task_arguments(dict_local)
        self.execute_specify(dict_local, dict_setts)
        logger.debug("dict_local after execute_specify: %s", dict_local.keys()) #dunno if its needed
        logger.debug("dict_global before update: %s", dict_global.keys())
        dict_global = self.update_dict(dict_global, dict_local, self.updates_by_value, self.updates_by_name)
        logger.debug("dict_global after update: %s", dict_global.keys())
        return dict_global

    def parse_task_arguments(self, dict_local):
        dict_setts = {}
        for key in self.dict_task:
            try: 
                value = dict_local[key]
            except:
                try:
                    value = self.dict_task[key]["default"]
                except:
                    if self.dict_task[key]["required"]:
                        logger.error("Required parameter %s is missing for %s.", key, str(self.__class__.__name__))
                        exit()
            dict_setts[key] = value
        return dict_setts

    def update_dict(self, dict_out, dict_in, list_by_value, list_by_name):
        for k, v in list_by_value.items(): #update by value
            dict_out[k] = v
            logger.debug("Dict_out new key (updated by value): %s", k)
        for k, v in list_by_name.items(): #update by name
            logger.debug("Dict_in (by names) key, value: %s, %s", k, v)
            try:
                value = dict_in[v]
            except:
                logger.error("Dictionary update_by_name error. Given key (%s) doesn't exist in dictionary", v)
            dict_out[k] = value
            logger.debug("Dict_out new key, value (updated by name): %s, %s", k, v)
        logger.debug("Dict_out before concatenation: %s", dict_out.keys())
        try:
            dict_out = self.concatenation_name_nr(dict_out)
        except:
            logger.error("Dictionary concatenation error. Dictionary: %s concatenation failed.", dict_out.keys())
        logger.debug("Dict_out after concatenation: %s", dict_out.keys())        
        return dict_out

    def concatenation_name_nr(self, dict_out):      
        #concatenation name.number
        key_list = []
        for k, v in dict_out.items():
            if "." in k:
                key = k.split(".")
                key_list.append(key[0])
        logger.debug("List of names to concatenate: %s", key_list)
        if len(key_list) > 1:
            temp_dict = dict_out.copy()
            temp_dict2 = OrderedDict(sorted(dict_out.items()))
            key_list = list(set(key_list))      
            for i in range(len(key_list)):
                value = []
                for k, v in temp_dict2.items():
                    if key_list[i] + "." in k:
                        value.append(str(v))
                        del temp_dict[k] # deleting name.number from temporary dictionary
                value = "".join(value)
                temp_dict[key_list[i]] = value
            dict_out = temp_dict.copy()
        return dict_out

class TASK_FOR(TASK):

    dict_task = {}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.variables_list = args['variables_list']
        self.task_do = args['task_do']
        
    def execute_specify(self, dict_local, dict_setts):
        for variable in self.variables_list:
            dict_local_for = self.update_dict(dict_local, dict_local, variable['parameters_by_value'], variable['parameters_by_name'])
            self.task_do.execute(dict_local_for)

class TASK_QUEUE(TASK):
 
    dict_task = {}
 
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.task_list = args['task_list']

    def execute_specify(self, dict_local, dict_setts):
        for task in self.task_list:
            dict_local = task.execute(dict_local)

class TASK_IF(TASK):
    """
    Required args:
    - argument_1 [first argument to compare (from local_dict)]
    - comparison [type of comparison i.e. "equal" or "<"]

    Optional args
    - <arg2>, which can be parsed as:
        1) - argument_2 [second argument to compare (from local_dict)]
        2) <value from map_plate> which requires:
            - mp_dict [map_plate disctionary name (default: map_plate)]
            - mp_well [well id, i.e. 'A01']
            - mp_param [param name i.e. 'exp_part']
    """
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.task_list = args['task_list']

    def execute_specify(self, dict_local):
        arg1 = dict_local["argument_1"] #[!] code need to be change to allow parsing both args from mp_dict
        comparison = dict_local["comparison"].lower() 
        try:
            arg2 = dict_local["argument_2"]
            if FC.compare_args(arg1, arg2, comparison) == True:
                self._execute_queue(dict_local)
            return
        except:
            pass
        try:
            mp_name = dict_local["mp_dict"]
        except:
            mp_name = "map_plate"
        try:
            mp_dict = dict_local[mp_name]
            mp_well = dict_local["mp_well"]
            mp_param = dict_local["mp_param"]
            arg2 = mp_dict[mp_well][mp_param]
        except:
            logger.error("Cannot get value from map_plate for given " 
            "dictionary, well and parameter: %s, %s, %s", mp_name, mp_well, mp_param)
            return
        if FC.compare_args(arg1, arg2, comparison) == True:
            self._execute_queue(dict_local)
        return

    def _execute_queue(self, dict_local):
        for task in self.task_list:
            task.execute(dict_local)

class TASK_CHECK_COMPLETNESS(TASK): # [!] not supported

    dict_task = {"experiment_finished" : {"required" : True, "default" : True},
                 "input_path" : {"required" : True}, 
                 "required_files" : {"requred" : False},
                 "sleep_time" : {"requred" : True}}
    # [!] class requires changes after merge with branch map_plate

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        in_path = dict_setts["input_path"]
        try:
            job_done = str(dict_setts["experiment_finished"])
            job_done = job_done.lower()
            if job_done == "no" or job_done ==  "0" or job_done == "false" or job_done == False:
                required_files = (dict_setts["required_files"]).split(",")
                sleep_time = int(dict_setts["sleep_time"])
                FM.dir_check_completeness(in_path, required_files, sleep_time)
        except:
            pass

class TASK_DOWNLOAD(TASK):

    dict_task = {"input_path" : {"required" : True}, 
                 "output_path" : {"requred" : True}}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        logger.info("TASK_DOWNLOAD from input: %s to output :%s", dict_setts["input_path"], dict_setts["output_path"]) 
        FM.dir_copy(dict_setts["input_path"], dict_setts["output_path"])


class TASK_REMOVE(TASK):

    dict_task = {"input_path" : {"required" : True}}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        FM.dir_remove(dict_setts["input_path"])

   
class TASK_QUANTIFY(TASK):

    dict_task = {"cp_path" : {"required" : True},
                 "input_path" : {"required" : True},
                 "output_path" : {"required" : True},
                 "pipeline" : {"required" : True}}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        cpm.run_cp_by_cmd(dict_setts["cp_path"], dict_setts["input_path"], 
                          dict_setts["output_path"], dict_setts["pipeline"])
   
class TASK_MERGE_SUBDIR_CSV(TASK):
 
    dict_task = {"input_path" : {"required" : True},
                 "output_path" : {"required" : True},
                 "csv_names_list" : {"required" : True},
                 "delimiter" : {"required" : True, "default" : ","},
                 "column_name" : {"required" : True, "default" : "well.name"}}
 
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        csv_names = (dict_setts["csv_names_list"]).split(",")
        main_subdir_list = FM.dir_get_paths(dict_setts["input_path"])
        for csv_name in csv_names:
            subdir_list = CSV_M.filter_subdir_list(main_subdir_list, csv_name) #filtering directiories containing given csv file
            data = CSV_M.merge_subdir_csv(csv_name, subdir_list, dict_setts["delimiter"], dict_setts["column_name"])
            extension = FM.file_get_extension(csv_name)
            len_ext = len(extension)
            name = csv_name[:-(len_ext)]
            dict_local[name] = data
            #Saving data
            out_path = FM.path_join(dict_setts["output_path"], csv_name)
            if FM.path_check_existence(out_path):
                logger.warning("File %s already exists. Removing old data.", out_path)
                FM.dir_remove(out_path)
            CSV_M.write_csv(out_path, dict_setts["delimiter"], data) #if we would like to write_csv somewhere...


class TASK_PARALLELIZE(TASK):

    dict_task = {"input_path" : {"required" : True},
                 "number_of_cores" : {"required" : True, "default" : "1"}, 
                 "sleep_time" : {"required" : True}}
    # [!] number_of_cores is temporary coded as string
    # [!] class requires changes after merge with branch map_plate

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.task_list = args['task_list']
        self.config_dict = args['config_dict']

    def execute_specify(self, dict_local, dict_setts):
        elements_list, ele_number = self.parse_elements_list(dict_local, dict_setts)
        processes_number = int(dict_setts["number_of_cores"])
        sleep_time = int(dict_setts["sleep_time"])
        new_elements = elements_list
        pool = multiprocessing.Pool(processes_number)
        while True:
            if len(new_elements) > 0:
                args = ((dict_local, element) for element in new_elements) #or just pass task, because we're able to get task_list and settings_dict from init if both functions will stay here
                pool.map_async(self._execute_queue, args)
            if len(elements_list) >= ele_number:
                break
            sleep(sleep_time)
            new_elements_list = self.parse_elements_list(dict_local, dict_setts)[0] # in MP case (ONLY) we could just call _create_ele_lis; TO DO
            new_elements = [i for i in new_elements_list if i not in elements_list]
            elements_list = new_elements_list
        pool.close()
        pool.join()

    def _execute_queue(self, args):
        dict_local, elements = args
        dict_local.update(elements)
        for task in self.task_list:
            task.execute(dict_local)

class TASK_PARALLELIZE_MP(TASK_PARALLELIZE): #all objects (folders) for given map_plate setup
    """
    Required args:
    - input_path [path to directories on which parallelize taks would be performed]
    [+ arguments for super class TASK_PARALLELIZE: number_of_cores, sleep_time]

    Optional args:
    - used_value [value defying if given dir name reflects well tag or id, by default 'tag']
    - prefix [subdir name prefixes]
                (i.e. 'Well ' for 'Well A0', where 'A01' is well tag)
    - sufix [subdir name sufixes]
    - exp_part [experiment part, by default '1']
    - mp_name [name of structure with all collected map_plate info, 
                by default 'map_plate']
    """
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK_PARALLELIZE.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.config_dict = args['config_dict']

    def parse_elements_list(self, dict_local): #implementing with tag
        input_path = str(dict_local["input_path"])
        try:
            used_value = dict_local["used_value"]
        except:
            used_value = "tag" 
        try:
            prefix = dict_local["prefix"]
        except:
            prefix = ""
        try:
            sufix = dict_local["sufix"]
        except:
            sufix = ""
        try:
            exp_part = dict_local["exp_part"]
        except:
            exp_part = "1"
        try:
            mp_name = dict_local["mp_name"]
        except:
            mp_name = "map_plate"
        mp_dict = dict_local[mp_name]
        active_wells_keys = FC.get_active_wells(mp_dict, exp_part) #get active wells keys for mp_dict 
        ele_number = len(active_wells_keys)
        params = FC.get_wells_base_params(mp_dict, active_wells_keys, prefix, sufix, exp_part)
        elements_list = FC.create_elements_list(input_path, params, used_value)
        return elements_list, ele_number

class TASK_PARALLELIZE_LIST(TASK_PARALLELIZE): # list of objects (folders) # [!] NOT SUPPORTED

    dict_task = {"input_path" : {"required" : True},
                 "number_of_cores" : {"required" : True, "default" : "1"}, 
                 "sleep_time" : {"required" : True},
                 "folders_list" : {"required" : True}}
    # [!] number_of_cores is temporary coded as string
    # [!] class requires changes after merge with branch map_plate

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK_PARALLELIZE.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def parse_elements_list(self, dict_local, dict_setts):
        paths = []
        input_path = str(dict_setts["input_path"])
        folder_list = (dict_setts["folders_list"]).split(",")
        for folder in folder_list:
            path = FM.path_join(input_path, folder)
            paths.append(path)
        folders_number = len(paths)
        return paths, folders_number


class TASK_PARALLELIZE_PATH(TASK_PARALLELIZE): #all objects (folders) in given directory (path)

    dict_task = {"input_path" : {"required" : True},
                 "number_of_cores" : {"required" : True, "default" : "1"}, 
                 "sleep_time" : {"required" : True},
                 "folders_number" : {"required" : True}}
    # [!] number_of_cores is temporary coded as string
    # [!] class requires changes after merge with branch map_plate
    
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK_PARALLELIZE.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.config_dict = args['config_dict']

    def parse_elements_list(self, dict_local, dict_setts):
        folders_number = int(dict_setts["folders_number"])
        input_path = str(dict_setts["input_path"])
        dir_list = FM.dir_get_names(input_path)
        return dir_list, folders_number

class TASK_READ_MAP_PLATE(TASK):
    """
    Required args:
    - input_path [path to map_plate csv files]

    Optional args:
    - delimiter [delimiter used in map_plate csv, by default ',']
    - mp_name [name for map_plate output 
            (variable assigned to dictionary containing all experiment settings), 
            by default 'map_plate']
    """
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        input_path = dict_local["input_path"]
        try:
            delimiter = dict_local["delimiter"]
        except:
            delimiter = ","
        try:
            mp_name = dict_local["mp_name"]
        except:
            mp_name = "map_plate"
        dict_local[mp_name] = map_plate.parse_mp(input_path, delimiter)

class TASK_APPLY_MAP_PLATE(TASK):
    """
    Required args:
    - input_path [path to input csv files]
    - output_path [path to output files]
    - csv_names_list [list of files to apply map_plate]
    - mp_key [well id/key to all well parameters in map_plate structure]
    
    Optional args:
    - delimiter [delimiter used in csv files, by default ',']
    - mp_name [name of dicitonary with all collected map_plate info, 
                by default 'map_plate']
    """
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        input_path = dict_local["input_path"]
        output_path = dict_local["output_path"]
        csv_names = (dict_local["csv_names_list"]).split(",")
        mp_key = dict_local["mp_key"]
        try:
            delimiter = dict_local["delimiter"]
        except:
            delimiter = ","
        try:
            mp_name = dict_local["mp_name"]
        except:
            mp_name = "map_plate"
        mp_dict = dict_local[mp_name]
        map_plate.apply_mp(input_path, output_path, delimiter, mp_dict, csv_names, mp_key)

class TASK_MAP_PLATE(TASK):

    dict_task = {"input_path_csv" : {"required" : True},
                 "input_path_metadata" : {"required" : True}, 
                 "output_path" : {"required" : True},
                 "csv_names_list" : {"required" : True},
                 "exp_id" : {"required" : True, "default" : "1"},
                 "delimiter_csv" : {"required" : True, "default" : ","},
                 "delimiter_mp" : {"required" : True, "default" : "\t"},
                 "exp_part" : {"required" : True, "default" : "1"},
                 "exp_parts" : {"required" : True, "default" : "1"}}
    # [!] class will be removed after merge with branch map_plate

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        input_path_csv = dict_local["input_path_csv"]
        input_path_metadata = dict_local["input_path_metadata"]
        output_path = dict_local["output_path"]
        csv_names = (dict_local["csv_names_list"]).split(",")
        try:
            exp_id = dict_local["exp_id"]
        except:
            exp_id = 1
        try:
            delimiter_csv = dict_local["delimiter_csv"]
        except:
            delimiter_csv = ","
        try:
            delimiter_mp = dict_local["delimiter_mp"]
        except:
            delimiter_mp = "\t"
        try:
            exp_part_id = dict_local["exp_part"]
            exp_parts = dict_local["exp_parts"]
        except:
            exp_part_id = "1" 
            exp_parts = "1"
        map_plate.combine(input_path_csv, input_path_metadata, output_path, csv_names, exp_id, exp_part_id, exp_parts, delimiter_mp, delimiter_csv)

class TASK_R(TASK):

    dict_task = {"r_function_name" : {"required" : True},
                 "r_script_path" : {"required" : True}}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        external_params = ["r_function_name", "r_script_path"]
        logger.info("Executing R function %s from %s", dict_setts["r_function_name"], dict_setts["r_script_path"]) 
        # PLACEHOLDER for adding more external params
        param_dict = R_connection.prepare_param_dict(dict_local, self.parameters_by_value, self.parameters_by_name, external_params)
        output_dict = R_connection.execute_r_script(param_dict, dict_setts["r_script_path"], dict_setts["r_function_name"])
        dict_local.update(output_dict)
        
class TASK_FFC_CREATE(TASK):

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        # Check if user set input an output paths
        output_dict = ffc.create_camcor(dict_local, self.parameters_by_value, self.parameters_by_name)
        dict_local.update(output_dict)

class TASK_FFC_READ(TASK):

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        # Check if user set input an output paths
        try:
            output_dict = ffc.read_camcor(dict_local, self.parameters_by_value, self.parameters_by_name)
        except:
            output_dict = ffc.create_camcor(dict_local, self.parameters_by_value, self.parameters_by_name)
        dict_local.update(output_dict)

class TASK_FFC_APPLY(TASK):

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        # Check if user set input an output paths
        output_dict = ffc.apply_camcor(dict_local, self.parameters_by_value, self.parameters_by_name)
        dict_local.update(output_dict)
   
   
class TASK_FFC_READ_APPLY(TASK):
 
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        # Check if user set input an output paths
        output_dict = ffc.read_apply_camcor(dict_local, self.parameters_by_value, self.parameters_by_name)
        dict_local.update(output_dict)
        
class TASK_READ_DATAFRAME_FROM_CSV(TASK):

    dict_task = {"input_path" : {"required" : True},
                 "filename" : {"required" : True},
                 "dict_key_name" : {"required" : True},
                 "delimiter" : {"required" : True, "default" : ","}}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        input_path = FM.path_join(dict_setts["input_path"], dict_setts["filename"])
        data = R_connection.read_dataframe_from_csv(input_path, dict_setts["delimiter"])
        dict_local[dict_setts["dict_key_name"]] = data

class TASK_WRITE_DATAFRAME_TO_CSV(TASK):

    dict_task = {"output_path" : {"required" : True},
                 "filename" : {"required" : True},
                 "dict_key_name" : {"required" : True},
                 "delimiter" : {"required" : True, "default" : ","}}
    
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        output_path = FM.path_join(dict_setts["output_path"], dict_setts["filename"])
        data = dict_local[dict_setts["dict_key_name"]]
        R_connection.write_dataframe_to_csv(output_path, data, dict_setts["delimiter"])

class TASK_MERGE_CSV(TASK):

    dict_task = {"input_path_1" : {"required" : True},
                 "input_path_1" : {"required" : True},
                 "csv_names_list" : {"required" : True},
                 "output_path" : {"required" : True},
                 "delimiter" : {"required" : True, "default" : ","}}

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local, dict_setts):
        in_path_list = []
        in_path_list.append(dict_setts["input_path_1"])
        in_path_list.append(dict_setts["input_path_2"])
        csv_names = (dict_setts["csv_names_list"]).split(",")
        for csv_name in csv_names:
            data = CSV_M.simple_merge(csv_name, in_path_list, dict_setts["delimiter"])
            #Saving data
            out_path = FM.path_join(dict_setts["output_path"], csv_name)
            if FM.path_check_existence(out_path):
                logger.warning("File %s already exists. Removing old data.", out_path)
                FM.dir_remove(out_path)
            CSV_M.write_csv(out_path, dict_setts["delimiter"], data) #if we would like to write_csv somewhere...
            # PLACEHOLDER adding data to dictionary 
