"""
api.py
All API route endpoints

:copyright: (C) 2014 by github.com/alfg.
:license:   MIT, see README for more details.
"""

from datetime import timedelta

from flask import request, jsonify, json, Response
from flask.ext.classy import FlaskView, route

from app import app, meta, auth, auth_enabled
from app.utils import obj_to_dict, get_server_conf, get_server_port, get_all_users_count, conditional


class ServersView(FlaskView):
    """
    Primary interface for creating, reading and writing to mumble servers.
    """

    route_prefix = '/api/v1/'

    @conditional(auth.login_required, auth_enabled)
    def index(self):
        """
        Lists all servers
        """

        servers = []
        for s in meta.getAllServers():
            servers.append({
                'id': s.id(),
                'name': get_server_conf(meta, s, 'registerName'),
                'address': '%s:%s' % (
                    get_server_conf(meta, s, 'host'),
                    get_server_port(meta, s),
                ),
                'running': s.isRunning(),
                'users': (s.isRunning() and len(s.getUsers())) or 0,
                'maxusers': get_server_conf(meta, s, 'users') or 0,
                'channels': (s.isRunning() and len(s.getChannels())) or 0,
                'uptime_seconds': s.getUptime() if s.isRunning() else 0,
                'uptime': str(
                    timedelta(seconds=s.getUptime()) if s.isRunning() else ''
                ),
                'log_length': s.getLogLen()
            })

        # Workaround response due to jsonify() not allowing top-level json response
        # https://github.com/mitsuhiko/flask/issues/170
        return Response(json.dumps(servers, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    def get(self, id):
        """
        Lists server details
        """

        s = meta.getServer(id)
        tree = obj_to_dict(s.getTree())

        json_data = {
            'id': s.id(),
            'name': get_server_conf(meta, s, 'registerName'),
            'host': get_server_conf(meta, s, 'host'),
            'port': get_server_port(meta, s),
            'address': '%s:%s' % (
                get_server_conf(meta, s, 'host'),
                get_server_port(meta, s),
            ),
            'password': get_server_conf(meta, s, 'password'),
            'welcometext': get_server_conf(meta, s, 'welcometext'),
            'user_count': (s.isRunning() and len(s.getUsers())) or 0,
            'maxusers': get_server_conf(meta, s, 'users') or 0,
            'uptime': s.getUptime() if s.isRunning() else 0,
            'humanize_uptime': str(
                timedelta(seconds=s.getUptime()) if s.isRunning() else ''
            ),
            'parent_channel': tree['c'],
            'sub_channels': tree['children'],
            'users': tree['users'],
            'registered_users': s.getRegisteredUsers(''),
            'log_length': s.getLogLen(),
            'bans': s.getBans()
        }

        return jsonify(json_data)

    @conditional(auth.login_required, auth_enabled)
    def post(self):
        """
        Creates a server, starts server, and returns id
        """

        # Basic Configuration
        password = request.form.get('password')
        port = request.form.get('port')  # Defaults to inifile+server_id-1
        timeout = request.form.get('timeout')
        bandwidth = request.form.get('bandwidth')
        users = request.form.get('users')
        welcometext = request.form.get('welcometext')

        # Data for registration in the public server list
        registername = request.form.get('registername')
        registerpassword = request.form.get('registerpassword')
        registerhostname = request.form.get('registerhostname')
        registerurl = request.form.get('registerurl')

        # Create server
        server = meta.newServer()

        # Set conf if provided
        server.setConf('password', password) if password else None
        server.setConf('port', port) if port else None
        server.setConf('timeout', timeout) if timeout else None
        server.setConf('bandwidth', bandwidth) if bandwidth else None
        server.setConf('users', users) if users else None
        server.setConf('welcometext', welcometext) if welcometext else None
        server.setConf('registername', registername) if registername else None

        # Start server
        server.start()

        # Format to JSON
        json_data = {
            'id': server.id()
        }

        return jsonify(json_data)

    @conditional(auth.login_required, auth_enabled)
    def delete(self, id):
        """
        Shuts down and deletes a server
        """

        server = meta.getServer(id)
        server.stop()
        server.delete()
        return jsonify(message="Server deleted")

    # Nested routes and actions
    @conditional(auth.login_required, auth_enabled)
    @route('<id>/logs', methods=['GET'])
    def logs(self, id):
        """ Gets all server logs by server ID
        """

        server = meta.getServer(id)
        logs = []

        for l in server.getLog(0, -1):
            logs.append({
                "message": l.txt,
                "timestamp": l.timestamp,
            })
        return Response(json.dumps(logs, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/register/<user>', methods=['GET'])
    def register_user(self, id, user):
        """ Gets registered user by ID
        """

        server = meta.getServer(id)
        data = obj_to_dict(server.getRegistration(user))

        json_data = {
            "user_id": user,
            "username": data['UserName'],
            "last_active": data['UserLastActive']
        }
        return Response(json.dumps(json_data, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/channels', methods=['GET'])
    def channels(self, id):
        """ Gets all channels in server
        """

        server = meta.getServer(id)
        data = obj_to_dict(server.getChannels())

        return Response(json.dumps(data, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/channels/<channel_id>', methods=['GET'])
    def channel(self, id, channel_id):
        """ Gets all channels in server
        """

        server = meta.getServer(id)
        data = obj_to_dict(server.getChannelState(channel_id))

        return Response(json.dumps(data, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/bans', methods=['GET'])
    def bans(self, id):
        """ Gets all banned IPs in server
        """

        server = meta.getServer(id)
        data = obj_to_dict(server.getBans())
        return Response(json.dumps(data, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/conf', methods=['GET'])
    def conf(self, id):
        """ Gets all configuration in server
        """

        server = meta.getServer(id)
        data = obj_to_dict(server.getAllConf())
        return Response(json.dumps(data, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/channels/<channel_id>/acl', methods=['GET'])
    def channel_acl(self, id, channel_id):
        """ Gets all channel ACLs in server
        """

        server = meta.getServer(id)
        data = obj_to_dict(server.getACL(channel_id))
        return Response(json.dumps(data, sort_keys=True, indent=4), mimetype='application/json')

    @conditional(auth.login_required, auth_enabled)
    @route('<id>/sendmessage', methods=['POST'])
    def send_message(self, id):
        """ Sends a message to all channels in a server
        """

        message = request.form.get('message')

        if message:
            server = meta.getServer(id)
            server.sendMessageChannel(0, True, message)
            return jsonify(message="Message sent.")
        else:
            return jsonify(message="Message required.")


class StatsView(FlaskView):
    """
    View for gathering stats on murmur statistics.
    """

    route_prefix = '/api/v1/'

    @conditional(auth.login_required, auth_enabled)
    def index(self):
        """
        Lists all stats
        """

        stats = {
            'all_servers': len(meta.getAllServers()),
            'booted_servers': len(meta.getBootedServers()),
            'users_online': get_all_users_count(meta),
            'murmur_version': meta.getVersion()[3],
            'murmur-rest_version': '0.1',
            'uptime': meta.getUptime()
        }

        # Workaround response due to jsonify() not allowing top-level json response
        # https://github.com/mitsuhiko/flask/issues/170
        return Response(json.dumps(stats, sort_keys=True, indent=4), mimetype='application/json')

ServersView.register(app)
StatsView.register(app)

if __name__ == '__main__':
    app.run(debug=True)
