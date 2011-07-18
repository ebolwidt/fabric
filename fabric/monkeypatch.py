import sys
import socket

from forward_ssh import ForwardSSHClient
import getpass
import paramiko as ssh
from paramiko.resource import ResourceManager

from fabric import network
from fabric import state as s

def connect_forward(gw, host, port, user):
    """
    Create a different connect that works with a gateway. We really need to
    create the socket and destroy it when the connection fails and then retry
    the connect.
    """
    client = ForwardSSHClient()
    while True:
        # Load known host keys (e.g. ~/.ssh/known_hosts) unless user says not to.
        if not s.env.disable_known_hosts:
            client.load_system_host_keys()
        # Unless user specified not to, accept/add new, unknown host keys
        if not s.env.reject_unknown_hosts:
            client.set_missing_host_key_policy(ssh.AutoAddPolicy())

        sock = gw.get_transport().open_channel('direct-tcpip', (host, int(port)), ('', 0))
        try:
            client.connect(host, sock, int(port), user, s.env.password,
                           key_filename=s.env.key_filename, timeout=10)
            client._sock_ = sock
            return client
        except (
            ssh.AuthenticationException,
            ssh.PasswordRequiredException,
            ssh.SSHException
        ), e:
            if e.__class__ is ssh.SSHException and s.env.password:
                network.abort(str(e))

            s.env.password = network.prompt_for_password(s.env.password)
            sock.close()

        except (EOFError, TypeError):
            # Print a newline (in case user was sitting at prompt)
            print('')
            sys.exit(0)
        # Handle timeouts
        except socket.timeout:
            network.abort('Timed out trying to connect to %s' % host)
        # Handle DNS error / name lookup failure
        except socket.gaierror:
            network.abort('Name lookup failed for %s' % host)
        # Handle generic network-related errors
        # NOTE: In 2.6, socket.error subclasses IOError
        except socket.error, e:
            network.abort('Low level socket error connecting to host %s: %s' % (
                host, e[1])
            )


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
            self[real_key] = connect_forward(self._gw, host, port, user)

        # Return the value either way
        return dict.__getitem__(self, real_key)

_c = s.connections = GatewayConnectionCache()
from fabric import operations
operations.connections = _c
