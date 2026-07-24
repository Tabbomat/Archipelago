import json
import logging
import os

from worlds.LauncherComponents import Component, components


class APWorldEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder to handle Python sets, frozensets, and other
    non-serializable types commonly found in Archipelago options.
    """

    def default(self, obj):
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if hasattr(obj, '__name__'):
            return obj.__name__
        try:
            return super().default(obj)
        except TypeError:
            # Ultimate fallback to string representation to prevent crashes
            return str(obj)


def export_apworld_options(*args):
    """
    Scans all loaded worlds, extracts their options,
    and exports them to a JSON file silently.
    """
    from worlds.AutoWorld import AutoWorldRegister
    import dataclasses

    logging.basicConfig(level=logging.INFO)
    logging.info("Scanning installed APWorlds for options...")

    all_options = {}

    # Iterate over all registered worlds
    for world_name, world_class in AutoWorldRegister.world_types.items():
        if world_name == "Archipelago":
            continue

        world_options = {}

        # New worlds should use dataclasses for defining options
        if hasattr(world_class, "options_dataclass"):
            for field in dataclasses.fields(world_class.options_dataclass):
                opt_class = field.type

                opt_data = {
                    "type": opt_class.__name__ if hasattr(opt_class, "__name__") else str(opt_class)
                }
                if hasattr(opt_class, "default"):
                    opt_data["default"] = opt_class.default
                if hasattr(opt_class, "options"):
                    opt_data["choices"] = opt_class.options

                world_options[field.name] = opt_data

        # Fallback for worlds using traditional dictionaries
        elif hasattr(world_class, "options"):
            for opt_name, opt_class in world_class.options.items():
                opt_data = {
                    "type": opt_class.__name__ if hasattr(opt_class, "__name__") else str(opt_class)
                }
                if hasattr(opt_class, "default"):
                    opt_data["default"] = opt_class.default
                if hasattr(opt_class, "options"):
                    opt_data["choices"] = opt_class.options

                world_options[opt_name] = opt_data

        all_options[world_name] = world_options

    # Export to a JSON file in the root Archipelago directory
    output_file = os.path.join(os.getcwd(), "apworld_options.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_options, f, indent=2, cls=APWorldEncoder)

    logging.info(f"Options successfully exported to: {output_file}")


# Register the tool as a new component in the Archipelago Launcher
components.append(
    Component(
        display_name="Export APWorld Options",
        script_name="export_apworld_options",
        func=export_apworld_options,
        description="Export options of all APWorlds",
    )
)
