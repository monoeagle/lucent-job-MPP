# app/data/clients/cmdb_client.py
import os
import yaml


class CmdbClient:
    """Interface for CMDB access."""

    def get_locations(self):
        raise NotImplementedError

    def get_location(self, id):
        raise NotImplementedError

    def get_networks(self, location_id=None, security_zone_id=None):
        raise NotImplementedError

    def get_network(self, id):
        raise NotImplementedError

    def get_tenants(self):
        raise NotImplementedError

    def get_tenant(self, id):
        raise NotImplementedError

    def get_security_zones(self):
        raise NotImplementedError

    def get_security_zone(self, id):
        raise NotImplementedError

    def get_networks_for_context(self, location_id, security_zone_id):
        raise NotImplementedError

    def health(self):
        raise NotImplementedError


class CmdbStubClient(CmdbClient):
    def __init__(self, data_path="./stubs/cmdb/"):
        self._data_path = data_path
        self._loaded = False
        self._locations = []
        self._networks = []
        self._tenants = []
        self._security_zones = []
        self._load_data()

    def _load_data(self):
        try:
            self._locations = self._load_file("locations")
            self._networks = self._load_file("networks")
            self._tenants = self._load_file("tenants")
            self._security_zones = self._load_file("security_zones")
            self._loaded = True
        except Exception:
            self._loaded = False

    def _load_file(self, name):
        path = os.path.join(self._data_path, f"{name}.yaml")
        with open(path, "r") as f:
            return yaml.safe_load(f) or []

    def _find_by_id(self, collection, id):
        for item in collection:
            if item["id"] == id:
                return item
        return None

    def get_locations(self):
        return list(self._locations)

    def get_location(self, id):
        return self._find_by_id(self._locations, id)

    def get_networks(self, location_id=None, security_zone_id=None):
        result = self._networks
        if location_id is not None:
            result = [n for n in result if n["location_id"] == location_id]
        if security_zone_id is not None:
            result = [n for n in result if n["security_zone_id"] == security_zone_id]
        return result

    def get_network(self, id):
        return self._find_by_id(self._networks, id)

    def get_tenants(self):
        return list(self._tenants)

    def get_tenant(self, id):
        return self._find_by_id(self._tenants, id)

    def get_security_zones(self):
        return list(self._security_zones)

    def get_security_zone(self, id):
        return self._find_by_id(self._security_zones, id)

    def get_networks_for_context(self, location_id, security_zone_id):
        return self.get_networks(location_id=location_id, security_zone_id=security_zone_id)

    def health(self):
        return self._loaded
