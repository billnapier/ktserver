#!/usr/bin/python

from ConfigParser import ConfigParser
import socket
import uuid
import logging
import urllib
import os

import simplejson as json

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.application.internet import MulticastServer
from twisted.web import server, resource, static
from twisted.internet import abstract

import media

UPNP_MULTICAST_PORT = 1900
UPNP_MULTICAST_ADDR = '239.255.255.250'

logging.basicConfig(level=logging.DEBUG,)

LOCAL_IP_ADDRESS = None

class MulticastServerUDP(DatagramProtocol):
    def __init__(self, config):
        self.config_ = config
        self.uuid_ = uuid.uuid4()

        self.port_ = reactor.listenUDP(0, DatagramProtocol())
        self.notify()
        reactor.callLater(300, self.notify)

    def notify(self):
        logging.debug("sending NOTIFY")

        msg="""NOTIFY * HTTP/1.1\r
Host: %s:%d\r
Location: http://%s:%d/hillcrest/descriptor.xml\r
SERVER: ktserv\r
NTS: ssdp:alive\r
USN: uuid:%s::urn:hcrest-com:service:X_RaptorIPCService:1\r
Cache-Control: max-age=600\r
NT: urn:hcrest-com:service:X_RaptorIPCService:1\r
Name: %s\r
Version: 1.1.110.15\r
HC_SCHEMA: 22.1\r
""" % (UPNP_MULTICAST_ADDR,
       UPNP_MULTICAST_PORT,
       LOCAL_IP_ADDRESS,
       self.config_.getint("server", "port"),
       self.uuid_,
       self.config_.get("server", "name"),
       )
        self.port_.write(msg,
                         (UPNP_MULTICAST_ADDR, UPNP_MULTICAST_PORT))

    def startProtocol(self):
        logging.debug('Started Listening')
        # Join a specific multicast group, which is the IP we will respond to
        self.transport.joinGroup(UPNP_MULTICAST_ADDR)

    def datagramReceived(self, datagram, address):
        lines = datagram.split("\r\n")
        if lines[0].startswith("M-SEARCH"):
            global LOCAL_IP_ADDRESS
            if LOCAL_IP_ADDRESS is None:
                # Figure out our local IP address
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(address)
                (ipaddr, port) = s.getsockname()
                LOCAL_IP_ADDRESS = ipaddr

            data = """HTTP/1.1 200 OK\r
Location: http://%s:%d/hillcrest/descriptor.xml\r
Ext:\r
USN: uuid:%s::urn:hcrest-com:service:X_RaptorIPCService:1\r
SERVER: ktserv\
Cache-Control: no-cache="Ext", max-age = 5000\r
ST: urn:hcrest-com:service:X_RaptorIPCService:1\r
Name: %s\r
Version: 1.1.110.15\r
HC_SCHEMA: 22.1\r
""" % (LOCAL_IP_ADDRESS,
       self.config_.getint("server", "port"),
       self.uuid_,
       self.config_.get("server", "name"))
            self.transport.write(data, address)

class Properties(resource.Resource):
    # We can't mach the properties file it gives us, since we're not
    # it.  So just say OK and get on with things.
    def render_GET(self, request):
        return "OK"
    def render_POST(self, request):
        logging.debug("got properties request")
        return "OK"

class Event(resource.Resource):
    def render_GET(self, request):
        global LOCAL_IP_ADDRESS
        if LOCAL_IP_ADDRESS is None:
            LOCAL_IP_ADDRESS = request.getHost().host
        return "{}"

class Media(resource.Resource):
    def __init__(self, handler):
        self.handler_ = handler

    def render_GET(self, request):
        logging.debug("got media request: " + urllib.unquote(request.uri))
        req = json.loads(request.args['Request'][0])
        response = self.handler_.process(req)
        logging.debug("sending response: " + response)
        return response

class MediaUrlFactory:
    def __init__(self, mediaDir, prefix, port):
        self.media_dir_ = mediaDir
        self.prefix_ = prefix
        self.port_ = port

    def create(self, item):
        comomn_path = os.path.commonprefix([item, self.media_dir_])
        path_part = urllib.quote(self.prefix_ + item.replace(comomn_path, ""))
        global LOCAL_IP_ADDRESS
        return "http://%s:%d/%s" % (LOCAL_IP_ADDRESS,
                                    self.port_,
                                    path_part)

class LoggingStatic(static.File):
    def __init__(self, dir, defaultType="text/html", ignoredExts=(), registry=None, allowExt=0):
        static.File.__init__(self, dir, defaultType, ignoredExts, registry, allowExt)

    def render(self, request):
        logging.debug("handling static request: " + request.uri)
        return static.File.render(self, request)

def buildResources(config):
    root = resource.Resource()
    ue = resource.Resource()
    root.putChild("UE", ue)
    ue.putChild("properties", Properties())
    ue.putChild("event", Event())

    child_handlers = {}
    count = 0

    for (prefix, path) in config.items('movies') + config.items('photos'):
        child_handlers[path] = media.Handler(config,
                                             path,
                                             MediaUrlFactory(path, prefix, config.getint("server", "port")))
        root.putChild(prefix, LoggingStatic(path))
        count += 1
    ue.putChild("media", Media(media.RootHandler(child_handlers)))
    return root

def main():
    config = ConfigParser()
    config.read("ktserver.conf")

    udp = MulticastServerUDP(config)

    # Start up the HTTP part
    site = server.Site(buildResources(config))
    reactor.listenTCP(config.getint("server", "port"), site)

    # Start up the SSDP part
    reactor.listenMulticast(UPNP_MULTICAST_PORT, udp, listenMultiple=True)
    reactor.run()

if __name__ == '__main__':
    main()
