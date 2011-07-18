import getpass
import paramiko as ssh
from paramiko.resource import ResourceManager

class ForwardSSHClient(ssh.SSHClient):
    """
    Override the default ssh.SSHClient to make it accept a socket as an extra argument,
    instead of creating one of its own.
    """
    def connect(self, hostname, sock, port=22, username=None, password=None, pkey=None,
                key_filename=None, timeout=None, allow_agent=True, look_for_keys=True):
        t = self._transport = ssh.Transport(sock)

        if self._log_channel is not None:
            t.set_log_channel(self._log_channel)

        t.start_client()
        ResourceManager.register(self, t)

        server_key = t.get_remote_server_key()
        keytype = server_key.get_name()

        our_server_key = self._system_host_keys.get(hostname, {}).get(keytype, None)
        if our_server_key is None:
            our_server_key = self._host_keys.get(hostname, {}).get(keytype, None)
        if our_server_key is None:
            # will raise exception if the key is rejected; let that fall out
            self._policy.missing_host_key(self, hostname, server_key)
            # if the callback returns, assume the key is ok
            our_server_key = server_key

        if server_key != our_server_key:
            raise ssh.BadHostKeyException(hostname, server_key, our_server_key)

        if username is None:
            username = getpass.getuser()

        if key_filename is None:
            key_filenames = []
        elif isinstance(key_filename, (str, unicode)):
            key_filenames = [ key_filename ]
        else:
            key_filenames = key_filename
        self._auth(username, password, pkey, key_filenames, allow_agent, look_for_keys)