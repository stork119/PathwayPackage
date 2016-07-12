#! /usr/bin/python
import logging, os.path
import argparse
import modules.file_managment as FM
import modules.logs_configuration as LC
import modules.xml_parser as XML_P

def main():
    PP_path = os.path.abspath('..')
    """Setting up logs."""
    LC.configure(PP_path)
    logger = logging.getLogger(__name__)
    logger.info("Starting program...")
    """Arg parse section."""
    parser = argparse.ArgumentParser(description = '\n PathwayPackage [PP] is an integration platform for instantaneous processing and analysis of confocal/fluorescent microscopy images software. \n[...]')
    parser.add_argument('-s',
                metavar = '<settingspath>', 
                type = str, 
                required = True, 
                nargs = 1, 
                help = 'Path to input_settings (in XML format).')
    parser.add_argument('-m',
                metavar = '<multiplesettings>', 
                type = str, 
                default=False,
                nargs = 1, 
                help = 'Option allows to process multiple configuration settings.')
    args = parser.parse_args()
    """Setting up pipeline."""
    logger.debug("Input settings source: %s", args.s[0])
    if os.path.isabs(args.s[0]): #relative or absolute path
        settings_path = FM.path_unify(args.s[0])
    else:
        settings_path = FM.path_join(PP_path, "configuration_settings" , args.s[0])
    if args.m != False: #single or multiple settings
        settings_list = FM.file_get_paths(settings_path)
    else:
        settings_list = [settings_path]
    for setts in settings_list:
        logger.info("Current xml settings: %s", setts)
        try:
            pipeline, config_dict = XML_P.parse(setts)
            pipeline.execute(config_dict)
        except:
            logger.error("Settings %s error.", setts)
if __name__ == "__main__":
    main()
