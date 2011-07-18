
from fabric import network
from fabric import state as s

class GatewayConnectionCache(network.HostConnectionCache):
    _gw = None
    def __getitem__(self, key):
        gw = s.env.get('gateway')
        if gw is None:
            return super(GatewayConnectionCache, self).__getitem__(key)

        gw_user, gw_host, gw_port = network.normalize(gw)
        if self._gw is None:
            # Normalize given key (i.e. obtain username and port, if not given)
            self._gw = network.connect(gw_user, gw_host, gw_port)

        # Normalize given key (i.e. obtain username and port, if not given)
        user, host, port = network.normalize(key)
        # Recombine for use as a key.
        real_key = network.join_host_strings(user, host, port)

        # If not found, create new connection and store it
        if real_key not in self:
            self[real_key] = network.connect_forward(self._gw, host, port, user)

        # Return the value either way
        return dict.__getitem__(self, real_key)

_c = s.connections = GatewayConnectionCache()
from fabric import operations
operations.connections = _c
