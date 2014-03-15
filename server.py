#!/usr/bin/python
import MySQLdb
import json
import time

from autobahn.twisted.websocket import WebSocketServerProtocol, \
                                       WebSocketServerFactory


#Container object for packets
class Object:
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class BroadcastServerProtocol(WebSocketServerProtocol):

   def onOpen(self):
      self.factory.register(self)
      sendHello = {'packetType': 'welcome'}
      self.sendMessage(json.dumps(sendHello))

   def onMessage(self, payload, isBinary):
      if not isBinary:
         msg = "{} from {}".format(payload.decode('utf8'), self.peer)
         print(msg)
         packet = json.loads(payload.decode('utf8'))
         if packet['packetType'] is 1:
            insertString = "INSERT INTO `input_activity` (`date`, `inactivity`, `machine_name`) VALUES (CURRENT_TIMESTAMP, '%s', '%s');" % (str(packet['idleTime']), packet['machineName'])
            cur.execute(insertString)
            db.commit()
            idleData = Object()
            idleData.packetType = 'wsi2'
            idleData.machineName = packet['machineName']
            idleData.idleTime = packet['idleTime']
            idleData.timeStamp = int(time.time())
            for client in self.factory.clients:
               client.sendMessage(idleData.to_JSON())
            self.factory.unregister(self)
         elif packet['packetType'] is 2:
            audioData = Object()
            audioData.packetType = 'wsa1'
            audioData.masterPeak = packet['masterPeak']
            audioData.leftPeak = packet['leftPeak']
            audioData.rightPeak = packet['rightPeak']
            audioData.machineName = packet['machineName']
            audioData.timeStamp = int(time.time())
            for client in self.factory.clients:
               client.sendMessage(audioData.to_JSON())
            self.factory.unregister(self)
         elif packet['packetType'] is 3:
            windowData = Object()
            windowData.packetType = 'wsw1'
            windowData.windowName = packet['windowName']
            windowData.machineName = packet['machineName']
            windowData.timeStamp = int(time.time())
            insertString = "INSERT INTO `window_activity` (`date`, `window_name`, `machine_name`) VALUES (CURRENT_TIMESTAMP, '%s', '%s');" % (packet['windowName'], packet['machineName'])
            cur.execute(insertString)
            db.commit()
            for client in self.factory.clients:
               client.sendMessage(windowData.to_JSON())
            self.factory.unregister(self)
         elif packet['packetType'] is 101:
            cur.execute("SELECT * FROM (SELECT UNIX_TIMESTAMP(date) AS datestamp, inactivity, machine_name FROM  `input_activity` ORDER BY datestamp DESC LIMIT 900) AS temp ORDER BY datestamp ASC")
            rows = cur.fetchall()
            initialData = Object()
            initialStruct = {'packetType': 'wsi0', 'data': {}}
            initialData.packetType = 'wsi1'
            initialData.data = []
            for row in rows:
               rowData = Object()
               rowData.machineName = row[2]
               rowData.idleTime = row[1]
               rowData.timeStamp = row[0]
               initialStruct['data'][row[2]] = row[2] #Make sure we have a data array for this
               initialData.data.append(rowData)
            self.sendMessage(json.dumps(initialStruct))
            self.sendMessage(initialData.to_JSON())
         #self.factory.broadcast(msg)

   def connectionLost(self, reason):
      WebSocketServerProtocol.connectionLost(self, reason)
      self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):
   """
   Simple broadcast server broadcasting any message it receives to all
   currently connected clients.
   """

   def __init__(self, url, debug = False, debugCodePaths = False):
      WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debugCodePaths)
      self.clients = []
      self.tickcount = 0
      #self.tick()

   def tick(self):
      self.tickcount += 1
      self.broadcast("tick %d from server" % self.tickcount)
      reactor.callLater(1, self.tick)

   def register(self, client):
      if not client in self.clients:
         print("registered client {}".format(client.peer))
         self.clients.append(client)

   def unregister(self, client):
      if client in self.clients:
         print("unregistered client {}".format(client.peer))
         self.clients.remove(client)

   def broadcast(self, msg):
      print("broadcasting message '{}' ..".format(msg))
      for c in self.clients:
         c.sendMessage(msg.encode('utf8'))
         print("message sent to {}".format(c.peer))


class BroadcastPreparedServerFactory(BroadcastServerFactory):
   """
   Functionally same as above, but optimized broadcast using
   prepareMessage and sendPreparedMessage.
   """

   def broadcast(self, msg):
      print("broadcasting prepared message '{}' ..".format(msg))
      preparedMsg = self.prepareMessage(msg)
      for c in self.clients:
         c.sendPreparedMessage(preparedMsg)
         print("prepared message sent to {}".format(c.peer))

if __name__ == '__main__':

   import sys

   from twisted.python import log
   from twisted.internet import reactor

   db = MySQLdb.connect("x1.ixeta.net", "thaddeusnet", "rammimu", "thaddeusnet")
   cur = db.cursor()

   log.startLogging(sys.stdout)

   ServerFactory = BroadcastServerFactory

   factory = ServerFactory("ws://x1.ixeta.net:41414")
   factory.protocol = BroadcastServerProtocol

   reactor.listenTCP(41414, factory)
   reactor.run()