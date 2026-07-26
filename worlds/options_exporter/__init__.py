import json
import logging
import os
import types
from collections.abc import KeysView, ValuesView, ItemsView

from worlds.AutoWorld import World
from worlds.LauncherComponents import Component, components, Type


class APWorldEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder to handle Python sets, frozensets, and other
    non-serializable types commonly found in Archipelago options.
    """

    def default(self, obj):
        # Convert most iterables (but not strings) into lists
        if isinstance(obj, (set, frozenset, KeysView, ValuesView, ItemsView)):
            return list(obj)
        if hasattr(obj, '__name__'):
            return obj.__name__
        try:
            return super().default(obj)
        except TypeError:
            # Ultimate fallback to string representation to prevent crashes
            return str(obj)


class OptionsExporterWorld(World):
    """Dummy world to allow the options exporter to be packaged as an .apworld."""
    game = "Options Exporter"
    hidden = True
    item_name_to_id = {}
    location_name_to_id = {}


def export_apworld_options(*args):
    """
    Scans all loaded worlds, extracts their options,
    and exports them to a JSON file silently.
    """
    from worlds.AutoWorld import AutoWorldRegister

    logging.basicConfig(level=logging.INFO)
    logging.info("Scanning installed APWorlds for options...")

    all_options = {}

    # Iterate over all registered worlds
    for world_name, world_class in AutoWorldRegister.world_types.items():
        if world_class.hidden:
            continue

        world_options = {}

        # New worlds should use dataclasses for defining options
        if hasattr(world_class, "options_dataclass"):
            for name, option in world_class.options_dataclass.type_hints.items():
                try:
                    is_removed = False
                    # Dynamically get the inheritance chain
                    parent_classes = []
                    mro = option.mro()
                    # Skip removed options
                    if mro[0].__name__ == "Removed":
                        continue
                    for cls in mro[1:]:  # Skip index 0 (the class itself)
                        if cls.__name__ == "Removed":
                            is_removed = True
                            break
                        parent_classes.append(cls.__name__)
                        if cls.__name__ == "Option":
                            break  # Stop once we reach the base Option class

                    if is_removed:
                        continue

                    # Extract relevant class variables
                    class_vars = {}
                    for cls in mro:
                        for key, value in cls.__dict__.items():
                            # Filter out private attributes
                            if key.startswith("_"):
                                continue

                            # Filter out methods etc
                            if isinstance(value, (types.FunctionType, property, classmethod, staticmethod)) \
                                    or hasattr(value, "__get__") or "classproperty" in type(value).__name__.lower():
                                # try to get the actual value if possible
                                # if value is for example a property, this resolves the property to get a primitive value
                                try:
                                    resolved = getattr(option, key)
                                    if callable(resolved) or hasattr(resolved, "__get__"):
                                        continue
                                except Exception:
                                    continue
                                # continue with other filtering
                                value = resolved

                            # Filter out unnecessary class variables
                            if any(key.startswith(prefix) for prefix in ("option_", "alias_")):
                                continue
                            if key in ("name_lookup", "rich_text_doc", "display_name", "auto_display_name",
                                       "verify_item_name", "verify_location_name", "cull_zeroes"):
                                continue
                            if key in ("options", "aliases") and value == {}:
                                continue
                            if cls.__name__ == "Sc2ItemDict" and key == "valid_keys":
                                continue

                            # There is a typo in alttp menuspeed
                            if key == "options":
                                for k, v in value.items():
                                    if isinstance(v, tuple) and len(v) == 1 and isinstance(v[0], int):
                                        value[k] = v[0]

                            # sometimes, valid_keys are not proper keys, but the entire dictionary
                            if key == "valid_keys" and isinstance(value, dict):
                                value = sorted(value.keys())

                            # Only add it if a child class hasn't already overridden it
                            if key not in class_vars:
                                class_vars[key] = value
                        if cls.__name__ == "Option":
                            break

                    opt_data = {
                        "name": getattr(option, "display_name", name),
                        "description": option.__doc__,
                        "parent_classes": parent_classes
                    }

                    # add class variables
                    opt_data.update(class_vars)

                    world_options[name] = opt_data
                except AttributeError:
                    logging.warning("Skipping option %s (%s)" % (world_name, name))

        # TODO: Fallback for worlds using traditional dictionaries
        else:
            continue

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
        func=export_apworld_options,
        description="Export options of all APWorlds",
        component_type=Type.TOOL
    )
)
