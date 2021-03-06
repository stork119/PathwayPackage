#! /usr/bin/python
from collections import OrderedDict
from time import sleep
import multiprocessing 
import simple_copy as SC

class TASK():
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name):
        self.parameters_by_value = parameters_by_value
        self.parameters_by_name = parameters_by_name
        self.updates_by_value = updates_by_value
        self.updates_by_name = updates_by_name
      
      
    def execute(self, dict_global):
        dict_local = dict_global.copy()
       # temp_dict = dict_global.copy()
        self.update_dict(dict_local, dict_local, self.parameters_by_value, self.parameters_by_name) #check out if its working 
        self.execute_specify(dict_local)
        self.update_dict(dict_global, dict_local, self.updates_by_value, self.updates_by_name)
      
    def update_dict(self, dict_out, dict_in, list_by_value, list_by_name):
        for k, v in list_by_value.items(): #update by value
            dict_out[k] = v
        for k, v in list_by_name.items(): #update by name
            value = dict_in[v]
            dict_out[k] = value
        self.concatenation_name_nr(dict_out)
            
    def concatenation_name_nr(self, dict_out):      
        #concatenation name.number
        key_list = []
        for k, v in dict_out.items():
            if "." in k:
                key = k.split(".")
                key_list.append(key[0])
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
                "".join(value)
                temp_dict[key_list[i]] = value
            dict_out = temp_dict.copy()


class TASK_PARALLELIZE(TASK):
   # has got object queue
    def __init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, task_list, config_dict = [], request_list = []):
        TASK.__init__(self, parameters_by_value, parameters_by_name, updates_by_value, updates_by_name)
        self.task_list = task_list
        self.config_dict = config_dict
        self.request_list = request_list

    def execute_specify(self, dict_local):
        processes_number = int(self.config_dict["number_of_cores"])
        samples_number = int(self.config_dict["sample_number"])
        sleep_time = int(dict_local["sleep_time"])
        pool = multiprocessing.Pool(processes_number)
        input_path = dict_local["input_path"]
        dir_list = SC.get_dir_names(input_path)
        print("pierwsza lista ", dir_list)
        args = ((dict_local, element) for element in dir_list) #or just pass task, because we're able to get task_list and settings_dict from init if both functions will stay here
        pool.map_async(self.execute_queue, args)
        while True:
            if len(dir_list) < samples_number:
                sleep(5)
                new_dir_list = SC.get_dir_names(input_path)
                new_dirs = [i for i in new_dir_list if i not in dir_list]
                print("new dirs", new_dirs)
                if len(new_dirs) > 0:
                    args = ((dict_local, element) for element in new_dirs) #or just pass task, because we're able to get task_list and settings_dict from init if both functions will stay here
                    pool.map_async(self.execute_queue, args)
                    dir_list = new_dir_list
            else:
                break
        pool.close()
        pool.join()

    def execute_queue(self, args):
        dict_local, element = args
        dict_local["folder_name"] = element + "\\"
        for task in task_list:
            task.execute(dict_local)
        #task_name = (type(task).__name__)
        #element.execute(dict_global) # or executing = getattr(tk, "execute"), executing() ?
        
            
def main():      
    dict_local = {"input_path":"C://Users//Setnea//Desktop//input//", "output_path": "C://Users//Setnea//Desktop//output//proba//", "sleep_time" :"2"}
    parameters_by_name = []
    parameters_by_value = []
    updates_by_name = []
    updates_by_value = []
    task_list = []
    config_dict = {"number_of_cores":"7", "zaza":"123", "sample_number":"3"}
    e1 = TASK_PARALLELIZE(parameters_by_value, parameters_by_name, updates_by_value, updates_by_name, task_list, config_dict)
    e1.execute_specify(dict_local)
    #in_path = dict_local["input_path"]
    #out_path = dict_local["output_path"]
    #sleep_time = int(dict_local["sleep_time"])
    #task_name = (type(task).__name__)
    #element.execute(dict_global) # or executing = getattr(tk, "execute"), executing() ?
    #SC.copy_data_constantly(in_path, out_path, int(sleep_time))

if __name__ == "__main__":
    main()
