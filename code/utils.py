import os
from itertools import product

import yaml

import seabeepy as sb

BASE_DIR = r"/home/notebook/shared-seabee-ns9879k/niva-tidy/2025/odm_tuning"
TEMP_DIR = r"/home/notebook/temp"


def copy_mission_data(mission_dir, param_version, run_id, client, odm_options=None):
    """Copy a mission folder, updating ODM parameter options, if desired.

    Args
        mission_dir: Str. Path to original mission folder.
        param_version: Int. Version of the parameter combinations YAML file to use.
        run_id: Int. Unique integer defining the model run.
        client: Obj. Client object connected to MinIO.
        odm_options: Dict. ODM options to use for this run.

    Returns
        Str. Path to copied mission folder with updated settings.
    """
    # Copy basic mission data (images and GCPs) to testing folder
    dst_dir = os.path.join(
        BASE_DIR,
        f"params_v{param_version:02d}",
        f"run-{param_version:02d}-{run_id:03d}",
    )
    for dir_name in ["images", "gcp"]:
        dir_path = os.path.join(mission_dir, dir_name)
        sb.storage.copy_folder(dir_path, dst_dir, client, containing_folder=True)

    # Parse 'default' config file
    data = sb.ortho.parse_config(mission_dir)

    # Update config. details
    data["grouping"] = f"odm-tuning-{param_version:02d}-{run_id:03d}"
    data["project"] = "odm-tuning"
    data["mosaic"] = True
    data["publish"] = False
    data["classify"] = False

    # Remove any ML options
    data.pop("ml_options", None)

    # Update ODM options
    if odm_options:
        data["odm_options"] = odm_options
    else:
        data.pop("odm_options", None)

    # Save updated config.
    config_path = os.path.join(dst_dir, "config.seabee.yaml")
    temp_path = os.path.join(TEMP_DIR, "config.seabee.yaml")
    write_config(temp_path, data)
    sb.storage.copy_file(temp_path, config_path, client, overwrite=False)
    os.remove(temp_path)

    return dst_dir


def get_param_combinations(yaml_path):
    """Read parameter options from a YAML file and get all combinations of specified parameters.

    Args
        yaml_path: Str. Path to YAML file with parameter options.

    Returns
        List of dicts. Each dict contains the parameters for a single ODM run.
    """
    # Read YAML file
    with open(yaml_path, "r") as f:
        options = yaml.safe_load(f)

    # Flatten nested sections (if any)
    flat_options = {}
    for k, v in options.items():
        if isinstance(v, dict):
            flat_options.update(v)
        else:
            flat_options[k] = v

    # Build all combinations
    keys = list(flat_options.keys())
    values = [flat_options[k] for k in keys]

    combos = [dict(zip(keys, combo)) for combo in product(*values)]

    return combos


def write_config(config_path, data):
    """Write a dict to YAML.

    Args
        config_path: Str. Path to YAML file to create.
        data: Dict. Data to convert to YAML.

    Returns
        None. Data are saved to disk.
    """
    with open(config_path, "w") as yaml_file:
        yaml.dump(data, yaml_file, default_flow_style=False, allow_unicode=True)