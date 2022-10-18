
import yaml


def parse_yml_file(file):
    """
    Reads a yaml file and returns its data.

    :type file:             string
    :content file:          The file path.
    """
    
    with open(file, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)