import os
from typing import Optional, Dict, Any

def load_crawler_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads and parses the YAML crawler configuration.
    Falls back to a standard default configuration if file is missing.
    """
    if not config_path:
        base_dir = os.path.dirname(__file__)
        config_path = os.path.join(base_dir, "crawler_config.yaml")

    default_config = {
        "mode": "full",
        "include_namespaces": ["Main"],
        "exclude_prefixes": [],
        "exclude_patterns": [],
        "seed_pages": [],
        "max_pages": 500
    }

    if not os.path.exists(config_path):
        return default_config

    config = {
        "mode": "full",
        "include_namespaces": [],
        "exclude_prefixes": [],
        "exclude_patterns": [],
        "seed_pages": [],
        "max_pages": 500
    }

    current_list = None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                raw_line = line.split('#')[0]
                stripped = raw_line.strip()
                if not stripped:
                    continue

                if stripped.startswith("-"):
                    val = stripped[1:].strip().strip('"').strip("'")
                    if current_list is not None:
                        current_list.append(val)
                    continue

                if ":" in stripped:
                    parts = stripped.split(":", 1)
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")

                    if not v:
                        if k in config:
                            current_list = config[k]
                        else:
                            current_list = []
                            config[k] = current_list
                    else:
                        if v.lower() == "true":
                            config[k] = True
                        elif v.lower() == "false":
                            config[k] = False
                        elif v.isdigit():
                            config[k] = int(v)
                        else:
                            config[k] = v
                        current_list = None
    except Exception as e:
        print(f"Warning: Failed to load config from {config_path}: {e}. Using default.")
        return default_config

    # Fill in defaults if any lists/keys were omitted
    for k, v in default_config.items():
        if k not in config:
            config[k] = v

    return config
