# Include standard modules
from typing import List, Dict, ValuesView

# Include 3rd-party modules
# Include DPL modules
from .placement import Placement
from .placement_builder import PlacementBuilder
from dpl.repo_impls.in_memory.placement_repository import PlacementRepository


class PlacementManager(object):
    """
    PlacementManager is a class that is responsible for initialization, storage
    and fetching of placements.
    """
    def __init__(self):
        """
        Default constructor
        """
        self._placements = PlacementRepository()

    def init_placements(self, config: List[Dict]) -> None:
        """
        Init all placements by a specified configuration data

        :param config: configuration data that will be used for building of Placements
        :return: None
        """
        for conf_item in config:
            new_placement = PlacementBuilder.build(conf_item)
            self._placements.add(new_placement)

    def fetch_all_placements(self) -> ValuesView[Placement]:
        """
        Fetch a set-like collection of all stored Placements

        :return: a set-like collection of Placements
        """
        return self._placements.load_all()

    def fetch_placement(self, placement_id: str) -> Placement:
        """
        Find specific placement by id

        :param placement_id:
        :return: an instance of Placement with the corresponding ID
        :raises KeyValue: if the Placement with the specified ID was not found
        """
        return self._placements.load(placement_id)
