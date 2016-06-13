#! /usr/bin/python
from collections import OrderedDict
import modules.file_managment as FM
import modules.cellprofiler as cpm
import modules.csv_managment as CSV_M
import modules.map_plate as map_plate
from time import sleep
import multiprocessing 
import logging
import os

logger = logging.getLogger(__name__)

class TASK():

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args = {}):
        self.parameters_by_value = parameters_by_value
        self.parameters_by_name = parameters_by_name
        self.updates_by_value = updates_by_value
        self.updates_by_name = updates_by_name

    def execute(self, dict_global):
        task_name = self.__class__.__name__
        logger.debug("TASK (class) name: %s", task_name)
        dict_local = dict_global.copy()
       # temp_dict = dict_global.copy()
        logger.debug("dict_local before update: %s", (dict_local))
        dict_local = self.update_dict(dict_local, dict_local, self.parameters_by_value, self.parameters_by_name) #check out if its working 
        logger.debug("dict_local after update: %s", dict_local)
        self.execute_specify(dict_local)
        logger.debug("dict_local after execute_specify: %s", dict_local) #dunno if its needed
        logger.debug("dict_global before update: %s", dict_global)
        dict_global = self.update_dict(dict_global, dict_local, self.updates_by_value, self.updates_by_name)
        logger.debug("dict_global after update: %s", dict_global)
        return dict_global

    def update_dict(self, dict_out, dict_in, list_by_value, list_by_name):
        for k, v in list_by_value.items(): #update by value
            dict_out[k] = v
            logger.debug("Dict_out new key, value (updated by value): %s, %s", k, v)
        for k, v in list_by_name.items(): #update by name
            logger.debug("Dict_in (by names) key, value: %s, %s", k, v)
            value = dict_in[v]
            dict_out[k] = value
            logger.debug("Dict_out new key, value (updated by name): %s, %s", k, value)
        logger.debug("Dict_out before concatenation: %s", dict_out)
        dict_out = self.concatenation_name_nr(dict_out)
        logger.debug("Dict_out after concatenation: %s", dict_out)        
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


class TASK_QUEUE(TASK):
  
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.task_list = args['task_list']
    def execute_specify(self, dict_local):
        for task in self.task_list:
            dict_local = task.execute(dict_local)


class TASK_DOWNLOAD(TASK):
  
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        in_path = dict_local["input_path"]
        out_path = dict_local["output_path"]
        try:
            job_done = str(dict_local["experiment_finished"])
            job_done = job_done.lower()
            if job_done == "no" or "0" or "false":
                required_files = (dict_local["required_files"]).split(",")
                sleep_time = dict_local["sleep_time"]
                FM.dir_check_completeness(in_path, required_files, sleep_time)
        except:
            pass
        FM.dir_copy(in_path, out_path)


class TASK_REMOVE(TASK):
  
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        in_path = dict_local["input_path"]
        FM.dir_remove(in_path)

   
class TASK_QUANTIFY(TASK):
  
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        cp_path = dict_local["cp_path"]
        in_path = dict_local["input_path"]
        out_path = dict_local["output_path"]
        pipeline = dict_local["pipeline"]
        #cpm.check_pipeline(pipeline)
        cpm.run_cp_by_cmd(cp_path, in_path, out_path, pipeline)

   
class TASK_MERGE(TASK):
  
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        in_path = dict_local["input_path"]
        output_path = dict_local["output_path"]
        subdir_list = FM.dir_get_paths(in_path)
        csv_names = (dict_local["csv_names_list"]).split(",")
        try:
            deltimer = dict_local["deltimer"]
        except:
            deltimer = "," #choose separator
        for csv_name in csv_names:
            data = CSV_M.merge(csv_name, subdir_list)
            """extension = FM.file_get_extension(csv_name)
            len_ext = len(extension)
            name = csv_name[:-(len_ext)] # for files different then csv...""" 
            name = csv_name[:-4] 
            dict_local[name] = data
            #Saving data
            out_path = FM.path_join(output_path, csv_name)
            if FM.path_check_existence(out_path):
                FM.dir_remove(out_path)
            CSV_M.write_csv(out_path, deltimer, data) #if we would like to write_csv somewhere...


class TASK_PARALLELIZE(TASK):

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.task_list = args['task_list']
        self.config_dict = args['config_dict']

    def execute_specify(self, dict_local):
        dir_list, folders_number = self.parsing_elements_list(dict_local)
        processes_number = int(dict_local["number_of_cores"])
        sleep_time = int(dict_local["sleep_time"])
        new_dirs = dir_list
        pool = multiprocessing.Pool(processes_number)
        while True:
            if len(new_dirs) > 0:
                args = ((dict_local, element) for element in new_dirs) #or just pass task, because we're able to get task_list and settings_dict from init if both functions will stay here
                pool.map_async(self._execute_queue, args)
            if len(dir_list) >= folders_number:
                break
            sleep(sleep_time)
            input_path = str(dict_local["input_path"])
            new_dir_list = FM.dir_get_names(input_path)
            new_dirs = [i for i in new_dir_list if i not in dir_list]
            dir_list = new_dir_list
        pool.close()
        pool.join()

    def _execute_queue(self, args):
        dict_local, element = args
        dict_local["folder_name"] = element
        for task in self.task_list:
            task.execute(dict_local)

   
class TASK_PARALLELIZE_LIST(TASK_PARALLELIZE): # list of objects (folders)

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK_PARALLELIZE.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def parsing_elements_list(self, dict_local):
        paths = []
        input_path = str(dict_local["input_path"])
        folder_list = (dict_local["folders_list"]).split(",")
        for folder in folder_list:
            path = FM.path_join(input_path, folder)
            paths.append(path)
        folders_number = len(paths)
        return paths, folders_number


class TASK_PARALLELIZE_PATH(TASK_PARALLELIZE): #all objects (folders) in given directory (path)

    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args):
        TASK_PARALLELIZE.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)
        self.config_dict = args['config_dict']

    def parsing_elements_list(self, dict_local):
        folders_number = int(dict_local["folders_number"])
        input_path = str(dict_local["input_path"])
        dir_list = FM.dir_get_names(input_path)
        return dir_list, folders_number


class MAP_PLATE(TASK):
  
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name,  args = {}):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, args)

    def execute_specify(self, dict_local):
        input_path_csv = dict_local["input_path_csv"]
        input_path_metadata = dict_local["input_path_metadata"]
        output_path = dict_local["output_path"]
        csv_names = (dict_local["csv_names_list"]).split(",")
        map_plate.combine(input_path_csv, input_path_metadata, output_path, csv_list)
