import obspython as obs

from time import sleep
from threading import Thread
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from urllib.parse import unquote

PORT = 5476
oldPORT = 0

serverthread = None
stopserver = False
httpd = None

# ------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):

        obs.script_log(obs.LOG_DEBUG, "Got GET!")

        opts = dict()

        command = self.path[1:]
        if "?" in command:
            split = command.split("?")
            options = split[1].split("&")

            for option in options:
                splitopt = option.split("=")
                opts[splitopt[0]] = splitopt[1]

            obs.script_log(obs.LOG_DEBUG, str(opts))

            if "scene" in opts:
                s = unquote(str(opts["scene"]))
                set_scene(s)
                obs.script_log(obs.LOG_DEBUG, s)
            elif "mute" in opts:
                s = unquote(str(opts["mute"]))
                mute_source(s)
                obs.script_log(obs.LOG_DEBUG, s)
            elif "unmute" in opts:
                s = unquote(str(opts["unmute"]))
                unmute_source(s)
                obs.script_log(obs.LOG_DEBUG, s)

            elif "visibility" in opts:
                obs.script_log(obs.LOG_DEBUG, str(opts))
                visibility = unquote(str(opts["visibility"]))

                if (
                    str(opts["hide"]).lower() == "true"
                    or str(opts["hide"]).lower() == "false"
                ):
                    hide = str(opts["hide"]).lower() == "true"
                    visibility_source(visibility, hide)

        self.send_response_only(200)
        self.send_header("Content-type", "text/plain")
        self.wfile.write("s".encode())


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ------------------------------------------------------------


def server_handle():
    global httpd

    if httpd:
        # Timeout must be very small, otherwise it impacts the
        # framerate of the stream
        httpd.timeout = 0.001
        httpd.handle_request()


def server_task():
    global httpd
    global stopserver
    obs.script_log(obs.LOG_DEBUG, "Server task started")

    while not stopserver:
        httpd.timeout = 0.001
        httpd.handle_request()
        sleep(0.1)

    obs.script_log(obs.LOG_DEBUG, "Server task stopped")

    stopserver = False


def stop_server():
    global httpd
    global serverthread
    global stopserver
    obs.script_log(obs.LOG_DEBUG, "Server stopped")

    if serverthread != None:
        stopserver = True
        serverthread = None

    if httpd:
        httpd.server_close()

    httpd = None


def start_server():
    global httpd
    global serverthread

    obs.script_log(obs.LOG_DEBUG, "Server started")

    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, Handler)

    if serverthread == None:
        serverthread = Thread(target=server_task)
        serverthread.start()


def manage_server():
    stop_server()
    start_server()


def script_update(settings):
    global PORT
    global oldPORT

    PORT = obs.obs_data_get_int(settings, "PORT")

    if oldPORT != PORT:
        manage_server()
        oldPORT = PORT


def script_load(settings):
    obs.script_log(obs.LOG_DEBUG, "Loading script")
    start_server()


def script_unload():
    stop_server()
    obs.script_log(obs.LOG_DEBUG, "Unloading script")


def script_defaults(settings):
    global PORT
    PORT = 8888


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_int(props, "PORT", "Port Number", 1000, 10000, 1)

    return props


def set_scene(scene_name):
    scenes = obs.obs_frontend_get_scenes()
    for scene in scenes:
        name = obs.obs_source_get_name(scene)
        if name == scene_name:
            obs.obs_frontend_set_current_scene(scene)


def mute_source(source_name):
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        obs.obs_source_set_muted(source, True)


def unmute_source(source_name):
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        obs.obs_source_set_muted(source, False)


def visibility_source(source_name, hide):
    current_scene = obs.obs_scene_from_source(obs.obs_frontend_get_current_scene())
    scene_item = obs.obs_scene_find_source(current_scene, source_name)
    if scene_item is not None:
        obs.obs_sceneitem_set_visible(scene_item, hide)